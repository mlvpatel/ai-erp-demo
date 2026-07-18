import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ai_erp_control_plane.app import app


PROPOSAL_PATH = "/v1/proposals/service-closeout-summary"
SHARED_SECRET = "example-shared-secret"


def _valid_request_payload():
	return {
		"schema_version": 1,
		"request_id": "00000000-0000-4000-8000-000000000001",
		"tenant_site": "demo.localhost",
		"requested_by": "technician@example.test",
		"work_order": {
			"doctype": "Service Work Order",
			"name": "SVC-WO-00001",
			"subject": "Inspect pump",
			"status": "Closeout Submitted",
			"description": "Investigate noise.",
			"closeout_notes": "Tightened the mount.",
			"time_entries": [],
			"parts": [],
		},
		"sources": [
			{
				"doctype": "Service Work Order",
				"name": "SVC-WO-00001",
				"field": "closeout_notes",
				"content_hash": "0" * 64,
			}
		],
	}


class TestAppSecurity(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.client = TestClient(app)

	def _post(self, authorization=None):
		headers = {"Authorization": authorization} if authorization is not None else {}
		return self.client.post(PROPOSAL_PATH, headers=headers, json=_valid_request_payload())

	def test_rejects_missing_empty_and_wrong_bearer_tokens(self):
		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "template",
		}
		with patch.dict(os.environ, environment, clear=True):
			for authorization in (None, "Bearer", "Bearer wrong-secret"):
				with self.subTest(authorization=authorization):
					self.assertEqual(self._post(authorization).status_code, 401)

	def test_fails_closed_when_shared_secret_is_unset(self):
		with patch.dict(os.environ, {"AI_ERP_PROVIDER": "template"}, clear=True):
			response = self._post(f"Bearer {SHARED_SECRET}")

		self.assertEqual(response.status_code, 401)

	def test_rejects_unapproved_provider(self):
		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "unapproved-provider",
		}
		with patch.dict(os.environ, environment, clear=True):
			response = self._post(f"Bearer {SHARED_SECRET}")

		self.assertEqual(response.status_code, 503)

	def test_accepts_valid_service_key_for_template_provider(self):
		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "template",
		}
		with patch.dict(os.environ, environment, clear=True):
			response = self._post(f"Bearer {SHARED_SECRET}")

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()["policy"]["decision"], "draft_only")

	def test_openai_provider_without_key_fails_closed(self):
		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "openai",
		}
		with patch.dict(os.environ, environment, clear=True):
			with self.assertLogs("ai_erp_control_plane.provider", level="INFO") as captured:
				response = self._post(f"Bearer {SHARED_SECRET}")

		self.assertEqual(response.status_code, 503)
		self.assertEqual(response.json()["detail"], "approved model provider is unavailable")
		joined = " ".join(captured.output)
		self.assertIn("ai_provider_attempt", joined)
		self.assertIn("ai_provider_failure", joined)
		for sensitive in (SHARED_SECRET, "demo.localhost", "SVC-WO-00001", "Tightened the mount"):
			self.assertNotIn(sensitive, joined)

	def test_readiness_is_separate_from_liveness_and_fails_closed(self):
		with patch.dict(os.environ, {"AI_ERP_PROVIDER": "openai"}, clear=True):
			self.assertEqual(self.client.get("/healthz").status_code, 200)
			self.assertEqual(self.client.get("/readyz").status_code, 503)
		with patch.dict(os.environ, {"AI_ERP_PROVIDER": "template"}, clear=True):
			self.assertEqual(self.client.get("/readyz").status_code, 200)
		with patch.dict(os.environ, {"AI_ERP_PROVIDER": "unapproved"}, clear=True):
			self.assertEqual(self.client.get("/readyz").status_code, 503)

	def test_scheduling_route_requires_service_key_and_strict_payload(self):
		scheduling_payload = {
			"schema_version": 1,
			"request_id": "00000000-0000-4000-8000-000000000002",
			"tenant_site": "demo.localhost",
			"requested_by": "dispatcher@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-00002",
				"subject": "Quarterly pump service",
				"status": "Draft",
			},
			"candidates": [],
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "SVC-WO-00002",
					"field": "scheduling",
					"content_hash": "0" * 64,
				}
			],
		}
		environment = {
			"AI_CONTROL_PLANE_SHARED_SECRET": "example-shared-secret",
			"AI_ERP_PROVIDER": "template",
		}
		with patch.dict(os.environ, environment, clear=True):
			denied = self.client.post("/v1/proposals/scheduling-explanation", json=scheduling_payload)
			self.assertEqual(denied.status_code, 401)

			accepted = self.client.post(
				"/v1/proposals/scheduling-explanation",
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
				json=scheduling_payload,
			)
			self.assertEqual(accepted.status_code, 200)
			self.assertEqual(accepted.json()["policy"]["decision"], "draft_only")

			rejected = self.client.post(
				"/v1/proposals/scheduling-explanation",
				headers={"Authorization": f"Bearer {SHARED_SECRET}"},
				json={**scheduling_payload, "requested_action": "assign_technician"},
			)
			self.assertEqual(rejected.status_code, 422)

	def test_rejects_empty_identifiers_bad_dates_non_finite_and_out_of_range_numbers(self):
		invalid_mutations = (
			lambda payload: payload["work_order"].update({"name": ""}),
			lambda payload: payload["work_order"].update(
				{"time_entries": [{"technician": "", "work_date": "2026-13-40", "time_type": "Work", "hours": 1}]}
			),
			lambda payload: payload["work_order"].update(
				{"time_entries": [{"technician": "tech", "work_date": "2026-07-10", "time_type": "Work", "hours": "NaN"}]}
			),
			lambda payload: payload["work_order"].update(
				{"parts": [{"item": "PART", "qty": 100001, "source_warehouse": "WH", "issued": False}]}
			),
		)
		environment = {"AI_CONTROL_PLANE_SHARED_SECRET": SHARED_SECRET, "AI_ERP_PROVIDER": "template"}
		with patch.dict(os.environ, environment, clear=True):
			for mutate in invalid_mutations:
				payload = _valid_request_payload()
				mutate(payload)
				response = self.client.post(
					PROPOSAL_PATH,
					headers={"Authorization": f"Bearer {SHARED_SECRET}"},
					json=payload,
				)
				self.assertEqual(response.status_code, 422)
