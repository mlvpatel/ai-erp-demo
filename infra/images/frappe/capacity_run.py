#!/usr/bin/env python3
"""Run, publish aggregate evidence for, and delete one synthetic capacity site."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ACKNOWLEDGEMENT = "I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY"
TARGET_PATTERN = re.compile(r"capacity-run-[a-z0-9-]+[.]internal")
KEY_PATTERN = re.compile(r"release-evidence/[0-9a-f]{40}/capacity/[0-9]+[.]json")
EVIDENCE_PATH = Path("/tmp/ai-erp-capacity-evidence.json")
EXPECTED_COUNTS = {
    "customers": 250,
    "service_locations": 500,
    "items": 750,
    "service_requests": 1000,
    "service_work_orders": 5000,
    "service_work_order_time_rows": 10000,
    "service_work_order_part_rows": 10000,
    "ai_proposals": 1000,
    "stock_entries": 2000,
    "draft_sales_invoices": 1000,
}


class CapacityRunError(RuntimeError):
    """Safe capacity failure whose message contains no synthetic record detail."""


def validate_evidence(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CapacityRunError("capacity evidence must be an object")
    required = {
        "schema_version",
        "profile_id",
        "mode",
        "status",
        "full_profile",
        "synthetic_only",
        "sample_count",
        "record_counts",
        "results",
        "concurrency",
    }
    if set(value) != required:
        raise CapacityRunError("capacity evidence fields are invalid")
    if value.get("schema_version") != 1 or value.get("status") != "PASS":
        raise CapacityRunError("capacity evidence does not record a passing v1 run")
    if value.get("full_profile") is not True or value.get("synthetic_only") is not True:
        raise CapacityRunError("capacity evidence is not a synthetic full profile")
    if value.get("record_counts") != EXPECTED_COUNTS:
        raise CapacityRunError("capacity evidence counts do not match the approved profile")
    results = value.get("results")
    if not isinstance(results, list) or len(results) != 7 or any(
        not isinstance(result, dict) or result.get("status") != "PASS" for result in results
    ):
        raise CapacityRunError("capacity evidence scenarios are incomplete")
    concurrency = value.get("concurrency")
    if not isinstance(concurrency, dict) or concurrency != {
        "request_count": 10,
        "authenticated_sessions": 10,
        "distinct_users": 5,
        "stock_entries_created": 1,
        "unique_result_count": 1,
        "partial_issue": False,
        "retry_idempotent": True,
    }:
        raise CapacityRunError("capacity concurrency evidence is invalid")
    serialized = json.dumps(value, sort_keys=True).casefold()
    for forbidden in ("api_key", "api_secret", "password", "hostname", "record_name", "customer_name"):
        if forbidden in serialized:
            raise CapacityRunError("capacity evidence contains a forbidden detail")
    return value


def publish_evidence(*, s3, cloudwatch, bucket: str, key: str, kms_key_arn: str,
                     environment: str, commit: str, workflow_run: str) -> dict[str, object]:
    if not KEY_PATTERN.fullmatch(key):
        raise CapacityRunError("capacity evidence key is outside the approved release prefix")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not workflow_run.isdigit():
        raise CapacityRunError("capacity release identifiers are invalid")
    try:
        evidence = validate_evidence(json.loads(EVIDENCE_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise CapacityRunError("capacity evidence could not be loaded") from exc
    evidence["commit"] = commit
    evidence["workflow_run"] = workflow_run
    body = json.dumps(evidence, indent=2, sort_keys=True).encode()
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="aws:kms",
        SSEKMSKeyId=kms_key_arn,
        Metadata={"evidence-status": "complete", "synthetic-only": "true"},
    )
    head = s3.head_object(Bucket=bucket, Key=key)
    if int(head.get("ContentLength", -1)) != len(body) or head.get("Metadata", {}).get("evidence-status") != "complete":
        raise CapacityRunError("uploaded capacity evidence verification failed")
    cloudwatch.put_metric_data(
        Namespace="AIERP/Capacity",
        MetricData=[{
            "MetricName": "FullProfileSuccess",
            "Dimensions": [{"Name": "Environment", "Value": environment}],
            "Timestamp": datetime.now(timezone.utc),
            "Value": 1,
            "Unit": "Count",
        }],
    )
    return evidence


def run_capacity(*, s3, cloudwatch, runner=subprocess.run) -> dict[str, object]:
    if os.environ.get("AI_ERP_FULL_CAPACITY_ALLOW") != ACKNOWLEDGEMENT:
        raise CapacityRunError("capacity run is not acknowledged")
    target_site = os.environ.get("CAPACITY_TARGET_SITE", "")
    if not TARGET_PATTERN.fullmatch(target_site):
        raise CapacityRunError("capacity target must be a disposable internal site")
    root_user = os.environ["DB_ROOT_USERNAME"]
    root_credential = os.environ["DB_ROOT_PASSWORD"]
    admin_credential = os.environ["FRAPPE_ADMIN_PASSWORD"]
    db_host = os.environ["DB_HOST"]
    bucket = os.environ["BACKUP_BUCKET"]
    kms_key_arn = os.environ["BACKUP_KMS_KEY_ARN"]
    environment = os.environ["DEPLOYMENT_ENVIRONMENT"]
    evidence_key = os.environ["CAPACITY_EVIDENCE_S3_KEY"]
    commit = os.environ["CAPACITY_COMMIT"]
    workflow_run = os.environ["CAPACITY_WORKFLOW_RUN"]
    samples = int(os.environ.get("CAPACITY_SAMPLES", "100"))
    if samples < 20 or samples > 250:
        raise CapacityRunError("capacity sample count is outside the approved range")

    database_name = "capacity_" + hashlib.sha256(target_site.encode()).hexdigest()[:16]
    database_credential = secrets.token_urlsafe(32)
    primary_error: Optional[Exception] = None
    cleanup_error: Optional[Exception] = None
    evidence: dict[str, object] | None = None
    cleanup_needed = False
    EVIDENCE_PATH.unlink(missing_ok=True)
    try:
        runner(
            [
                "bench", "new-site", target_site,
                "--db-host", db_host,
                "--db-port", "3306",
                "--db-name", database_name,
                "--db-password", database_credential,
                "--db-root-username", root_user,
                "--db-root-password", root_credential,
                "--admin-password", admin_credential,
                "--mariadb-user-host-login-scope", "%",
                "--install-app", "erpnext",
                "--install-app", "ai_erp_core",
                "--install-app", "ai_erp_service",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cleanup_needed = True
        runner(
            [
                "bench", "--site", target_site, "set-config", "ai_erp_full_capacity_allow",
                ACKNOWLEDGEMENT,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        runner(
            [
                "bench", "--site", target_site, "execute", "ai_erp_service.capacity.run",
                "--kwargs", json.dumps({"samples": samples}, separators=(",", ":")),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        evidence = publish_evidence(
            s3=s3,
            cloudwatch=cloudwatch,
            bucket=bucket,
            key=evidence_key,
            kms_key_arn=kms_key_arn,
            environment=environment,
            commit=commit,
            workflow_run=workflow_run,
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
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as exc:
                cleanup_error = exc
        EVIDENCE_PATH.unlink(missing_ok=True)

    if cleanup_error:
        raise CapacityRunError("disposable capacity cleanup failed") from cleanup_error
    if primary_error:
        raise CapacityRunError("disposable capacity execution failed") from primary_error
    if evidence is None:
        raise CapacityRunError("capacity evidence was not published")
    return evidence


def main() -> int:
    try:
        import boto3

        run_capacity(s3=boto3.client("s3"), cloudwatch=boto3.client("cloudwatch"))
    except Exception as exc:
        print(f"capacity run failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print("synthetic full capacity profile passed; aggregate evidence published; disposable site deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
