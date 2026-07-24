"""Replay harness test verifying that AI Proposals remain draft-only and cited."""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_erp_control_plane.app import app

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "replay-bundles"
EXPECTED_BUNDLES = {
	"closeout_summary.json",
	"repair_memory.json",
	"scheduling_explanation.json",
	"exception_recovery.json",
}


class TestReplayHarness(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = TestClient(app)

	def test_replay_all_bundles(self):
		bundle_files = sorted(FIXTURES_DIR.glob("*.json"))
		self.assertTrue(bundle_files, "At least one replay bundle fixture must exist.")
		self.assertEqual(
			{path.name for path in bundle_files},
			EXPECTED_BUNDLES,
			"Replay harness must cover all registered proposal-type fixtures.",
		)

		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "template",
		}
		with patch.dict(os.environ, environment, clear=True):
			for bundle_file in bundle_files:
				with self.subTest(bundle=bundle_file.name):
					bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
					route = bundle["route"]
					payload = bundle["payload"]
					self.assertIn(
						bundle["proposal_type"],
						{
							"service_closeout_summary",
							"repair_memory",
							"scheduling_explanation",
							"exception_recovery",
						},
					)
					self._assert_synthetic_domains(payload)

					response = self.client.post(
						route,
						headers={"Authorization": "Bearer example-shared-secret"},
						json=payload,
					)
					self.assertEqual(
						response.status_code,
						200,
						f"Bundle {bundle_file.name} failed: {response.text}",
					)
					data = response.json()

					self.assertIn("policy", data)
					self.assertEqual(data["policy"]["decision"], "draft_only")
					self.assertEqual(data["policy"]["allowed_action"], "none")
					self.assertEqual(data["proposal_type"], bundle["proposal_type"])
					self.assertIn("sources", data)
					self.assertTrue(
						len(data["sources"]) > 0, "AI Proposal must carry source citations"
					)
					self.assertTrue(data.get("draft_content"))

	def test_replay_fails_closed_without_shared_secret(self):
		bundle_files = list(FIXTURES_DIR.glob("*.json"))
		self.assertTrue(bundle_files, "At least one replay bundle fixture must exist.")
		for bundle_file in bundle_files:
			with self.subTest(bundle=bundle_file.name):
				bundle = json.loads(bundle_file.read_text(encoding="utf-8"))
				with patch.dict(os.environ, {"AI_ERP_PROVIDER": "template"}, clear=True):
					response = self.client.post(
						bundle["route"],
						headers={"Authorization": "Bearer example-shared-secret"},
						json=bundle["payload"],
					)
				self.assertEqual(response.status_code, 401)

	def _assert_synthetic_domains(self, payload):
		serialized = json.dumps(payload)
		for banned in ("gmail.com", "yahoo.com", "customer.com", "realuser@"):
			self.assertNotIn(banned, serialized)
		self.assertTrue(
			"example.test" in serialized or "example.org" in serialized or "localhost" in serialized,
			"Replay fixtures must use allowlisted synthetic domains.",
		)


if __name__ == "__main__":
	unittest.main()
