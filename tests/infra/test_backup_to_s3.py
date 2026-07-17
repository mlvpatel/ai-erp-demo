from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "infra" / "images" / "frappe" / "backup_to_s3.py"
SPEC = importlib.util.spec_from_file_location("backup_to_s3", MODULE_PATH)
backup_to_s3 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(backup_to_s3)


class BackupUploadTest(unittest.TestCase):
    def create_set(self, root: Path) -> None:
        for name in (
            "20260714-site-database.sql.gz",
            "20260714-site-files.tar",
            "20260714-site-private-files.tar",
            "20260714-site-site_config_backup.json",
        ):
            (root / name).write_bytes((name + " synthetic").encode())

    def test_uploads_verified_artifacts_then_manifest_and_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_set(root)
            s3 = Mock()
            def head_object(*, Bucket, Key):
                if Key.endswith("/manifest.json"):
                    body = s3.put_object.call_args.kwargs["Body"]
                    return {"ContentLength": len(body), "Metadata": {"backup-status": "complete"}}
                path = next(path for path in root.iterdir() if path.name == Key.rsplit("/", 1)[-1])
                return {"ContentLength": path.stat().st_size, "Metadata": {"sha256": backup_to_s3.digest(path)}}

            s3.head_object.side_effect = head_object
            cloudwatch = Mock()
            result = backup_to_s3.upload_backup(
                backup_dir=root,
                bucket="private-backups",
                site="erp.example.org",
                kms_key_arn="arn:aws:kms:eu-central-1:000000000000:key/example",
                started_epoch=0,
                s3=s3,
                cloudwatch=cloudwatch,
                environment="pilot",
                now=datetime(2026, 7, 14, tzinfo=timezone.utc),
            )
            self.assertEqual(len(result["artifacts"]), 4)
            self.assertEqual(s3.upload_file.call_count, 4)
            s3.put_object.assert_called_once()
            cloudwatch.put_metric_data.assert_called_once()
            self.assertEqual(list(root.iterdir()), [])

    def test_incomplete_set_fails_before_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "20260714-site-database.sql.gz").write_bytes(b"synthetic")
            s3 = Mock()
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                backup_to_s3.upload_backup(
                    backup_dir=root,
                    bucket="private-backups",
                    site="erp.example.org",
                    kms_key_arn="arn:aws:kms:eu-central-1:000000000000:key/example",
                    started_epoch=0,
                    s3=s3,
                    cloudwatch=Mock(),
                    environment="pilot",
                )
            s3.upload_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
