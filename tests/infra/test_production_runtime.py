from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "infra" / "images" / "frappe" / "runtime.sh"


class ProductionRuntimeConfigureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.bench_root = self.root / "bench"
        self.bin_dir = self.root / "bin"
        self.log_path = self.root / "bench.log"
        self.bench_root.mkdir()
        self.bin_dir.mkdir()
        fake_bench = self.bin_dir / "bench"
        fake_bench.write_text(
            """#!/bin/sh
set -eu
printf '%s\\n' "$*" >>"${BENCH_LOG}"
if [ "${1:-}" = "new-site" ]; then
  mkdir -p "${BENCH_ROOT}/sites/${2}"
  printf '{}\\n' >"${BENCH_ROOT}/sites/${2}/site_config.json"
elif [ "${1:-}" = "--site" ] && [ "${3:-}" = "list-apps" ]; then
  printf 'erpnext\\nai_erp_core\\nai_erp_service\\n'
fi
""",
            encoding="utf-8",
        )
        fake_bench.chmod(0o755)

    def environment(self, *, include_creation_secrets: bool = True) -> dict[str, str]:
        environment = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "BENCH_ROOT": str(self.bench_root),
            "BENCH_LOG": str(self.log_path),
            "SITE_NAME": "pilot.example.test",
            "DB_HOST": "database.internal",
            "REDIS_CACHE": "rediss://cache.internal:6379",
            "REDIS_QUEUE": "rediss://queue.internal:6379",
        }
        if include_creation_secrets:
            environment.update(
                {
                    "DB_ROOT_USERNAME": "erpadmin",
                    "DB_ROOT_PASSWORD": "<synthetic-root-password>",
                    "FRAPPE_ADMIN_PASSWORD": "<synthetic-admin-password>",
                    "FRAPPE_DB_NAME": "pilot_erp",
                    "FRAPPE_DB_PASSWORD": "<synthetic-site-password>",
                }
            )
        return environment

    def run_configure(self, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(RUNTIME), "configure"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_fresh_site_is_created_with_required_apps_and_registry(self) -> None:
        result = self.run_configure(self.environment())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            (self.bench_root / "sites" / "apps.txt").read_text(encoding="utf-8").splitlines(),
            ["frappe", "erpnext", "ai_erp_core", "ai_erp_service"],
        )
        log = self.log_path.read_text(encoding="utf-8")
        self.assertIn("new-site pilot.example.test", log)
        self.assertIn("--install-app erpnext --install-app ai_erp_core --install-app ai_erp_service", log)
        self.assertIn("use pilot.example.test", log)

    def test_existing_site_is_idempotent_without_creation_secrets(self) -> None:
        first = self.run_configure(self.environment())
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.log_path.read_text(encoding="utf-8").count("new-site ")

        second = self.run_configure(self.environment(include_creation_secrets=False))
        self.assertEqual(second.returncode, 0, second.stderr)
        after = self.log_path.read_text(encoding="utf-8").count("new-site ")
        self.assertEqual(before, after)

    def test_fresh_site_fails_closed_without_creation_secrets(self) -> None:
        result = self.run_configure(self.environment(include_creation_secrets=False))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DB_ROOT_USERNAME is required for a new site", result.stderr)
        self.assertFalse((self.bench_root / "sites" / "pilot.example.test").exists())


if __name__ == "__main__":
    unittest.main()
