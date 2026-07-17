#!/usr/bin/env python3
"""Upload and verify one fresh Frappe backup set, publishing its manifest last."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_CLASSES = {"database", "files", "private-files", "site-config"}


def classify(path: Path) -> str | None:
    name = path.name.casefold()
    if "database" in name and (name.endswith(".sql.gz") or name.endswith(".sql")):
        return "database"
    if name.endswith("private-files.tar"):
        return "private-files"
    if name.endswith("files.tar"):
        return "files"
    if name.endswith("site_config_backup.json"):
        return "site-config"
    return None


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fresh_backup_files(backup_dir: Path, started_epoch: float) -> list[tuple[Path, str]]:
    selected: list[tuple[Path, str]] = []
    for path in sorted(backup_dir.iterdir()):
        category = classify(path) if path.is_file() and path.stat().st_mtime >= started_epoch else None
        if category:
            selected.append((path, category))
    present = {category for _path, category in selected}
    missing = REQUIRED_CLASSES - present
    if missing:
        raise RuntimeError("fresh backup set is incomplete: " + ", ".join(sorted(missing)))
    return selected


def upload_backup(*, backup_dir: Path, bucket: str, site: str, kms_key_arn: str, started_epoch: float,
                  s3, cloudwatch, environment: str, now: datetime | None = None) -> dict[str, object]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]+[a-z0-9]", site):
        raise ValueError("SITE_NAME is not a safe backup prefix")
    files = fresh_backup_files(backup_dir, started_epoch)
    current = now or datetime.now(timezone.utc)
    backup_id = current.strftime("%Y%m%dT%H%M%SZ")
    prefix = f"sites/{site}/{current:%Y/%m/%d}/{backup_id}"
    artifacts: list[dict[str, object]] = []

    for path, category in files:
        checksum = digest(path)
        key = f"{prefix}/{path.name}"
        size = path.stat().st_size
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": kms_key_arn,
                "Metadata": {"sha256": checksum, "backup-class": category},
            },
        )
        head = s3.head_object(Bucket=bucket, Key=key)
        if int(head.get("ContentLength", -1)) != size or head.get("Metadata", {}).get("sha256") != checksum:
            raise RuntimeError("uploaded backup artifact verification failed")
        artifacts.append({"key": key, "class": category, "sha256": checksum, "size": size})

    manifest = {
        "schema_version": 1,
        "site": site,
        "created_at": current.isoformat(),
        "synthetic": False,
        "verified": True,
        "artifacts": artifacts,
    }
    manifest_body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_key = f"{prefix}/manifest.json"
    s3.put_object(
        Bucket=bucket,
        Key=manifest_key,
        Body=manifest_body,
        ContentType="application/json",
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId=kms_key_arn,
        Metadata={"backup-status": "complete", "artifact-count": str(len(artifacts))},
    )
    manifest_head = s3.head_object(Bucket=bucket, Key=manifest_key)
    if (
        int(manifest_head.get("ContentLength", -1)) != len(manifest_body)
        or manifest_head.get("Metadata", {}).get("backup-status") != "complete"
    ):
        raise RuntimeError("uploaded backup manifest verification failed")
    for path, _category in files:
        path.unlink()
    cloudwatch.put_metric_data(
        Namespace="AIERP/Backup",
        MetricData=[{
            "MetricName": "BackupSuccess",
            "Dimensions": [{"Name": "Environment", "Value": environment}],
            "Timestamp": current,
            "Value": 1,
            "Unit": "Count",
        }],
    )
    return manifest


def main() -> int:
    try:
        import boto3

        site = os.environ["SITE_NAME"]
        bucket = os.environ["BACKUP_BUCKET"]
        kms_key_arn = os.environ["BACKUP_KMS_KEY_ARN"]
        environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
        started_epoch = float(os.environ["BACKUP_STARTED_EPOCH"])
        bench_root = Path(os.environ.get("BENCH_ROOT", "/home/frappe/frappe-bench"))
        manifest = upload_backup(
            backup_dir=bench_root / "sites" / site / "private" / "backups",
            bucket=bucket,
            site=site,
            kms_key_arn=kms_key_arn,
            started_epoch=started_epoch,
            s3=boto3.client("s3"),
            cloudwatch=boto3.client("cloudwatch"),
            environment=environment,
        )
    except Exception as exc:
        print(f"backup upload failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(f"backup upload completed with {len(manifest['artifacts'])} verified artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
