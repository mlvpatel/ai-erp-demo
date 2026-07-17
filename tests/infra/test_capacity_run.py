from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "infra" / "images" / "frappe" / "capacity_run.py"
SPEC = importlib.util.spec_from_file_location("capacity_run", MODULE_PATH)
capacity_run = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(capacity_run)


class CapacityRunTest(unittest.TestCase):
    def evidence(self):
        return {
            "schema_version": 1,
            "profile_id": "service-operations-mvp-v1",
            "mode": "disposable-synthetic-full-profile",
            "status": "PASS",
            "full_profile": True,
            "synthetic_only": True,
            "sample_count": 100,
            "record_counts": capacity_run.EXPECTED_COUNTS,
            "results": [{"scenario": f"scenario-{index}", "status": "PASS"} for index in range(7)],
            "concurrency": {
                "request_count": 10,
                "authenticated_sessions": 10,
                "distinct_users": 5,
                "stock_entries_created": 1,
                "unique_result_count": 1,
                "partial_issue": False,
                "retry_idempotent": True,
            },
        }

    def environment(self):
        return {
            "AI_ERP_FULL_CAPACITY_ALLOW": capacity_run.ACKNOWLEDGEMENT,
            "CAPACITY_TARGET_SITE": "capacity-run-123.internal",
            "DB_ROOT_USERNAME": "synthetic-root",
            "DB_ROOT_PASSWORD": "<synthetic-root-credential>",
            "FRAPPE_ADMIN_PASSWORD": "<synthetic-admin-credential>",
            "DB_HOST": "synthetic-db.internal",
            "BACKUP_BUCKET": "private-evidence",
            "BACKUP_KMS_KEY_ARN": "arn:aws:kms:eu-central-1:123456789012:key/synthetic",
            "DEPLOYMENT_ENVIRONMENT": "pilot",
            "CAPACITY_EVIDENCE_S3_KEY": "release-evidence/0123456789abcdef0123456789abcdef01234567/capacity/123.json",
            "CAPACITY_COMMIT": "0123456789abcdef0123456789abcdef01234567",
            "CAPACITY_WORKFLOW_RUN": "123",
            "CAPACITY_SAMPLES": "100",
        }

    def test_runs_publishes_metric_and_deletes_site(self):
        s3 = Mock()
        s3.head_object.side_effect = lambda **kwargs: {
            "ContentLength": len(s3.put_object.call_args.kwargs["Body"]),
            "Metadata": {"evidence-status": "complete"},
        }
        cloudwatch = Mock()
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "aggregate.json"

            def runner(command, **_kwargs):
                if "ai_erp_service.capacity.run" in command:
                    evidence_path.write_text(json.dumps(self.evidence()), encoding="utf-8")

            with (
                patch.dict(os.environ, self.environment(), clear=True),
                patch.object(capacity_run, "EVIDENCE_PATH", evidence_path),
            ):
                result = capacity_run.run_capacity(s3=s3, cloudwatch=cloudwatch, runner=runner)

        self.assertEqual(result["status"], "PASS")
        s3.put_object.assert_called_once()
        cloudwatch.put_metric_data.assert_called_once()
        self.assertFalse(evidence_path.exists())

    def test_profile_failure_still_deletes_and_does_not_publish(self):
        runner = Mock()
        runner.side_effect = [None, None, subprocess.CalledProcessError(1, "bench"), None]
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict(os.environ, self.environment(), clear=True),
                patch.object(capacity_run, "EVIDENCE_PATH", Path(directory) / "aggregate.json"),
            ):
                with self.assertRaisesRegex(capacity_run.CapacityRunError, "execution failed"):
                    capacity_run.run_capacity(s3=Mock(), cloudwatch=Mock(), runner=runner)
        self.assertIn("drop-site", runner.call_args_list[-1].args[0])

    def test_rejects_non_disposable_target_before_running(self):
        environment = self.environment()
        environment["CAPACITY_TARGET_SITE"] = "erp.example.org"
        runner = Mock()
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(capacity_run.CapacityRunError, "disposable"):
                capacity_run.run_capacity(s3=Mock(), cloudwatch=Mock(), runner=runner)
        runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()
