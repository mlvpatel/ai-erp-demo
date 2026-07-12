import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
EVENT_CONTRACT_PATH = REPO_ROOT / "contracts" / "events" / "service-operations-v1.yaml"


class TestServiceOperationsEventContract(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.contract = yaml.safe_load(EVENT_CONTRACT_PATH.read_text())

	def test_catalog_metadata_is_versioned_and_not_claimed_as_implemented(self):
		self.assertEqual(self.contract["schema_version"], 1)
		self.assertEqual(self.contract["catalog"], "ai-erp-service-operations")
		self.assertEqual(self.contract["status"], "contract-only")

	def test_event_types_are_explicitly_versioned(self):
		event_types = self.contract["event_types"]
		self.assertEqual(len(event_types), len(set(event_types)))
		for event_type in event_types:
			with self.subTest(event_type=event_type):
				self.assertTrue(event_type.startswith("ai_erp."))
				self.assertTrue(event_type.endswith(".v1"))

		envelope_event_enum = self.contract["envelope"]["properties"]["event_type"]["enum"]
		self.assertCountEqual(event_types, envelope_event_enum)

	def test_envelope_is_strict_and_tenant_scoped(self):
		envelope = self.contract["envelope"]
		self.assertFalse(envelope["additionalProperties"])
		self.assertIn("tenant_site", envelope["required"])
		self.assertIn("actor", envelope["required"])
		self.assertIn("source", envelope["required"])
		self.assertIn("payload", envelope["required"])

	def test_payloads_are_strict_and_do_not_carry_sensitive_fields_or_mutation_instructions(self):
		for payload_name, payload_schema in self.contract["payloads"].items():
			with self.subTest(payload=payload_name):
				self.assertFalse(payload_schema["additionalProperties"])
				field_names = set(payload_schema["properties"])
				for forbidden in (
					"email",
					"phone",
					"address",
					"contact",
					"attachment",
					"prompt",
					"credential",
					"password",
					"submit",
					"cancel",
					"role",
					"permission",
					"ledger",
				):
					self.assertFalse(any(forbidden in field for field in field_names), forbidden)

	def test_ai_review_event_cannot_authorize_erp_action(self):
		payload = self.contract["payloads"]["AIProposalReviewed"]["properties"]
		self.assertEqual(payload["policy_decision"]["const"], "draft_only")
		self.assertEqual(payload["allowed_action"]["const"], "none")


if __name__ == "__main__":
	unittest.main()
