"""Replay harness test verifying that AI Proposals remain draft-only and cited."""

import json
import os
import re
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_erp_control_plane.app import app

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "replay-bundles"
EVIDENCE_PACKET_DIR = REPO_ROOT / "tests" / "fixtures" / "evidence-packets"
EXPECTED_BUNDLES = {
	"closeout_summary.json",
	"repair_memory.json",
	"scheduling_explanation.json",
	"exception_recovery.json",
}
EXPECTED_EVIDENCE_PACKETS = {
	"finance_handoff.json",
}
FORBIDDEN_PACKET_KEYS = (
	"draft_content",
	"prompt",
	"prompt_version",
	"provider_response",
	"raw_response",
)
REQUIRED_FINANCE_STAGES = (
	"request_identity",
	"execution",
	"ai_proposals",
	"finance_handoff",
	"completeness",
)
# Bundles carry relative date markers such as "@today+3" instead of literal dates.
# An absolute date in a fixture silently becomes "in the past" and stops
# exercising the case it was written for.
TODAY_OFFSET_PATTERN = re.compile(r"@today(?P<offset>[+-]\d+)?")
ABSOLUTE_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def expand_relative_dates(value):
	"""Replace @today markers with dates resolved at run time."""
	if isinstance(value, dict):
		return {key: expand_relative_dates(item) for key, item in value.items()}
	if isinstance(value, list):
		return [expand_relative_dates(item) for item in value]
	if isinstance(value, str):
		return TODAY_OFFSET_PATTERN.sub(
			lambda match: (date.today() + timedelta(days=int(match.group("offset") or 0))).isoformat(),
			value,
		)
	return value


class TestReplayHarness(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = TestClient(app)

	def test_bundle_dates_stay_relative(self):
		for bundle_file in sorted(FIXTURES_DIR.glob("*.json")):
			with self.subTest(bundle=bundle_file.name):
				raw = bundle_file.read_text(encoding="utf-8")
				self.assertEqual(
					ABSOLUTE_DATE.findall(raw),
					[],
					f"{bundle_file.name} must use @today tokens instead of absolute dates.",
				)

	def test_bundle_history_is_cited(self):
		for bundle_file in sorted(FIXTURES_DIR.glob("*.json")):
			with self.subTest(bundle=bundle_file.name):
				payload = json.loads(bundle_file.read_text(encoding="utf-8"))["payload"]
				history = payload.get("related_history") or payload.get("work_order", {}).get(
					"related_history", []
				)
				cited = {source["name"] for source in payload["sources"]}
				uncited = [entry["name"] for entry in history if entry["name"] not in cited]
				self.assertEqual(
					uncited,
					[],
					f"{bundle_file.name} supplies prior work without a matching source citation.",
				)

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
					payload = expand_relative_dates(bundle["payload"])
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
						json=expand_relative_dates(bundle["payload"]),
					)
				self.assertEqual(response.status_code, 401)

	def test_finance_handoff_evidence_packet_fixture(self):
		packet_files = sorted(EVIDENCE_PACKET_DIR.glob("*.json"))
		self.assertTrue(packet_files, "At least one evidence-packet fixture must exist.")
		self.assertEqual(
			{path.name for path in packet_files},
			EXPECTED_EVIDENCE_PACKETS,
			"Evidence-packet harness must include finance-handoff packaging.",
		)

		for packet_file in packet_files:
			with self.subTest(packet=packet_file.name):
				fixture = json.loads(packet_file.read_text(encoding="utf-8"))
				self.assertEqual(fixture.get("packet_kind"), "evidence_to_cash_ledger")
				packet = fixture["packet"]
				self._assert_synthetic_domains(packet)
				self._assert_finance_handoff_packet(packet)

	def _assert_finance_handoff_packet(self, packet):
		serialized = json.dumps(packet)
		for forbidden in FORBIDDEN_PACKET_KEYS:
			self.assertNotIn(forbidden, serialized)
		self.assertEqual(packet["packet_kind"], "evidence_to_cash_ledger")
		self.assertTrue(packet.get("sales_invoice"))
		self.assertTrue(packet.get("stock_entries"))
		self.assertIn("ledger_narrative", packet)
		self.assertFalse(packet["ledger_narrative"].get("incomplete", False))
		self.assertTrue(packet.get("proposal_idempotency"))
		self.assertEqual(len(packet["proposal_idempotency"][0]["input_context_hash"]), 64)
		self.assertIn("Identical input_context_hash", packet["proposal_idempotency"][0]["reuse_note"])
		stages = [row["stage"] for row in packet["ledger_narrative"]["stages"]]
		for required in REQUIRED_FINANCE_STAGES:
			self.assertIn(required, stages)
		finance_stage = next(
			row for row in packet["ledger_narrative"]["stages"] if row["stage"] == "finance_handoff"
		)
		self.assertIn(packet["sales_invoice"], finance_stage["summary"])
		self.assertEqual(len(packet["chain_hash"]), 64)
		self.assertIn("Synthetic export evidence", packet["synthetic_note"])
		self.assertNotIn("submit invoice", serialized.casefold())
		self.assertNotIn("post stock", serialized.casefold())

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
