from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts" / "check-terraform-plan.py"


class TerraformPlanPolicyTest(unittest.TestCase):
    def run_checker(self, changes: list[dict]) -> subprocess.CompletedProcess[str]:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"format_version": "1.2", "terraform_version": "1.13.5", "resource_changes": changes}, handle)
            path = Path(handle.name)
        try:
            return subprocess.run(
                [str(CHECKER), str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            path.unlink()

    def test_accepts_non_destructive_aws_plan(self):
        result = self.run_checker([{
            "address": "aws_ecs_service.web",
            "type": "aws_ecs_service",
            "change": {"actions": ["update"], "after": {"desired_count": 1}},
        }])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["destructive_changes"], 0)

    def test_rejects_destroy_and_secret_state(self):
        result = self.run_checker([{
            "address": "aws_secretsmanager_secret_version.example",
            "type": "aws_secretsmanager_secret_version",
            "change": {"actions": ["delete", "create"], "after": {"secret_string": "redacted"}},
        }])
        self.assertEqual(result.returncode, 1)
        self.assertIn("destructive action", result.stderr)
        self.assertIn("secret material", result.stderr)


if __name__ == "__main__":
    unittest.main()
