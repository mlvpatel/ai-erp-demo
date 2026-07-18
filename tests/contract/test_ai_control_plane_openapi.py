import unittest
from pathlib import Path

import yaml
from pydantic import ValidationError

from ai_erp_control_plane.app import app
from ai_erp_control_plane.models import ServiceCloseoutSummaryRequest


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "contracts" / "openapi" / "ai-control-plane-v1.yaml"
HEALTH_PATH = "/healthz"
READY_PATH = "/readyz"
SERVICE_CLOSEOUT_PATH = "/v1/proposals/service-closeout-summary"
SCHEDULING_PATH = "/v1/proposals/scheduling-explanation"
HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})
EXPECTED_RESPONSES = {
	(HEALTH_PATH, "get"): frozenset({"200"}),
	(READY_PATH, "get"): frozenset({"200", "503"}),
	(SERVICE_CLOSEOUT_PATH, "post"): frozenset({"200", "401", "422", "503"}),
	(SCHEDULING_PATH, "post"): frozenset({"200", "401", "422"}),
}


class TestAIControlPlaneOpenAPIContract(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.contract_text = CONTRACT_PATH.read_text()
		cls.contract = yaml.safe_load(cls.contract_text)
		cls.openapi = app.openapi()

	def assert_contract_contains(self, *snippets):
		for snippet in snippets:
			with self.subTest(snippet=snippet):
				self.assertIn(snippet, self.contract_text)

	def test_route_metadata_matches_published_contract(self):
		self.assert_contract_contains(
			"openapi: 3.1.0",
			"title: AI ERP Control Plane API",
			"version: 1.3.0",
			f"  {SERVICE_CLOSEOUT_PATH}:",
			f"  {SCHEDULING_PATH}:",
			"operationId: draftServiceCloseoutSummary",
			"operationId: draftSchedulingExplanation",
			"const: scheduling_explanation",
			"ControlPlaneServiceKey: []",
		)

		self.assertEqual(self.openapi["openapi"], "3.1.0")
		self.assertEqual(self.openapi["info"]["title"], "AI ERP Control Plane API")
		self.assertEqual(self.openapi["info"]["version"], "1.3.0")

		operation = self.openapi["paths"][SERVICE_CLOSEOUT_PATH]["post"]
		self.assertEqual(operation["operationId"], "draftServiceCloseoutSummary")
		self.assertEqual(operation["security"], [{"ControlPlaneServiceKey": []}])
		self.assertIn("200", operation["responses"])
		self.assertIn("401", operation["responses"])
		self.assertIn("422", operation["responses"])

	def test_health_and_provider_unavailable_responses_are_published(self):
		self.assert_contract_contains(
			f"  {HEALTH_PATH}:",
			"security: []",
			"'503':",
			"The selected approved model provider is unavailable.",
		)

		health_operation = self.openapi["paths"][HEALTH_PATH]["get"]
		self.assertNotIn("security", health_operation)
		self.assertIn("200", health_operation["responses"])

		proposal_operation = self.openapi["paths"][SERVICE_CLOSEOUT_PATH]["post"]
		self.assertIn("503", proposal_operation["responses"])
		ready_operation = self.openapi["paths"][READY_PATH]["get"]
		self.assertNotIn("security", ready_operation)
		self.assertEqual(set(ready_operation["responses"]), {"200", "503"})

	def test_path_and_response_sets_match_exactly(self):
		contract_paths = self.contract["paths"]
		generated_paths = self.openapi["paths"]
		expected_paths = {path for path, _method in EXPECTED_RESPONSES}
		self.assertEqual(set(contract_paths), expected_paths)
		self.assertEqual(set(generated_paths), set(contract_paths))

		for (path, method), expected_responses in EXPECTED_RESPONSES.items():
			with self.subTest(path=path, method=method):
				contract_item = contract_paths[path]
				generated_item = generated_paths[path]
				self.assertEqual(set(contract_item) & HTTP_METHODS, {method})
				self.assertEqual(set(generated_item) & HTTP_METHODS, {method})

				contract_responses = contract_item[method]["responses"]
				generated_responses = generated_item[method]["responses"]
				self.assertEqual(set(contract_responses), expected_responses)
				self.assertEqual(set(generated_responses), set(contract_responses))

		contract_health = contract_paths[HEALTH_PATH]["get"]
		generated_health = generated_paths[HEALTH_PATH]["get"]
		self.assertEqual(contract_health.get("security", []), [])
		self.assertEqual(generated_health.get("security", []), [])

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

		for schema_name, field_constraints in {
			"TimeEntry": {
				"technician": {"minLength": 1, "maxLength": 256},
				"work_date": {"format": "date"},
				"time_type": {"minLength": 1, "maxLength": 128},
				"hours": {"exclusiveMinimum": 0, "maximum": 24},
			},
			"PartUsage": {
				"item": {"minLength": 1, "maxLength": 256},
				"qty": {"exclusiveMinimum": 0, "maximum": 100000},
				"source_warehouse": {"minLength": 1, "maxLength": 256},
			},
			"RelatedWorkSummary": {
				"name": {"minLength": 1, "maxLength": 256},
				"subject": {"minLength": 1, "maxLength": 256},
				"status": {"minLength": 1, "maxLength": 128},
				"inspection_result": {"maxLength": 128},
				"closeout_notes": {"maxLength": 4000},
			},
		}.items():
			for fieldname, constraints in field_constraints.items():
				for key, expected in constraints.items():
					self.assertEqual(
						schemas[schema_name]["properties"][fieldname][key],
						expected,
					)
					self.assertEqual(
						self.contract["components"]["schemas"][schema_name]["properties"][fieldname][key],
						expected,
					)

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
