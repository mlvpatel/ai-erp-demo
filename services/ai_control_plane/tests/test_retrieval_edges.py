"""Negative and edge-case retrieval/abstention/leakage coverage for templates."""

import hashlib
import unittest
from uuid import uuid4

from pydantic import ValidationError

from ai_erp_control_plane.models import (
	ExceptionRecoveryRequest,
	RepairMemoryRequest,
	SchedulingExplanationRequest,
	ServiceCloseoutSummaryRequest,
)
from ai_erp_control_plane.render import (
	render_development_template,
	render_recovery_template,
	render_repair_memory_template,
	render_scheduling_template,
)


def _hash(value):
	return hashlib.sha256(value.encode()).hexdigest()


class TestRetrievalAbstentionAndLeakage(unittest.TestCase):
	def test_closeout_abstains_from_inventing_history_and_rejects_action_fields(self):
		payload = {
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "demo.localhost",
			"requested_by": "technician@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-EDGE-01",
				"subject": "No visible history",
				"status": "Closeout Submitted",
				"description": "Noise report.",
				"closeout_notes": "Checked mount only.",
				"time_entries": [
					{
						"technician": "technician@example.test",
						"work_date": "2026-07-24",
						"time_type": "Work",
						"hours": 1.0,
					}
				],
				"parts": [],
				"related_history": [],
			},
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "SVC-WO-EDGE-01",
					"field": "closeout_notes",
					"content_hash": _hash("Checked mount only."),
				}
			],
		}
		response = render_development_template(ServiceCloseoutSummaryRequest.model_validate(payload))
		self.assertEqual(response.policy.decision, "draft_only")
		self.assertNotIn("Prior related work", response.draft_content)
		self.assertNotIn("uncited-history-leak", response.draft_content)

		with self.assertRaises(ValidationError):
			ServiceCloseoutSummaryRequest.model_validate({**payload, "post_invoice": True})

	def test_repair_memory_rejects_uncited_history_fields_and_abstains_on_empty(self):
		payload = {
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "demo.localhost",
			"requested_by": "technician@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-EDGE-02",
				"subject": "Pump vibration edge",
				"status": "In Progress",
				"description": "Recurring vibration.",
			},
			"related_history": [],
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "SVC-WO-EDGE-02",
					"field": "repair_context",
					"content_hash": _hash("empty"),
				}
			],
		}
		abstention = render_repair_memory_template(RepairMemoryRequest.model_validate(payload))
		self.assertIn("Abstention", abstention.draft_content)
		self.assertIn("no repair suggestion is made", abstention.draft_content)
		self.assertNotIn("BEARING-KIT", abstention.draft_content)

		leaky = dict(payload)
		leaky["related_history"] = [
			{
				"name": "SVC-WO-HIDDEN",
				"subject": "Hidden prior visit",
				"status": "Closed",
				"closeout_notes": "Used BEARING-KIT at private site.",
				"parts": [{"item": "BEARING-KIT", "qty": 1, "issued": True}],
				"customer_email": "leak@example.org",
			}
		]
		with self.assertRaises(ValidationError):
			RepairMemoryRequest.model_validate(leaky)

	def test_scheduling_explanation_cannot_smuggle_assignment_or_foreign_domains(self):
		payload = {
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "demo.localhost",
			"requested_by": "dispatcher@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-EDGE-03",
				"subject": "Edge scheduling",
				"status": "Draft",
				"service_priority": "Low",
			},
			"candidates": [
				{
					"technician": "tech.a@example.test",
					"score": 0,
					"workload": 0,
					"familiarity": 0,
					"reasons": ["open_workload:0"],
				}
			],
			"excluded": [],
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "SVC-WO-EDGE-03",
					"field": "ranking",
					"content_hash": _hash("ranking"),
				}
			],
		}
		response = render_scheduling_template(SchedulingExplanationRequest.model_validate(payload))
		self.assertIn("ranking rests on open workload alone", response.draft_content)
		self.assertIn("cannot assign a technician", response.draft_content)

		with self.assertRaises(ValidationError):
			SchedulingExplanationRequest.model_validate(
				{**payload, "assign_to": "tech.a@example.test"}
			)

	def test_exception_recovery_abstains_on_other_without_history(self):
		payload = {
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "demo.localhost",
			"requested_by": "manager@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "SVC-WO-EDGE-04",
				"subject": "Weak recovery evidence",
				"status": "Cannot Close",
				"cannot_close_reason": "Other",
				"inspection_result": "",
			},
			"exception": {
				"name": "SVC-EXC-EDGE-01",
				"reason": "Other",
				"status": "Open",
				"due_date": "2026-07-25",
			},
			"parts": [],
			"related_history": [],
			"sources": [
				{
					"doctype": "Service Closure Exception",
					"name": "SVC-EXC-EDGE-01",
					"field": "reason",
					"content_hash": _hash("Other"),
				}
			],
		}
		response = render_recovery_template(ExceptionRecoveryRequest.model_validate(payload))
		self.assertIn("Abstention", response.draft_content)
		self.assertIn("no recovery recommendation is made", response.draft_content)
		self.assertEqual(response.policy.allowed_action, "none")

		with self.assertRaises(ValidationError):
			ExceptionRecoveryRequest.model_validate({**payload, "resolve_exception": True})


if __name__ == "__main__":
	unittest.main()
