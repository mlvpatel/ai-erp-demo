#!/usr/bin/env python3
"""Restore one verified S3 backup into a disposable site and delete it."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_DISPOSABLE_RESTORE"
TARGET_PATTERN = re.compile(r"restore-drill-[a-z0-9-]+[.]internal")
REQUIRED_CLASSES = {"database", "files", "private-files", "site-config"}


class RestoreDrillError(RuntimeError):
    """Safe restore failure whose message contains no backup or tenant detail."""


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def parse_manifest_uri(uri: str, approved_bucket: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or parsed.netloc != approved_bucket:
        raise RestoreDrillError("restore manifest is outside the approved backup bucket")
    key = parsed.path.lstrip("/")
    if not key.startswith("sites/") or not key.endswith("/manifest.json") or ".." in key.split("/"):
        raise RestoreDrillError("restore manifest key is invalid")
    return parsed.netloc, key


def download_backup_set(*, s3, bucket: str, manifest_key: str, destination: Path) -> dict[str, Path]:
    head = s3.head_object(Bucket=bucket, Key=manifest_key)
    if head.get("Metadata", {}).get("backup-status") != "complete":
        raise RestoreDrillError("backup manifest is not marked complete")
    payload = s3.get_object(Bucket=bucket, Key=manifest_key)["Body"].read()
    try:
        manifest = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise RestoreDrillError("backup manifest is invalid") from exc
    if manifest.get("schema_version") != 1 or manifest.get("verified") is not True:
        raise RestoreDrillError("backup manifest is not verified")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise RestoreDrillError("backup manifest has no artifacts")

    prefix = manifest_key.removesuffix("manifest.json")
    selected: dict[str, Path] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise RestoreDrillError("backup manifest artifact is invalid")
        category = artifact.get("class")
        key = artifact.get("key")
        checksum = artifact.get("sha256")
        size = artifact.get("size")
        if category not in REQUIRED_CLASSES or category in selected:
            raise RestoreDrillError("backup manifest artifact classes are invalid")
        if not isinstance(key, str) or not key.startswith(prefix) or ".." in key.split("/"):
            raise RestoreDrillError("backup artifact key is outside its manifest prefix")
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise RestoreDrillError("backup artifact checksum is invalid")
        if not isinstance(size, int) or size <= 0:
            raise RestoreDrillError("backup artifact size is invalid")
        if category == "database":
            suffix = ".sql.gz" if key.endswith(".sql.gz") else ".sql"
        elif category in {"files", "private-files"}:
            suffix = ".tgz" if key.endswith(".tgz") else ".tar"
        else:
            suffix = ".json"
        target = destination / f"{category}{suffix}"
        s3.download_file(bucket, key, str(target))
        if target.stat().st_size != size or sha256(target) != checksum:
            raise RestoreDrillError("downloaded backup artifact verification failed")
        selected[category] = target
    if set(selected) != REQUIRED_CLASSES:
        raise RestoreDrillError("backup set is incomplete")
    return selected


def run_restore_drill(*, s3, cloudwatch, runner=subprocess.run) -> None:
    if os.environ.get("ALLOW_RESTORE_DRILL") != ACKNOWLEDGEMENT:
        raise RestoreDrillError("restore drill is not acknowledged")
    target_site = os.environ.get("RESTORE_TARGET_SITE", "")
    if not TARGET_PATTERN.fullmatch(target_site):
        raise RestoreDrillError("restore target must be a disposable internal site")
    bucket = os.environ["BACKUP_BUCKET"]
    manifest_uri = os.environ["RESTORE_MANIFEST_S3_URI"]
    root_user = os.environ["DB_ROOT_USERNAME"]
    root_credential = os.environ["DB_ROOT_PASSWORD"]
    admin_credential = os.environ["FRAPPE_ADMIN_PASSWORD"]
    db_host = os.environ["DB_HOST"]
    environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
    bucket, manifest_key = parse_manifest_uri(manifest_uri, bucket)
    database_name = "restore_" + hashlib.sha256(target_site.encode()).hexdigest()[:16]
    database_credential = secrets.token_urlsafe(32)

    cleanup_needed = False
    primary_error: Optional[Exception] = None
    cleanup_error: Optional[Exception] = None
    with tempfile.TemporaryDirectory(prefix="ai-erp-restore-", dir="/tmp") as directory:
        files = download_backup_set(
            s3=s3,
            bucket=bucket,
            manifest_key=manifest_key,
            destination=Path(directory),
        )
        new_site_command = [
            "bench", "new-site", target_site,
            "--db-host", db_host,
            "--db-port", "3306",
            "--db-name", database_name,
            "--db-password", database_credential,
            "--db-root-username", root_user,
            "--db-root-password", root_credential,
            "--admin-password", admin_credential,
            "--mariadb-user-host-login-scope", "%",
        ]
        restore_command = [
            "bench", "--site", target_site, "restore", str(files["database"]),
            "--db-root-username", root_user,
            "--db-root-password", root_credential,
            "--admin-password", admin_credential,
            "--with-public-files", str(files["files"]),
            "--with-private-files", str(files["private-files"]),
        ]
        try:
            cleanup_needed = True
            runner(new_site_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            runner(restore_command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            runner(
                ["bench", "--site", target_site, "migrate"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            runner(
                ["bench", "--site", target_site, "execute", "ai_erp_service.restore_validation.validate_restore"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            primary_error = exc
        finally:
            if cleanup_needed:
                try:
                    runner(
                        [
                            "bench", "drop-site", target_site, "--force", "--no-backup",
                            "--root-login", root_user, "--root-password", root_credential,
                        ],
                        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                except Exception as exc:
                    cleanup_error = exc

    if cleanup_error:
        raise RestoreDrillError("disposable restore cleanup failed") from cleanup_error
    if primary_error:
        raise RestoreDrillError("disposable restore validation failed") from primary_error
    cloudwatch.put_metric_data(
        Namespace="AIERP/Backup",
        MetricData=[{
            "MetricName": "RestoreDrillSuccess",
            "Dimensions": [{"Name": "Environment", "Value": environment}],
            "Timestamp": datetime.now(timezone.utc),
            "Value": 1,
            "Unit": "Count",
        }],
    )


def main() -> int:
    try:
        import boto3

        run_restore_drill(s3=boto3.client("s3"), cloudwatch=boto3.client("cloudwatch"))
    except Exception as exc:
        print(f"restore drill failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("restore drill passed and disposable site deletion completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
