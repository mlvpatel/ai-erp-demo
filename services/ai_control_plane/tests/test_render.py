import hashlib
import unittest
from uuid import uuid4

from pydantic import ValidationError

from ai_erp_control_plane.models import ServiceCloseoutSummaryRequest
from ai_erp_control_plane.render import render_development_template


def _hash(value):
	return hashlib.sha256(value.encode()).hexdigest()


def _valid_request_payload():
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": "demo.localhost",
		"requested_by": "technician@example.test",
		"work_order": {
			"doctype": "Service Work Order",
			"name": "SVC-WO-00001",
			"subject": "Inspect pump",
			"status": "Closeout Submitted",
			"description": "Investigate noise.",
			"closeout_notes": "Tightened the mount.",
			"time_entries": [
				{
					"technician": "technician@example.test",
					"work_date": "2026-07-10",
					"time_type": "Work",
					"hours": 1.5,
				}
			],
			"parts": [],
		},
		"sources": [
			{
				"doctype": "Service Work Order",
				"name": "SVC-WO-00001",
				"field": "closeout_notes",
				"content_hash": _hash("Tightened the mount."),
			}
		],
	}


class TestDevelopmentTemplate(unittest.TestCase):
	def test_response_is_draft_only_and_carries_exact_sources(self):
		request = ServiceCloseoutSummaryRequest.model_validate(_valid_request_payload())

		response = render_development_template(request)

		self.assertEqual(response.policy.decision, "draft_only")
		self.assertEqual(response.policy.allowed_action, "none")
		self.assertEqual(response.sources, request.sources)
		self.assertEqual(response.model.provider, "development-template")
		self.assertIn("Tightened the mount.", response.draft_content)

	def test_related_history_is_cited_bounded_and_absent_when_empty(self):
		payload = _valid_request_payload()
		history_entry = {
			"name": "SVC-WO-00000",
			"subject": "Prior pump repair",
			"status": "Closed",
			"inspection_result": "Passed",
			"closeout_notes": "Replaced the seal.",
		}
		payload["work_order"]["related_history"] = [history_entry]
		payload["sources"].append(
			{
				"doctype": "Service Work Order",
				"name": "SVC-WO-00000",
				"field": "history",
				"content_hash": _hash("Replaced the seal."),
			}
		)
		request = ServiceCloseoutSummaryRequest.model_validate(payload)

		response = render_development_template(request)

		self.assertIn("Prior related work (cited)", response.draft_content)
		self.assertIn("SVC-WO-00000: Prior pump repair (Closed)", response.draft_content)
		self.assertIn("Replaced the seal.", response.draft_content)
		self.assertEqual(response.sources, request.sources)

		empty_payload = _valid_request_payload()
		empty_request = ServiceCloseoutSummaryRequest.model_validate(empty_payload)
		self.assertNotIn("Prior related work", render_development_template(empty_request).draft_content)

		bounded = _valid_request_payload()
		bounded["work_order"]["related_history"] = [history_entry] * 6
		with self.assertRaises(ValidationError):
			ServiceCloseoutSummaryRequest.model_validate(bounded)

	def test_rejects_unsupported_erp_record_payload(self):
		payload = _valid_request_payload()
		payload["work_order"]["doctype"] = "Sales Invoice"

		with self.assertRaises(ValidationError):
			ServiceCloseoutSummaryRequest.model_validate(payload)

	def test_rejects_extra_action_request_fields(self):
		payload = _valid_request_payload()
		payload["requested_action"] = "submit_sales_invoice"

		with self.assertRaises(ValidationError):
			ServiceCloseoutSummaryRequest.model_validate(payload)
