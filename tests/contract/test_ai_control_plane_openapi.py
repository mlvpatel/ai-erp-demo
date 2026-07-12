import unittest
from pathlib import Path

from pydantic import ValidationError

from ai_erp_control_plane.app import app
from ai_erp_control_plane.models import ServiceCloseoutSummaryRequest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts" / "openapi" / "ai-control-plane-v1.yaml"
SERVICE_CLOSEOUT_PATH = "/v1/proposals/service-closeout-summary"


class TestAIControlPlaneOpenAPIContract(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.contract_text = CONTRACT_PATH.read_text()
		cls.openapi = app.openapi()

	def assert_contract_contains(self, *snippets):
		for snippet in snippets:
			with self.subTest(snippet=snippet):
				self.assertIn(snippet, self.contract_text)

	def test_route_metadata_matches_published_contract(self):
		self.assert_contract_contains(
			"openapi: 3.1.0",
			"title: AI ERP Control Plane API",
			"version: 1.0.0",
			f"  {SERVICE_CLOSEOUT_PATH}:",
			"operationId: draftServiceCloseoutSummary",
			"ControlPlaneServiceKey: []",
		)

		self.assertEqual(self.openapi["openapi"], "3.1.0")
		self.assertEqual(self.openapi["info"]["title"], "AI ERP Control Plane API")
		self.assertEqual(self.openapi["info"]["version"], "1.0.0")

		operation = self.openapi["paths"][SERVICE_CLOSEOUT_PATH]["post"]
		self.assertEqual(operation["operationId"], "draftServiceCloseoutSummary")
		self.assertEqual(operation["security"], [{"ControlPlaneServiceKey": []}])
		self.assertIn("200", operation["responses"])
		self.assertIn("401", operation["responses"])
		self.assertIn("422", operation["responses"])

	def test_security_scheme_matches_published_contract(self):
		self.assert_contract_contains(
			"ControlPlaneServiceKey:",
			"type: http",
			"scheme: bearer",
			"bearerFormat: opaque-service-key",
		)

		scheme = self.openapi["components"]["securitySchemes"]["ControlPlaneServiceKey"]
		self.assertEqual(scheme["type"], "http")
		self.assertEqual(scheme["scheme"], "bearer")
		self.assertEqual(scheme["bearerFormat"], "opaque-service-key")

	def test_schema_guardrails_match_published_contract(self):
		self.assert_contract_contains(
			"additionalProperties: false",
			"const: 1",
			"const: Service Work Order",
			"const: service_closeout_summary",
			"const: draft_only",
			"const: none",
			"pattern: '^[a-f0-9]{64}$'",
		)

		schemas = self.openapi["components"]["schemas"]

		request_schema = schemas["ServiceCloseoutSummaryRequest"]
		self.assertFalse(request_schema["additionalProperties"])
		self.assertCountEqual(
			request_schema["required"],
			[
				"schema_version",
				"request_id",
				"tenant_site",
				"requested_by",
				"work_order",
				"sources",
			],
		)

		work_order_ref = request_schema["properties"]["work_order"]["$ref"]
		work_order_schema_name = work_order_ref.rsplit("/", 1)[1]
		work_order_schema = schemas[work_order_schema_name]
		self.assertFalse(work_order_schema["additionalProperties"])
		self.assertCountEqual(
			work_order_schema["required"],
			["doctype", "name", "subject", "status", "time_entries", "parts"],
		)
		self.assertEqual(work_order_schema["properties"]["doctype"]["const"], "Service Work Order")

		response_schema = schemas["ProposalResponse"]
		self.assertFalse(response_schema["additionalProperties"])
		self.assertCountEqual(
			response_schema["required"],
			[
				"schema_version",
				"request_id",
				"proposal_type",
				"policy",
				"model",
				"draft_content",
				"sources",
			],
		)
		self.assertEqual(response_schema["properties"]["proposal_type"]["const"], "service_closeout_summary")

		policy_ref = response_schema["properties"]["policy"]["$ref"]
		policy_schema = schemas[policy_ref.rsplit("/", 1)[1]]
		self.assertEqual(policy_schema["properties"]["decision"]["const"], "draft_only")
		self.assertEqual(policy_schema["properties"]["allowed_action"]["const"], "none")

	def test_runtime_model_rejects_unsupported_action_shape(self):
		payload = {
			"schema_version": 1,
			"request_id": "00000000-0000-4000-8000-000000000001",
			"tenant_site": "demo.localhost",
			"requested_by": "technician@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-00001",
				"subject": "Inspect pump",
				"status": "Closeout Submitted",
				"time_entries": [],
				"parts": [],
			},
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "SVC-WO-00001",
					"field": "status",
					"content_hash": "0" * 64,
				}
			],
			"requested_action": "submit_sales_invoice",
		}

		with self.assertRaises(ValidationError):
			ServiceCloseoutSummaryRequest.model_validate(payload)


if __name__ == "__main__":
	unittest.main()
