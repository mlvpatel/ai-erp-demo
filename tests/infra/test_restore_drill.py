from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "infra" / "images" / "frappe" / "restore_drill.py"
SPEC = importlib.util.spec_from_file_location("restore_drill", MODULE_PATH)
restore_drill = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(restore_drill)


class RestoreDrillTest(unittest.TestCase):
    def fixtures(self):
        payloads = {
            "database": b"synthetic database",
            "files": b"synthetic public files",
            "private-files": b"synthetic private files",
            "site-config": b'{"synthetic":true}',
        }
        suffixes = {
            "database": "database.sql.gz",
            "files": "files.tar",
            "private-files": "private-files.tar",
            "site-config": "site_config_backup.json",
        }
        prefix = "sites/erp.example.org/2026/07/14/example/"
        manifest = {
            "schema_version": 1,
            "verified": True,
            "artifacts": [
                {
                    "key": prefix + suffixes[category],
                    "class": category,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "size": len(content),
                }
                for category, content in payloads.items()
            ],
        }
        s3 = Mock()
        s3.head_object.return_value = {"Metadata": {"backup-status": "complete"}}
        s3.get_object.return_value = {"Body": BytesIO(json.dumps(manifest).encode())}
        by_key = {item["key"]: payloads[item["class"]] for item in manifest["artifacts"]}
        s3.download_file.side_effect = lambda bucket, key, target: Path(target).write_bytes(by_key[key])
        return s3

    def environment(self):
        return {
            "ALLOW_RESTORE_DRILL": restore_drill.ACKNOWLEDGEMENT,
            "RESTORE_TARGET_SITE": "restore-drill-123.internal",
            "RESTORE_MANIFEST_S3_URI": "s3://private-backups/sites/erp.example.org/2026/07/14/example/manifest.json",
            "BACKUP_BUCKET": "private-backups",
            "DB_ROOT_USERNAME": "synthetic-root",
            "DB_ROOT_PASSWORD": "<synthetic-root-password>",
            "FRAPPE_ADMIN_PASSWORD": "<synthetic-admin-password>",
            "DB_HOST": "synthetic-db.internal",
            "DEPLOYMENT_ENVIRONMENT": "pilot",
        }

    def test_restores_validates_deletes_and_emits_metric(self):
        runner = Mock()
        cloudwatch = Mock()
        with patch.dict(os.environ, self.environment(), clear=True):
            restore_drill.run_restore_drill(s3=self.fixtures(), cloudwatch=cloudwatch, runner=runner)
        self.assertEqual(runner.call_count, 5)
        self.assertIn("new-site", runner.call_args_list[0].args[0])
        self.assertIn("restore", runner.call_args_list[1].args[0])
        self.assertIn("validate_restore", runner.call_args_list[3].args[0][-1])
        self.assertIn("drop-site", runner.call_args_list[4].args[0])
        cloudwatch.put_metric_data.assert_called_once()

    def test_validation_failure_still_deletes_and_emits_no_success(self):
        runner = Mock()
        runner.side_effect = [None, None, None, subprocess.CalledProcessError(1, "bench"), None]
        cloudwatch = Mock()
        with patch.dict(os.environ, self.environment(), clear=True):
            with self.assertRaisesRegex(restore_drill.RestoreDrillError, "validation failed"):
                restore_drill.run_restore_drill(s3=self.fixtures(), cloudwatch=cloudwatch, runner=runner)
        self.assertIn("drop-site", runner.call_args_list[-1].args[0])
        cloudwatch.put_metric_data.assert_called_once()
        self.assertEqual(
            cloudwatch.put_metric_data.call_args.kwargs["MetricData"][0]["MetricName"],
            "RestoreDrillFailure",
        )

    def test_rejects_non_disposable_target_before_s3_access(self):
        environment = self.environment()
        environment["RESTORE_TARGET_SITE"] = "erp.example.org"
        s3 = Mock()
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(restore_drill.RestoreDrillError, "disposable"):
                restore_drill.run_restore_drill(s3=s3, cloudwatch=Mock())
        s3.get_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
