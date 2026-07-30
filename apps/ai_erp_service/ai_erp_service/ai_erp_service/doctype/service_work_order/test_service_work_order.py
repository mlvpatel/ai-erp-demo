# Copyright (c) 2026, AI ERP Demo and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, flt, get_datetime, now_datetime, today

from ai_erp_service.ai_drafts import request_closeout_summary
from ai_erp_service.ai_erp_service.doctype.service_request.service_request import create_service_work_order
from ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order import (
	_with_transaction_retry,
	issue_parts,
	make_draft_sales_invoice,
)
from ai_erp_service.ai_erp_service.report.service_profitability.service_profitability import (
	execute as profitability_report,
)
from ai_erp_service.demo_seed import prepare_e2e_demo, seed_service_demo
from ai_erp_service.evidence import get_evidence_timeline
from ai_erp_service.tasks import escalate_overdue_closure_exceptions

# This focused integration suite creates its synthetic dependencies directly.
# Avoid recursively loading unrelated ERPNext test-record modules.
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Customer",
	"AI Proposal",
	"AI Proposal Source",
	"Asset",
	"Item",
	"Price List",
	"Service Closure Exception",
	"Service Location",
	"Service Request",
	"Service Work Order Part",
	"Service Work Order Time",
	"Sales Invoice",
	"Stock Entry",
	"User",
	"Warehouse",
]


class IntegrationTestServiceWorkOrder(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.technician = self._make_technician()
		self.manager = self._make_role_user(
			"service.manager.finance-separation@example.test", ("Service Manager",)
		)
		self.finance_user = self._make_role_user(
			"service.finance@example.test", ("Accounts User",)
		)
		self.customer = self._make_customer()
		self.location = self._make_location()

	def test_request_creates_a_linked_draft_work_order(self):
		request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"subject": "Test request",
				"customer": self.customer,
				"service_location": self.location,
			}
		).insert()

		work_order_name = create_service_work_order(request.name)
		request.reload()
		work_order = frappe.get_doc("Service Work Order", work_order_name)

		self.assertEqual(request.status, "Triaged")
		self.assertEqual(request.service_work_order, work_order.name)
		self.assertEqual(work_order.service_request, request.name)
		self.assertEqual(work_order.status, "Draft")

	def test_transient_database_deadlock_is_retried(self):
		operation = Mock(side_effect=[frappe.QueryDeadlockError("retry"), "completed"])

		with (
			patch("frappe.db.rollback") as rollback,
			patch(
				"ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.sleep"
			),
		):
			self.assertEqual(_with_transaction_retry(operation), "completed")

		self.assertEqual(operation.call_count, 2)
		rollback.assert_called_once_with()

	def test_technician_scope_and_manager_only_close(self):
		invoices_before = frappe.db.count("Sales Invoice")
		assigned = self._make_work_order("Assigned work order")
		other = self._make_work_order("Other work order")
		self._schedule(assigned, self.technician)
		self._schedule(other, "Administrator")

		frappe.set_user(self.technician)
		visible = set(
			frappe.get_list(
				"Service Work Order",
				filters={"name": ["in", [assigned.name, other.name]]},
				pluck="name",
			)
		)
		self.assertEqual(visible, {assigned.name})
		self.assertFalse(assigned.has_permission("share"))
		self.assertFalse(assigned.has_permission("email"))
		self.assertFalse(other.has_permission("read"))

		assigned.reload()
		assigned.status = "In Progress"
		assigned.save()
		assigned.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		assigned.closeout_notes = "Work completed."
		assigned.closeout_evidence = "/private/files/test-closeout.txt"
		assigned.status = "Closeout Submitted"
		assigned.save()

		assigned.status = "Closed"
		with self.assertRaises(frappe.PermissionError):
			assigned.save()

		frappe.set_user("Administrator")
		assigned.reload()
		assigned.status = "Closed"
		assigned.save()
		assigned.status = "Invoice Ready"
		assigned.save()
		self.assertEqual(assigned.invoice_ready, 1)
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before)

	def test_cannot_close_creates_an_owned_exception(self):
		work_order = self._make_work_order("Blocked work order")
		self._schedule(work_order, self.technician)
		work_order.closure_owner = self.manager
		work_order.closure_due_date = today()
		work_order.save()

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.cannot_close_reason = "Parts unavailable"
		work_order.status = "Cannot Close"
		work_order.save()

		exception = frappe.get_doc("Service Closure Exception", work_order.closure_exception)
		self.assertEqual(exception.work_order, work_order.name)
		self.assertEqual(exception.exception_owner, self.manager)
		self.assertEqual(exception.status, "Open")

	def test_technician_cannot_mutate_manager_or_finance_fields(self):
		item, warehouse = self._make_stocked_item()
		work_order = self._make_work_order("Permission boundary work order")
		work_order.append(
			"parts",
			{"item": item, "qty": 1, "bill_rate": 25, "source_warehouse": warehouse},
		)
		self._schedule(work_order, self.technician)
		alternate_customer = self._make_customer()

		frappe.set_user(self.technician)
		for fieldname, value in (
			("customer", alternate_customer),
			("service_priority", "Critical"),
			("warranty_status", "In Warranty"),
			("inspection_required", 1),
			("scheduled_end", add_to_date(work_order.scheduled_end, hours=1)),
			("assigned_technician", "Administrator"),
			("hourly_rate", 999),
			("projected_revenue", 999),
		):
			work_order.reload()
			original = work_order.get(fieldname)
			work_order.set(fieldname, value)
			with self.assertRaises(frappe.PermissionError, msg=f"defense in depth: {fieldname}"):
				work_order._validate_technician_field_scope()
			try:
				work_order.save()
			except frappe.PermissionError:
				pass
			work_order.reload()
			self.assertEqual(work_order.get(fieldname), original, fieldname)

		work_order.reload()
		original_rate = work_order.parts[0].bill_rate
		work_order.parts[0].bill_rate = 999
		with self.assertRaises(frappe.PermissionError, msg="defense in depth: part bill rate"):
			work_order._validate_technician_field_scope()
		try:
			work_order.save()
		except frappe.PermissionError:
			pass
		work_order.reload()
		self.assertEqual(work_order.parts[0].bill_rate, original_rate)

	def test_service_foundation_gates_warranty_and_required_inspection(self):
		work_order = self._make_work_order("Asset SLA inspection work order")
		work_order.warranty_status = "In Warranty"
		with self.assertRaises(frappe.ValidationError):
			work_order.save()

		work_order.reload()
		work_order.warranty_status = "Unknown"
		work_order.inspection_required = 1
		work_order.save()
		self._schedule(work_order, self.technician)

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Inspection completed during service."
		work_order.closeout_evidence = "/private/files/test-inspection-closeout.txt"
		work_order.save()
		work_order.status = "Closeout Submitted"
		with self.assertRaises(frappe.ValidationError):
			work_order.save()

		work_order.reload()
		work_order.status = "Closeout Submitted"
		work_order.inspection_result = "Failed"
		with self.assertRaises(frappe.ValidationError):
			work_order.save()

		work_order.reload()
		work_order.status = "Closeout Submitted"
		work_order.inspection_result = "Failed"
		work_order.inspection_notes = "Pressure test failed; manager follow-up required."
		work_order.save()
		self.assertEqual(work_order.status, "Closeout Submitted")

	def test_technician_related_reads_are_limited_to_assigned_work(self):
		assigned_request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"subject": "Assigned request",
				"customer": self.customer,
				"service_location": self.location,
			}
		).insert()
		assigned = self._make_work_order("Assigned related records")
		assigned.service_request = assigned_request.name
		assigned.save()
		self._schedule(assigned, self.technician)

		other_customer = self._make_customer()
		other_location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Other Site {0}".format(frappe.generate_hash(length=8)),
				"customer": other_customer,
			}
		).insert()
		other_request = frappe.get_doc(
			{
				"doctype": "Service Request",
				"subject": "Unassigned request",
				"customer": other_customer,
				"service_location": other_location.name,
			}
		).insert()

		frappe.set_user(self.technician)
		self.assertTrue(frappe.get_doc("Service Request", assigned_request.name).has_permission("read"))
		self.assertTrue(frappe.get_doc("Service Location", self.location).has_permission("read"))
		self.assertFalse(frappe.get_doc("Service Request", other_request.name).has_permission("read"))
		self.assertFalse(frappe.get_doc("Service Location", other_location.name).has_permission("read"))
		self.assertFalse(frappe.get_doc("Service Request", assigned_request.name).has_permission("share"))
		self.assertFalse(frappe.get_doc("Service Location", self.location).has_permission("email"))

	def test_overdue_cannot_close_is_escalated_once_without_auto_close(self):
		work_order = self._make_work_order("Overdue blocked work order")
		self._schedule(work_order, self.technician)
		work_order.closure_owner = self.manager
		work_order.closure_due_date = today()
		work_order.save()

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.cannot_close_reason = "Parts unavailable"
		work_order.status = "Cannot Close"
		work_order.save()
		exception_name = work_order.closure_exception

		frappe.set_user("Administrator")
		frappe.db.set_value(
			"Service Closure Exception",
			exception_name,
			"due_date",
			add_to_date(today(), days=-1),
			update_modified=False,
		)
		escalate_overdue_closure_exceptions()
		first_count = frappe.db.count(
			"Notification Log",
			{"document_type": "Service Closure Exception", "document_name": exception_name},
		)
		escalate_overdue_closure_exceptions()

		work_order.reload()
		exception = frappe.get_doc("Service Closure Exception", exception_name)
		self.assertEqual(work_order.status, "Cannot Close")
		self.assertTrue(exception.escalated_on)
		self.assertGreaterEqual(first_count, 1)
		self.assertEqual(
			frappe.db.count(
				"Notification Log",
				{"document_type": "Service Closure Exception", "document_name": exception_name},
			),
			first_count,
		)

	def test_parts_issue_is_idempotent(self):
		item, warehouse = self._make_stocked_item()
		work_order = self._make_work_order("Parts issue work order")
		self._schedule(work_order, self.technician)

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"parts",
			{"item": item, "qty": 1, "source_warehouse": warehouse},
		)
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Part installed."
		work_order.closeout_evidence = "/private/files/test-parts-closeout.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		frappe.set_user("Administrator")
		stock_entry_name = issue_parts(work_order.name)
		work_order.reload()

		self.assertEqual(frappe.db.get_value("Stock Entry", stock_entry_name, "docstatus"), 1)
		self.assertEqual(work_order.parts[0].stock_entry, stock_entry_name)
		self.assertEqual(issue_parts(work_order.name), stock_entry_name)

	def test_finance_creates_idempotent_draft_sales_invoice(self):
		invoices_before = frappe.db.count("Sales Invoice")
		item, warehouse = self._make_stocked_item()
		service_item = self._make_service_item()
		work_order = self._make_work_order("Invoice-ready work order")
		self._schedule(work_order, self.technician)

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1.25,
			},
		)
		work_order.append(
			"parts",
			{"item": item, "qty": 2, "bill_rate": 25, "source_warehouse": warehouse},
		)
		work_order.closeout_notes = "Labor and part completed."
		work_order.closeout_evidence = "/private/files/test-invoice-closeout.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		frappe.set_user("Administrator")
		work_order.reload()
		work_order.parts[0].bill_rate = 25
		work_order.save()
		issue_parts(work_order.name)
		work_order.reload()
		work_order.service_billing_item = service_item
		work_order.hourly_rate = 80
		work_order.status = "Closed"
		work_order.save()
		work_order.status = "Invoice Ready"
		work_order.save()
		stock_entries_after_issue = frappe.db.count("Stock Entry")
		work_order.reload()
		expected_revenue = 150
		expected_cost = self._stock_entry_cost(work_order.parts[0].stock_entry)

		self.assertEqual(work_order.projected_revenue, expected_revenue)
		self.assertEqual(work_order.issued_parts_cost, expected_cost)
		self.assertEqual(work_order.projected_margin_before_labor, expected_revenue - expected_cost)
		self.assertEqual(
			flt(work_order.projected_margin_percent, 2),
			flt((expected_revenue - expected_cost) / expected_revenue * 100, 2),
		)
		self.assertIn("Labor overhead is excluded", work_order.profitability_basis)

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			make_draft_sales_invoice(work_order.name)

		frappe.set_user(self.manager)
		with self.assertRaises(frappe.PermissionError):
			make_draft_sales_invoice(work_order.name)

		frappe.set_user(self.finance_user)
		self.assertEqual(
			frappe.get_list(
				"Service Work Order", filters={"name": work_order.name}, pluck="name"
			),
			[work_order.name],
		)
		invoice_name = make_draft_sales_invoice(work_order.name)
		self.assertEqual(make_draft_sales_invoice(work_order.name), invoice_name)

		work_order.reload()
		invoice = frappe.get_doc("Sales Invoice", invoice_name)
		self.assertEqual(work_order.sales_invoice, invoice.name)
		self.assertEqual(invoice.service_work_order, work_order.name)
		self.assertEqual(invoice.customer, self.customer)
		self.assertEqual(invoice.docstatus, 0)
		self.assertEqual(invoice.update_stock, 0)
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before + 1)
		self.assertEqual(frappe.db.count("Stock Entry"), stock_entries_after_issue)

		items_by_code = {row.item_code: row for row in invoice.items}
		self.assertEqual(set(items_by_code), {service_item, item})
		self.assertEqual(items_by_code[service_item].qty, 1.25)
		self.assertEqual(items_by_code[service_item].rate, 80)
		self.assertEqual(items_by_code[item].qty, 2)
		self.assertEqual(items_by_code[item].rate, 25)

		frappe.set_user("Administrator")
		work_order.hourly_rate = 90
		with self.assertRaises(frappe.ValidationError):
			work_order.save()

	def test_ai_closeout_draft_is_cited_immutable_and_human_reviewed(self):
		invoices_before = frappe.db.count("Sales Invoice")
		stock_entries_before = frappe.db.count("Stock Entry")
		work_order = self._make_work_order("AI closeout work order")
		work_order.description = "Investigate a reported vibration."
		work_order.save()
		self._schedule(work_order, self.technician)

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1.5,
			},
		)
		work_order.closeout_notes = "Tightened the mount and confirmed normal operation."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		def control_plane_response(payload, route=None):
			return {
				"schema_version": 1,
				"request_id": payload["request_id"],
				"proposal_type": "service_closeout_summary",
				"policy": {
					"decision": "draft_only",
					"allowed_action": "none",
					"reason": "Draft only; human review has no ERP side effect.",
				},
				"model": {
					"provider": "test-control-plane",
					"name": "test-closeout-model",
					"prompt_version": "service-closeout-summary@v1",
				},
				"draft_content": "Draft: mount tightened; normal operation confirmed.",
				"sources": payload["sources"],
			}

		with patch("ai_erp_core.proposals._post_to_control_plane", side_effect=control_plane_response) as control_plane:
			result = request_closeout_summary(work_order.name)
			retry = request_closeout_summary(work_order.name)
			self.assertEqual(control_plane.call_count, 1)
			self.assertEqual(retry["name"], result["name"])

		proposal = frappe.get_doc("AI Proposal", result["name"])
		self.assertEqual(proposal.proposal_status, "Draft")
		self.assertEqual(proposal.policy_outcome, "Draft Only")
		self.assertEqual(proposal.requested_by, self.technician)
		self.assertEqual(proposal.reference_name, work_order.name)
		self.assertEqual(proposal.model_provider, "test-control-plane")
		self.assertIn("closeout_notes", {source.source_field for source in proposal.sources})
		self.assertNotIn("closeout_evidence", {source.source_field for source in proposal.sources})
		self.assertEqual(
			frappe.get_list("AI Proposal", filters={"name": proposal.name}, pluck="name"),
			[proposal.name],
		)
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before)
		self.assertEqual(frappe.db.count("Stock Entry"), stock_entries_before)

		proposal.draft_content = "Attempted edit"
		with self.assertRaises(frappe.PermissionError):
			proposal.save()

		frappe.set_user("Administrator")
		proposal.reload()
		proposal.draft_content = "Attempted edit"
		with self.assertRaises(frappe.ValidationError):
			proposal.save()

		proposal.reload()
		self.assertEqual(proposal.policy_category, "draft_only")
		proposal.review("Approved", "Reviewed against cited field evidence.")
		proposal.reload()
		work_order.reload()
		self.assertEqual(proposal.proposal_status, "Approved")
		self.assertEqual(proposal.reviewed_by, "Administrator")
		self.assertEqual(work_order.status, "Closeout Submitted")
		self.assertEqual(work_order.closeout_notes, "Tightened the mount and confirmed normal operation.")
		self.assertFalse(work_order.sales_invoice)
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before)
		self.assertEqual(frappe.db.count("Stock Entry"), stock_entries_before)

	def test_concurrent_identical_context_reuses_one_proposal_without_second_provider_call(self):
		"""Prove deadlock recovery + context-hash reuse converge on one proposal."""
		work_order = self._make_work_order("Concurrent proposal idempotency")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Verified airflow after filter change."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		def control_plane_response(payload, route=None):
			return {
				"schema_version": 1,
				"request_id": payload["request_id"],
				"proposal_type": "service_closeout_summary",
				"policy": {
					"decision": "draft_only",
					"allowed_action": "none",
					"category": "draft_only",
					"reason": "Draft only; human review has no ERP side effect.",
				},
				"model": {
					"provider": "test-control-plane",
					"name": "test-closeout-model",
					"prompt_version": "service-closeout-summary@v1",
				},
				"audit": {
					"response_id_hash": "a" * 64,
					"input_tokens": 11,
					"output_tokens": 7,
					"duration_ms": 33,
					"redaction_count": 0,
				},
				"draft_content": "Draft: filter changed; airflow verified.",
				"sources": payload["sources"],
			}

		with patch("ai_erp_core.proposals._post_to_control_plane", side_effect=control_plane_response) as control_plane:
			first = request_closeout_summary(work_order.name)
			proposal_name = first["name"]

			# Simulate a concurrent waiter that hit snapshot deadlock, then saw
			# the committed proposal on the fresh snapshot without calling provider.
			original_get_value = frappe.db.get_value
			calls = {"count": 0}

			def get_value_with_deadlock(*args, **kwargs):
				if kwargs.get("for_update") and calls["count"] == 0:
					calls["count"] += 1
					raise frappe.QueryDeadlockError("synthetic concurrent context lock")
				if kwargs.get("for_update"):
					return proposal_name
				return original_get_value(*args, **kwargs)

			with (
				patch("frappe.db.get_value", side_effect=get_value_with_deadlock),
				patch("frappe.db.rollback") as rollback,
				patch("ai_erp_core.proposals._lock_reference"),
			):
				second = request_closeout_summary(work_order.name)

			self.assertEqual(control_plane.call_count, 1)
			self.assertEqual(second["name"], proposal_name)
			rollback.assert_called()

		proposal = frappe.get_doc("AI Proposal", proposal_name)
		self.assertEqual(proposal.policy_category, "draft_only")
		self.assertEqual(proposal.provider_input_tokens, 11)
		self.assertEqual(proposal.provider_output_tokens, 7)
		self.assertEqual(proposal.provider_duration_ms, 33)
		self.assertEqual(
			frappe.db.count(
				"AI Proposal",
				{
					"reference_doctype": "Service Work Order",
					"reference_name": work_order.name,
					"input_context_hash": proposal.input_context_hash,
				},
			),
			1,
		)

	def test_closeout_draft_history_retrieval_is_permission_scoped_and_cited(self):
		other_technician = self._make_role_user(
			"service.technician.history@example.test", ("Service Technician",)
		)
		history = self._make_work_order("Historical pump repair")
		self._schedule(history, other_technician)
		frappe.set_user(other_technician)
		history.reload()
		history.status = "In Progress"
		history.save()
		history.append(
			"time_entries",
			{
				"technician": other_technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 2,
			},
		)
		history.closeout_notes = "Cleared debris and replaced the worn seal."
		history.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		history.status = "Closeout Submitted"
		history.save()
		frappe.set_user(self.manager)
		history.reload()
		history.status = "Closed"
		history.save()

		current = self._make_work_order("Repeat pump vibration")
		self._schedule(current, self.technician)
		frappe.set_user(self.technician)
		current.reload()
		current.status = "In Progress"
		current.save()
		current.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		current.closeout_notes = "Re-tightened the mount."
		current.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		current.status = "Closeout Submitted"
		current.save()

		def control_plane_response(payload, route=None):
			return {
				"schema_version": 1,
				"request_id": payload["request_id"],
				"proposal_type": "service_closeout_summary",
				"policy": {
					"decision": "draft_only",
					"allowed_action": "none",
					"reason": "Draft only; human review has no ERP side effect.",
				},
				"model": {
					"provider": "test-control-plane",
					"name": "test-closeout-model",
					"prompt_version": "service-closeout-summary@v1",
				},
				"draft_content": "Draft closeout with cited history.",
				"sources": payload["sources"],
			}

		with patch(
			"ai_erp_core.proposals._post_to_control_plane", side_effect=control_plane_response
		) as control_plane:
			request_closeout_summary(current.name)
		technician_payload = control_plane.call_args[0][0]
		self.assertEqual(technician_payload["work_order"]["related_history"], [])
		self.assertNotIn(
			"history", {source["field"] for source in technician_payload["sources"]}
		)

		frappe.set_user(self.manager)
		with patch(
			"ai_erp_core.proposals._post_to_control_plane", side_effect=control_plane_response
		) as control_plane:
			request_closeout_summary(current.name)
		manager_payload = control_plane.call_args[0][0]
		entries = manager_payload["work_order"]["related_history"]
		entry = next(row for row in entries if row["name"] == history.name)
		self.assertEqual(
			set(entry), {"name", "subject", "status", "inspection_result", "closeout_notes"}
		)
		self.assertEqual(entry["closeout_notes"], "Cleared debris and replaced the worn seal.")

		history_citations = {
			source["name"]
			for source in manager_payload["sources"]
			if source["field"] == "history"
		}
		self.assertIn(history.name, history_citations)
		visible_to_manager = set(
			frappe.get_list("Service Work Order", pluck="name", limit_page_length=0)
		)
		self.assertLessEqual(history_citations, visible_to_manager)

	def test_evidence_chain_is_role_scoped_hashed_and_explicit_about_gaps(self):
		from ai_erp_service.evidence import get_evidence_chain

		work_order = self._make_work_order("Evidence chain work order")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()

		incomplete = get_evidence_chain(work_order.name)
		self.assertFalse(incomplete["completeness"]["complete"])
		self.assertIn("time_entries", incomplete["completeness"]["missing"])
		self.assertNotIn("finance", incomplete["sections"])
		self.assertTrue(incomplete["ledger_narrative"]["incomplete"])
		self.assertIn("Incomplete evidence chain", incomplete["ledger_narrative"]["headline"])
		self.assertIn("time_entries", incomplete["ledger_narrative"]["headline"])

		frappe.set_user(self.finance_user)
		with self.assertRaises(frappe.PermissionError):
			get_evidence_chain(work_order.name)

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Verified repair and cleaned the work area."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		technician_chain = get_evidence_chain(work_order.name)
		self.assertTrue(technician_chain["completeness"]["complete"])
		self.assertNotIn("finance", technician_chain["sections"])
		self.assertEqual(
			technician_chain["sections"]["execution"]["closeout_notes"],
			"Verified repair and cleaned the work area.",
		)

		frappe.set_user(self.manager)
		work_order.reload()
		work_order.status = "Closed"
		work_order.save()
		work_order.status = "Invoice Ready"
		work_order.save()

		manager_chain = get_evidence_chain(work_order.name)
		self.assertIn("finance", manager_chain["sections"])
		self.assertIn("projected_revenue", manager_chain["sections"]["finance"])
		self.assertEqual(len(manager_chain["chain_hash"]), 64)
		self.assertEqual(manager_chain["chain_hash"], get_evidence_chain(work_order.name)["chain_hash"])
		self.assertNotEqual(manager_chain["chain_hash"], technician_chain["chain_hash"])
		self.assertEqual(
			set(manager_chain["section_hashes"]),
			set(manager_chain["sections"]),
		)
		self.assertIn("ledger_narrative", manager_chain)
		manager_stages = [row["stage"] for row in manager_chain["ledger_narrative"]["stages"]]
		self.assertIn("finance_handoff", manager_stages)
		self.assertIn("completeness", manager_stages)
		self.assertFalse(manager_chain["ledger_narrative"]["incomplete"])
		self.assertIn("Request → execution", manager_chain["ledger_narrative"]["headline"])

		technician_stages = [row["stage"] for row in technician_chain["ledger_narrative"]["stages"]]
		self.assertNotIn("finance_handoff", technician_stages)
		self.assertIn("execution", technician_stages)

		frappe.set_user(self.finance_user)
		finance_chain = get_evidence_chain(work_order.name)
		self.assertTrue(finance_chain["sections"]["finance"]["invoice_ready"])
		self.assertIn("sales_invoice", finance_chain["sections"]["finance"])

		frappe.set_user("Administrator")
		approver = self._make_role_user(
			"service.ai.approver.evidence@example.test", ("AI Proposal Approver",)
		)
		frappe.set_user(approver)
		with self.assertRaises(frappe.PermissionError):
			get_evidence_chain(work_order.name)

	def test_evidence_timeline_hides_finance_and_ai_from_technician(self):
		from ai_erp_service.evidence import get_evidence_timeline

		work_order = self._make_work_order("Evidence timeline work order")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Verified repair for timeline coverage."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		technician_timeline = get_evidence_timeline(work_order.name)
		stages = {event["stage"] for event in technician_timeline}
		self.assertIn("Created", stages)
		self.assertIn("Execution", stages)
		self.assertIn("Closeout", stages)
		self.assertNotIn("Finance", stages)

		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "Service Closure Exception",
				"work_order": work_order.name,
				"status": "Open",
				"reason": "Parts unavailable",
				"exception_owner": self.manager,
				"due_date": today(),
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.manager)
		manager_with_exception = get_evidence_timeline(work_order.name)
		self.assertIn("Exception", {event["stage"] for event in manager_with_exception})

		exception_name = frappe.db.get_value(
			"Service Closure Exception", {"work_order": work_order.name}, "name"
		)
		exception = frappe.get_doc("Service Closure Exception", exception_name)
		exception.status = "Resolved"
		exception.resolution_note = "Synthetic spare received for timeline coverage."
		exception.save()

		work_order.reload()
		work_order.status = "Closed"
		work_order.save()
		work_order.status = "Invoice Ready"
		work_order.save()
		# Timeline finance stage is gated on sales_invoice presence plus manager/finance role.
		frappe.db.set_value(
			"Service Work Order", work_order.name, "sales_invoice", "SINV-TEST-TIMELINE"
		)

		manager_timeline = get_evidence_timeline(work_order.name)
		manager_stages = {event["stage"] for event in manager_timeline}
		self.assertIn("Finance", manager_stages)
		self.assertIn("Exception", manager_stages)

		frappe.set_user(self.technician)
		technician_after_close = get_evidence_timeline(work_order.name)
		self.assertNotIn("Finance", {event["stage"] for event in technician_after_close})

	def test_margin_leakage_summary_is_manager_or_finance_only(self):
		from ai_erp_service.margin_risk import MARGIN_RISK_CATEGORIES, margin_leakage_summary

		work_order = self._make_work_order("Margin leakage summary work order")
		self._schedule(work_order, self.technician)
		frappe.set_user("Administrator")
		work_order.reload()
		# Unknown warranty is the DocType default and already a margin risk category.
		work_order.inspection_result = "Failed"
		work_order.save()

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			margin_leakage_summary()

		frappe.set_user(self.manager)
		summary = margin_leakage_summary()
		self.assertIn("total_orders", summary)
		self.assertIn("category_counts", summary)
		self.assertIn("high_risk_orders", summary)
		self.assertIn("truncated", summary)
		self.assertIn("page_limit", summary)
		self.assertEqual(summary["available_categories"], list(MARGIN_RISK_CATEGORIES))
		self.assertGreaterEqual(summary["total_orders"], 1)
		# Unfiltered scans on a long-lived local site may hit the page limit;
		# truncation honesty itself is covered in
		# test_margin_leakage_summary_truncation_and_high_risk_caps.
		if summary["truncated"]:
			self.assertEqual(summary["total_orders"], summary["page_limit"])
		# Category filter reaches this work order among a large demo/test site.
		filtered = margin_leakage_summary(risk_category="failed_inspection")
		self.assertEqual(filtered["risk_category"], "failed_inspection")
		self.assertGreaterEqual(filtered["category_counts"].get("failed_inspection", 0), 1)
		self.assertTrue(filtered["high_risk_orders"])
		self.assertTrue(
			all("failed_inspection" in row["risks"] for row in filtered["high_risk_orders"])
		)
		detail_row = next(
			(
				row
				for row in filtered["high_risk_orders"]
				if row.get("name") == work_order.name
			),
			filtered["high_risk_orders"][0],
		)
		self.assertTrue(detail_row.get("risk_details"))
		self.assertTrue(
			any(
				item.get("category") == "failed_inspection"
				and item.get("evidence", {}).get("inspection_result") == "Failed"
				for item in detail_row["risk_details"]
			)
		)

		status_filtered = margin_leakage_summary(status=work_order.status)
		self.assertEqual(status_filtered["status"], work_order.status)
		self.assertTrue(
			all(row["status"] == work_order.status for row in status_filtered["high_risk_orders"])
		)
		self.assertGreaterEqual(status_filtered["category_counts"].get("failed_inspection", 0), 1)

		frappe.set_user(self.finance_user)
		finance_summary = margin_leakage_summary()
		self.assertIn("category_counts", finance_summary)
		self.assertIn("high_risk_truncated", finance_summary)
		self.assertIn("high_risk_limit", finance_summary)

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			profitability_report({})

		frappe.set_user(self.finance_user)
		finance_columns, finance_rows = profitability_report({})
		self.assertIn("margin_risks", {column["fieldname"] for column in finance_columns})
		self.assertIsInstance(finance_rows, list)

	def test_margin_leakage_summary_truncation_and_high_risk_caps(self):
		from ai_erp_service import margin_risk as margin_risk_mod
		from ai_erp_service.margin_risk import margin_leakage_summary

		self._make_work_order("Margin truncation order A")
		self._make_work_order("Margin truncation order B")
		self._make_work_order("Margin truncation order C")

		frappe.set_user(self.manager)
		with patch.object(margin_risk_mod, "MARGIN_SUMMARY_PAGE_LENGTH", 1):
			summary = margin_leakage_summary()
		self.assertTrue(summary["truncated"])
		self.assertEqual(summary["total_orders"], 1)
		self.assertEqual(summary["page_limit"], 1)

		# Exactly page_limit rows must not claim truncation (fetch uses limit+1).
		exact_rows = [
			frappe._dict(
				name=f"EXACT-{index}",
				status="Draft",
				hourly_rate=0,
				warranty_status="Out of Warranty",
				inspection_result="",
				service_asset="",
				service_location=self.location,
				creation=now_datetime(),
				projected_margin_percent=40,
				customer=self.customer,
			)
			for index in range(2)
		]
		with patch.object(margin_risk_mod, "MARGIN_SUMMARY_PAGE_LENGTH", 2):
			with patch.object(
				margin_risk_mod,
				"_load_summary_work_orders",
				return_value=(exact_rows, False),
			):
				exact = margin_leakage_summary()
		self.assertFalse(exact["truncated"])
		self.assertEqual(exact["total_orders"], 2)

		risky_rows = [
			frappe._dict(
				name=f"RISK-{index}",
				status="Closeout Submitted",
				hourly_rate=0,
				warranty_status="Unknown",
				inspection_result="Failed",
				service_asset="",
				service_location=self.location,
				creation=now_datetime(),
				projected_margin_percent=5,
				customer=self.customer,
				margin_risks="failed_inspection, warranty_risk",
				margin_risk_details=[
					{
						"category": "failed_inspection",
						"evidence": {"inspection_result": "Failed"},
					},
					{
						"category": "warranty_risk",
						"evidence": {"warranty_status": "Unknown"},
					},
				],
			)
			for index in range(3)
		]
		with patch.object(margin_risk_mod, "MARGIN_HIGH_RISK_LIMIT", 1):
			with patch.object(
				margin_risk_mod,
				"_load_summary_work_orders",
				return_value=(risky_rows, False),
			):
				with patch.object(
					margin_risk_mod,
					"annotate_margin_risks",
					side_effect=lambda rows: rows,
				):
					capped = margin_leakage_summary()
		self.assertTrue(capped["high_risk_truncated"])
		self.assertEqual(capped["high_risk_limit"], 1)
		self.assertEqual(len(capped["high_risk_orders"]), 1)

	def test_margin_unit_costs_keep_highest_split_line_rate(self):
		from ai_erp_service.margin_risk import _unit_costs

		parts_by_order = {
			"WO-1": [
				frappe._dict(stock_entry="SE-1", item="ITEM-A", bill_rate=10),
			]
		}
		with patch(
			"ai_erp_service.margin_risk.frappe.get_all",
			return_value=[
				frappe._dict(parent="SE-1", item_code="ITEM-A", basic_rate=8),
				frappe._dict(parent="SE-1", item_code="ITEM-A", basic_rate=12),
			],
		):
			costs = _unit_costs(parts_by_order)
		self.assertEqual(costs[("SE-1", "ITEM-A")], 12.0)

	def test_profitability_report_flags_page_truncation_honestly(self):
		from ai_erp_service.ai_erp_service.report.service_profitability import (
			service_profitability as report_mod,
		)

		self._make_work_order("Profitability truncation A")
		self._make_work_order("Profitability truncation B")
		frappe.set_user(self.manager)
		with patch.object(report_mod, "PROFITABILITY_PAGE_LENGTH", 1):
			with patch.object(frappe, "msgprint") as mocked_msgprint:
				_columns, rows = profitability_report({})
		self.assertEqual(len(rows), 1)
		mocked_msgprint.assert_called()

	def test_evidence_packet_is_role_scoped_and_carries_no_draft_content(self):
		from ai_erp_service.evidence import get_evidence_packet

		packet_manager = self._make_role_user(
			"service.manager.packet@example.test",
			("Service Manager", "AI Proposal Approver"),
		)
		work_order = self._make_work_order("Evidence packet work order")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Replaced the belt and verified alignment."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		draft_text = "Draft summary: belt replaced and alignment verified."

		def control_plane_response(payload, route=None):
			return {
				"schema_version": 1,
				"request_id": payload["request_id"],
				"proposal_type": "service_closeout_summary",
				"policy": {
					"decision": "draft_only",
					"allowed_action": "none",
					"category": "draft_only",
					"reason": "Draft only; human review has no ERP side effect.",
				},
				"model": {
					"provider": "test-control-plane",
					"name": "test-closeout-model",
					"prompt_version": "service-closeout-summary@v1",
				},
				"audit": {
					"response_id_hash": "b" * 64,
					"input_tokens": 21,
					"output_tokens": 9,
					"duration_ms": 55,
					"redaction_count": 0,
				},
				"draft_content": draft_text,
				"sources": payload["sources"],
			}

		with patch("ai_erp_core.proposals._post_to_control_plane", side_effect=control_plane_response):
			request_closeout_summary(work_order.name)

		with self.assertRaises(frappe.PermissionError):
			get_evidence_packet(work_order.name)

		frappe.set_user(packet_manager)
		packet = get_evidence_packet(work_order.name)
		self.assertEqual(packet["policy_decisions"], ["Draft Only"])
		self.assertEqual(packet["policy_categories"], ["draft_only"])
		self.assertIn("closeout_notes", {row["source_field"] for row in packet["citations"]})
		self.assertTrue(packet["citation_hashes"])
		self.assertTrue(all(len(value) == 64 for value in packet["citation_hashes"]))
		self.assertEqual(packet["unresolved_exceptions"], [])
		self.assertIn("stock_entries", packet)
		self.assertIn("sales_invoice", packet)
		self.assertEqual(packet["packet_kind"], "evidence_to_cash_ledger")
		self.assertIn("ledger_narrative", packet)
		self.assertIn("stages", packet["ledger_narrative"])
		self.assertIn("margin_risks", packet)
		self.assertEqual(len(packet["chain_hash"]), 64)
		self.assertIn("Synthetic export evidence", packet["synthetic_note"])
		self.assertTrue(packet["proposal_idempotency"])
		self.assertEqual(len(packet["proposal_idempotency"][0]["input_context_hash"]), 64)
		self.assertIn("Identical input_context_hash", packet["proposal_idempotency"][0]["reuse_note"])
		self.assertEqual(packet["proposal_idempotency"][0]["policy_category"], "draft_only")
		self.assertEqual(packet["proposal_idempotency"][0]["provider_duration_ms"], 55)
		self.assertEqual(packet["proposals"][0]["provider_input_tokens"], 21)
		self.assertEqual(packet["proposals"][0]["provider_output_tokens"], 9)

		serialized = frappe.as_json(packet)
		self.assertNotIn(draft_text, serialized)
		self.assertNotIn("draft_content", serialized)
		self.assertNotIn("prompt_version", serialized)

		# Accounts may export only after invoice-ready / invoice visibility.
		frappe.set_user(packet_manager)
		work_order.reload()
		work_order.status = "Closed"
		work_order.save()
		work_order.status = "Invoice Ready"
		work_order.save()

		frappe.set_user(self.finance_user)
		finance_packet = get_evidence_packet(work_order.name)
		self.assertEqual(finance_packet["packet_kind"], "evidence_to_cash_ledger")
		self.assertIn("finance_handoff", [row["stage"] for row in finance_packet["ledger_narrative"]["stages"]])
		self.assertEqual(len(finance_packet["chain_hash"]), 64)
		# Accounts may lack AI Proposal read; packet stays exportable with finance fields.
		self.assertIn("proposal_idempotency", finance_packet)
		self.assertIn("margin_risks", finance_packet)
		self.assertEqual(finance_packet["sales_invoice"], "")

	def test_profitability_report_classifies_margin_leakage_deterministically(self):
		first = self._make_work_order("Margin risk first visit")
		self._schedule(first, self.technician)
		frappe.set_user(self.technician)
		first.reload()
		first.status = "In Progress"
		first.save()
		first.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		first.inspection_result = "Failed"
		first.inspection_notes = "Alignment drifts beyond tolerance after warm-up."
		first.closeout_notes = "Repair attempted; alignment still drifts."
		first.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		first.status = "Closeout Submitted"
		first.save()

		frappe.set_user("Administrator")
		second = self._make_work_order("Margin risk repeat visit")
		self._schedule(second, self.technician)
		frappe.get_doc(
			{
				"doctype": "Service Closure Exception",
				"work_order": first.name,
				"reason": "Parts unavailable",
				"exception_owner": self.manager,
				"due_date": today(),
				"status": "Open",
			}
		).insert(ignore_permissions=True)

		frappe.set_user(self.manager)
		columns, rows = profitability_report({})
		self.assertIn("margin_risks", {column["fieldname"] for column in columns})
		by_name = {row.name: row for row in rows}
		first_risks = by_name[first.name].margin_risks
		for expected_risk in (
			"zero_rate_labor",
			"warranty_risk",
			"failed_inspection",
			"unresolved_exception",
			"repeat_visit_risk",
		):
			self.assertIn(expected_risk, first_risks)
		self.assertNotIn("missing_billable_time", first_risks)
		self.assertNotIn("part_cost_above_bill_rate", first_risks)
		self.assertIn("repeat_visit_risk", by_name[second.name].margin_risks)
		self.assertTrue(getattr(by_name[second.name], "margin_risk_details", None))
		repeat_detail = next(
			(
				item
				for item in by_name[second.name].margin_risk_details
				if item.get("category") == "repeat_visit_risk"
			),
			None,
		)
		self.assertIsNotNone(repeat_detail)
		self.assertIn(first.name, repeat_detail["evidence"]["neighbor_work_orders"])
		self.assertEqual(repeat_detail["evidence"]["window_days"], 30)

	def test_scheduling_suggestions_are_deterministic_bounded_and_propose_only(self):
		from ai_erp_service.scheduling import suggest_technicians

		second_technician = self._make_role_user(
			"service.technician.second@example.test", ("Service Technician",)
		)
		dispatcher = self._make_role_user(
			"service.dispatcher.scheduling@example.test", ("Service Dispatcher",)
		)

		history = self._make_work_order("Familiarity history work order")
		self._schedule(history, second_technician)
		frappe.set_user(self.manager)
		history.reload()
		history.status = "In Progress"
		history.save()
		history.append(
			"time_entries",
			{
				"technician": second_technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		history.closeout_notes = "Completed prior visit."
		history.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		history.status = "Closeout Submitted"
		history.save()
		history.status = "Closed"
		history.save()

		frappe.set_user("Administrator")
		target = self._make_work_order("Scheduling target work order")

		frappe.set_user(dispatcher)
		target.reload()
		with self.assertRaises(frappe.ValidationError):
			suggest_technicians(target.name)

		frappe.set_user("Administrator")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.save()

		busy = self._make_work_order("Overlapping busy work order")
		self._schedule(busy, self.technician)

		frappe.set_user(dispatcher)
		suggestions = suggest_technicians(target.name)
		self.assertLessEqual(len(suggestions["candidates"]), 5)
		candidate_names = [row["technician"] for row in suggestions["candidates"]]
		self.assertIn(second_technician, candidate_names)
		self.assertNotIn(self.technician, candidate_names)
		self.assertIn(
			{"technician": self.technician, "reason": "overlapping_scheduled_work"},
			suggestions["excluded"],
		)
		top = suggestions["candidates"][0]
		self.assertEqual(top["technician"], second_technician)
		self.assertEqual(top["familiarity"], 1)
		self.assertEqual(suggestions, suggest_technicians(target.name))

		target.reload()
		self.assertFalse(target.assigned_technician)

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			suggest_technicians(target.name)

	def test_parts_readiness_uses_service_location_warehouse(self):
		from ai_erp_service.scheduling import _parts_readiness, suggest_technicians

		item, warehouse = self._make_stocked_item()
		frappe.db.set_value("Service Location", self.location, "default_warehouse", warehouse)

		dispatcher = self._make_role_user(
			"service.dispatcher.parts@example.test", ("Service Dispatcher",)
		)
		target = self._make_work_order("Parts readiness scheduling work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.append(
			"parts",
			{"item": item, "qty": 1, "bill_rate": 25, "source_warehouse": warehouse},
		)
		target.save()

		ready = _parts_readiness(target, [self.technician])
		self.assertTrue(ready[self.technician]["ready"])
		self.assertEqual(ready[self.technician]["source"], "primary")

		frappe.db.set_value("Service Location", self.location, "default_warehouse", "")
		target.reload()
		# Fall back to part source_warehouse when location default is unset.
		ready_from_parts = _parts_readiness(target, [self.technician])
		self.assertTrue(ready_from_parts[self.technician]["ready"])

		frappe.set_user(dispatcher)
		suggestions = suggest_technicians(target.name)
		top_reasons = suggestions["candidates"][0]["reasons"]
		self.assertIn("parts_ready:true", top_reasons)

	def test_parts_readiness_sums_duplicate_items_and_honors_row_warehouse(self):
		from ai_erp_service.scheduling import _parts_readiness

		item, warehouse = self._make_stocked_item()
		# Location default points at an empty warehouse so readiness must use the
		# part-row source_warehouse (same warehouse issue_parts would debit).
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		empty_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": f"Empty Parts WH {frappe.generate_hash(length=6)}",
				"company": company,
			}
		).insert(ignore_permissions=True).name
		frappe.db.set_value("Service Location", self.location, "default_warehouse", empty_warehouse)

		target = self._make_work_order("Duplicate parts readiness work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		# Seed receipt qty is 5; two rows of 3 would undercount as ready if only
		# the last row were kept, but the summed demand of 6 must fail readiness.
		target.append(
			"parts",
			{"item": item, "qty": 3, "bill_rate": 25, "source_warehouse": warehouse},
		)
		target.append(
			"parts",
			{"item": item, "qty": 3, "bill_rate": 25, "source_warehouse": warehouse},
		)
		target.save()

		ready = _parts_readiness(target, [self.technician])
		self.assertFalse(ready[self.technician]["ready"])

		bin_name = frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse})
		self.assertTrue(bin_name)
		frappe.db.set_value("Bin", bin_name, "actual_qty", 6)
		target.reload()
		ready_after_restock = _parts_readiness(target, [self.technician])
		self.assertTrue(ready_after_restock[self.technician]["ready"])
		frappe.db.set_value("Service Location", self.location, "default_warehouse", "")

	def test_evidence_timeline_closeout_ignores_later_modified(self):
		work_order = self._make_work_order("Timeline closeout stability work order")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Stable closeout timestamp."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		first = get_evidence_timeline(work_order.name)
		closeout_first = next(event for event in first if event["stage"] == "Closeout")
		closeout_ts = closeout_first["timestamp"]

		frappe.set_user(self.manager)
		work_order.reload()
		work_order.subject = f"{work_order.subject} edited later"
		work_order.save()

		second = get_evidence_timeline(work_order.name)
		closeout_second = next(event for event in second if event["stage"] == "Closeout")
		self.assertEqual(closeout_second["timestamp"], closeout_ts)
		self.assertNotEqual(str(work_order.modified), closeout_ts)

		parsed = [get_datetime(event["timestamp"]) for event in second]
		self.assertEqual(parsed, sorted(parsed))

	def test_evidence_timeline_closeout_queries_version_by_status_marker(self):
		from ai_erp_service import evidence as evidence_mod

		work_order = self._make_work_order("Timeline closeout version filter work order")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.closeout_notes = "Closeout with filtered Version lookup."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		version_calls = []
		real_get_all = frappe.get_all

		def tracking_get_all(*args, **kwargs):
			doctype = args[0] if args else kwargs.get("doctype")
			if doctype == "Version":
				version_calls.append(kwargs)
			return real_get_all(*args, **kwargs)

		with patch.object(frappe, "get_all", side_effect=tracking_get_all):
			timeline = evidence_mod.get_evidence_timeline(work_order.name)

		self.assertTrue(version_calls)
		filters = version_calls[0].get("filters") or {}
		self.assertEqual(filters.get("data"), ("like", "%Closeout Submitted%"))
		closeout = next(event for event in timeline if event["stage"] == "Closeout")
		self.assertTrue(closeout["timestamp"])

	def test_scheduling_explanation_is_draft_only_cited_and_cannot_assign(self):
		from ai_erp_service.scheduling import request_scheduling_explanation

		dispatcher = self._make_role_user(
			"service.dispatcher.explanation@example.test",
			("Service Dispatcher", "AI Proposal Approver"),
		)
		target = self._make_work_order("Scheduling explanation work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.save()

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			request_scheduling_explanation(target.name)

		frappe.set_user(dispatcher)
		result = request_scheduling_explanation(target.name)
		retry = request_scheduling_explanation(target.name)
		self.assertEqual(retry["name"], result["name"])

		proposal = frappe.get_doc("AI Proposal", result["name"])
		self.assertEqual(proposal.proposal_type, "Scheduling Explanation")
		self.assertEqual(proposal.proposal_status, "Draft")
		self.assertEqual(proposal.policy_outcome, "Draft Only")
		self.assertEqual(proposal.model_provider, "development-template")
		source_fields = {source.source_field for source in proposal.sources}
		self.assertIn("ranking", source_fields)
		self.assertIn("priority", source_fields)
		self.assertIn("cannot assign a technician", proposal.draft_content)

		target.reload()
		self.assertFalse(target.assigned_technician)
		proposal.review("Approved", "Ranking matches recorded workload evidence.")
		target.reload()
		self.assertFalse(target.assigned_technician)
		self.assertEqual(
			frappe.get_doc("AI Proposal", result["name"]).proposal_status, "Approved"
		)

	def test_suggestion_rejection_feedback_is_dispatcher_only_and_non_assigning(self):
		from ai_erp_service.scheduling import record_suggestion_feedback

		dispatcher = self._make_role_user(
			"service.dispatcher.feedback@example.test",
			("Service Dispatcher",),
		)
		target = self._make_work_order("Suggestion feedback work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.save()

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			record_suggestion_feedback(
				target.name,
				self.technician,
				"Wrong skill or territory",
				"Not the right craft.",
			)

		frappe.set_user(dispatcher)
		result = record_suggestion_feedback(
			target.name,
			self.technician,
			"Parts not ready",
			"Van stock missing filter.",
		)
		self.assertTrue(result["recorded"])
		target.reload()
		self.assertFalse(target.assigned_technician)
		comments = frappe.get_all(
			"Comment",
			filters={"reference_doctype": "Service Work Order", "reference_name": target.name},
			fields=["content"],
		)
		self.assertTrue(
			any("Scheduling suggestion rejected" in (row.content or "") for row in comments)
		)

	def test_suggestion_feedback_summary_is_dispatcher_only_and_aggregates_categories(self):
		from ai_erp_service.scheduling import (
			record_suggestion_feedback,
			suggest_technicians,
			suggestion_feedback_summary,
		)

		dispatcher = self._make_role_user(
			"service.dispatcher.feedback.summary@example.test",
			("Service Dispatcher",),
		)
		target = self._make_work_order("Suggestion feedback summary work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.save()

		frappe.set_user(dispatcher)
		record_suggestion_feedback(target.name, self.technician, "Parts not ready")
		record_suggestion_feedback(target.name, self.technician, "Workload conflict")
		record_suggestion_feedback(target.name, self.technician, "Parts not ready")

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			suggestion_feedback_summary(target.name)

		frappe.set_user(dispatcher)
		summary = suggestion_feedback_summary(target.name)
		self.assertEqual(summary["scope"], target.name)
		self.assertEqual(summary["total"], 3)
		self.assertEqual(summary["category_counts"]["Parts not ready"], 2)
		self.assertEqual(summary["category_counts"]["Workload conflict"], 1)
		self.assertFalse(summary["truncated"])

		suggestions = suggest_technicians(target.name)
		self.assertEqual(suggestions["feedback_summary"]["total"], 3)
		self.assertEqual(suggestions["feedback_summary"]["category_counts"]["Parts not ready"], 2)

	def test_scheduling_capability_match_excludes_and_ranks_without_assigning(self):
		from ai_erp_service.scheduling import suggest_technicians

		matched = self._make_role_user(
			"service.technician.capable@example.test", ("Service Technician",)
		)
		mismatched = self._make_role_user(
			"service.technician.wrongskill@example.test", ("Service Technician",)
		)
		dispatcher = self._make_role_user(
			"service.dispatcher.capability@example.test", ("Service Dispatcher",)
		)

		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "Service Technician Capability",
				"technician": matched,
				"skills": "HVAC, Electrical",
				"territories": "North",
				"active": 1,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Service Technician Capability",
				"technician": mismatched,
				"skills": "Plumbing",
				"territories": "South",
				"active": 1,
			}
		).insert()

		target = self._make_work_order("Capability scheduling work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.required_skill = "HVAC"
		target.service_territory = "North"
		target.save()

		frappe.set_user(dispatcher)
		suggestions = suggest_technicians(target.name)
		candidate_names = [row["technician"] for row in suggestions["candidates"]]
		self.assertIn(matched, candidate_names)
		self.assertNotIn(mismatched, candidate_names)
		self.assertIn(
			{"technician": mismatched, "reason": "missing_skill"},
			suggestions["excluded"],
		)
		top = next(row for row in suggestions["candidates"] if row["technician"] == matched)
		self.assertIn("skill_match:hvac", top["reasons"])
		self.assertIn("territory_match:north", top["reasons"])
		target.reload()
		self.assertFalse(target.assigned_technician)

		capability_name = frappe.db.get_value(
			"Service Technician Capability", {"technician": matched}
		)
		frappe.set_user(mismatched)
		capability = frappe.get_doc("Service Technician Capability", capability_name)
		with self.assertRaises(frappe.PermissionError):
			capability.check_permission("read")

	def test_parts_readiness_uses_van_warehouse_when_primary_bin_is_short(self):
		from ai_erp_service.scheduling import _parts_readiness, suggest_technicians

		item, empty_primary = self._make_stocked_item()
		company = frappe.db.get_value("Warehouse", empty_primary, "company")
		van_warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": f"Van Stock WH {frappe.generate_hash(length=6)}",
				"company": company,
			}
		).insert(ignore_permissions=True).name
		# Drain the primary bin so only van stock can satisfy readiness.
		primary_bin = frappe.db.get_value(
			"Bin", {"item_code": item, "warehouse": empty_primary}
		)
		self.assertTrue(primary_bin)
		frappe.db.set_value("Bin", primary_bin, "actual_qty", 0)
		make_stock_entry(
			item_code=item,
			qty=2,
			to_warehouse=van_warehouse,
			rate=10,
			purpose="Material Receipt",
			company=company,
		)

		van_tech = self._make_role_user(
			"service.technician.van@example.test", ("Service Technician",)
		)
		no_van_tech = self._make_role_user(
			"service.technician.novan@example.test", ("Service Technician",)
		)
		dispatcher = self._make_role_user(
			"service.dispatcher.van@example.test", ("Service Dispatcher",)
		)
		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "Service Technician Capability",
				"technician": van_tech,
				"skills": "HVAC",
				"territories": "North",
				"van_warehouse": van_warehouse,
				"active": 1,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Service Technician Capability",
				"technician": no_van_tech,
				"skills": "HVAC",
				"territories": "North",
				"active": 1,
			}
		).insert()

		target = self._make_work_order("Van stock readiness work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.required_skill = "HVAC"
		target.service_territory = "North"
		target.service_priority = "High"
		target.append(
			"parts",
			{"item": item, "qty": 1, "bill_rate": 25, "source_warehouse": empty_primary},
		)
		target.save()

		ready = _parts_readiness(
			target,
			[van_tech, no_van_tech],
			{van_tech: van_warehouse, no_van_tech: ""},
		)
		self.assertTrue(ready[van_tech]["ready"])
		self.assertEqual(ready[van_tech]["source"], "van")
		self.assertFalse(ready[no_van_tech]["ready"])

		frappe.set_user(dispatcher)
		suggestions = suggest_technicians(target.name)
		van_row = next(row for row in suggestions["candidates"] if row["technician"] == van_tech)
		no_van_row = next(
			row for row in suggestions["candidates"] if row["technician"] == no_van_tech
		)
		self.assertIn("parts_ready:van_stock", van_row["reasons"])
		self.assertIn("sla_priority:High", van_row["reasons"])
		self.assertIn(f"van_warehouse:{van_warehouse}", van_row["reasons"])
		self.assertNotIn("parts_ready:true", no_van_row["reasons"])
		self.assertNotIn("parts_ready:van_stock", no_van_row["reasons"])
		self.assertGreater(van_row["score"], no_van_row["score"])
		target.reload()
		self.assertFalse(target.assigned_technician)

	def test_scheduling_tie_breakers_prefer_lower_workload_then_technician_id(self):
		from ai_erp_service.scheduling import suggest_technicians

		# Lexicographically ordered ids so the sort key is checkable.
		alpha = self._make_role_user(
			"service.technician.alpha@example.test", ("Service Technician",)
		)
		bravo = self._make_role_user(
			"service.technician.bravo@example.test", ("Service Technician",)
		)
		dispatcher = self._make_role_user(
			"service.dispatcher.tiebreak@example.test", ("Service Dispatcher",)
		)
		# Capability gate keeps the top-5 list to these two technicians only.
		frappe.set_user("Administrator")
		for technician in (alpha, bravo):
			frappe.get_doc(
				{
					"doctype": "Service Technician Capability",
					"technician": technician,
					"skills": "TieBreakSkill",
					"territories": "TieBreakTerritory",
					"active": 1,
				}
			).insert()

		# Non-overlapping open work for alpha raises workload without exclusion.
		busy = self._make_work_order("Tie-break busy work order")
		busy.reload()
		busy_start = add_to_date(now_datetime(), days=3)
		busy.assigned_technician = alpha
		busy.scheduled_start = busy_start
		busy.scheduled_end = add_to_date(busy_start, hours=2)
		busy.status = "Scheduled"
		busy.save()

		target = self._make_work_order("Tie-break target work order")
		target.reload()
		start = now_datetime()
		target.scheduled_start = start
		target.scheduled_end = add_to_date(start, hours=2)
		target.required_skill = "TieBreakSkill"
		target.service_territory = "TieBreakTerritory"
		target.save()

		frappe.set_user(dispatcher)
		suggestions = suggest_technicians(target.name)
		ranked = [row["technician"] for row in suggestions["candidates"]]
		self.assertEqual(ranked, [bravo, alpha])
		self.assertGreater(
			next(row["workload"] for row in suggestions["candidates"] if row["technician"] == alpha),
			next(row["workload"] for row in suggestions["candidates"] if row["technician"] == bravo),
		)

		# Close alpha's open work; equal workload then breaks ties on id ascending.
		frappe.set_user("Administrator")
		busy.reload()
		busy.status = "In Progress"
		busy.save()
		busy.append(
			"time_entries",
			{
				"technician": alpha,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		busy.closeout_notes = "Closed for tie-break reset."
		busy.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		busy.status = "Closeout Submitted"
		busy.save()
		busy.status = "Closed"
		busy.save()

		frappe.set_user(dispatcher)
		equal_workload = suggest_technicians(target.name)
		self.assertEqual(
			[row["technician"] for row in equal_workload["candidates"]],
			[alpha, bravo],
		)
		self.assertEqual(equal_workload, suggest_technicians(target.name))
		target.reload()
		self.assertFalse(target.assigned_technician)

	def test_related_history_retrieval_abstains_without_asset_or_location(self):
		from ai_erp_service.retrieval import related_work_history

		orphan = frappe.get_doc(
			{
				"doctype": "Service Work Order",
				"subject": "Orphan retrieval work order",
				"customer": self.customer,
				"status": "Draft",
			}
		)
		orphan.insert()
		self.assertEqual(related_work_history(orphan), [])

	def test_evidence_chain_surfaces_margin_risks_for_managers(self):
		from ai_erp_service.evidence import get_evidence_chain

		work_order = self._make_work_order("Margin risk evidence chain")
		self._schedule(work_order, self.technician)
		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		work_order.inspection_result = "Failed"
		work_order.inspection_notes = "Alignment still drifts after warm-up."
		work_order.closeout_notes = "Alignment still drifts."
		work_order.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		work_order.status = "Closeout Submitted"
		work_order.save()

		frappe.set_user(self.technician)
		technician_chain = get_evidence_chain(work_order.name)
		self.assertNotIn("finance", technician_chain["sections"])

		frappe.set_user(self.manager)
		manager_chain = get_evidence_chain(work_order.name)
		self.assertIn("margin_risks", manager_chain["sections"]["finance"])
		self.assertIn(
			"failed_inspection", manager_chain["sections"]["finance"]["margin_risks"]
		)
		self.assertIn("margin_risk_details", manager_chain["sections"]["finance"])
		failed_detail = next(
			(
				item
				for item in manager_chain["sections"]["finance"]["margin_risk_details"]
				if item.get("category") == "failed_inspection"
			),
			None,
		)
		self.assertIsNotNone(failed_detail)
		self.assertEqual(failed_detail["evidence"]["inspection_result"], "Failed")
		self.assertEqual(failed_detail["evidence"]["source"], "Service Work Order.inspection_result")
		zero_rate = next(
			(
				item
				for item in manager_chain["sections"]["finance"]["margin_risk_details"]
				if item.get("category") == "zero_rate_labor"
			),
			None,
		)
		self.assertIsNotNone(zero_rate)
		self.assertIn("billable_hours", zero_rate["evidence"])
		finance_stage = next(
			(
				stage
				for stage in (manager_chain.get("ledger_narrative") or {}).get("stages") or []
				if stage.get("stage") == "finance_handoff"
			),
			None,
		)
		self.assertIsNotNone(finance_stage)
		self.assertIn("zero_rate_labor→", finance_stage["summary"])
		self.assertIn("failed_inspection", finance_stage["summary"])

	def test_recovery_draft_is_manager_only_cited_and_cannot_close_work(self):
		from ai_erp_service.recovery import request_recovery_draft

		recovery_manager = self._make_role_user(
			"service.manager.recovery@example.test",
			("Service Manager", "AI Proposal Approver"),
		)
		work_order = self._make_work_order("Blocked compressor work order")
		self._schedule(work_order, self.technician)
		work_order.closure_owner = recovery_manager
		work_order.closure_due_date = today()
		work_order.save()

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.cannot_close_reason = "Parts unavailable"
		work_order.status = "Cannot Close"
		work_order.save()

		with self.assertRaises(frappe.PermissionError):
			request_recovery_draft(work_order.name)

		frappe.set_user(recovery_manager)
		result = request_recovery_draft(work_order.name)
		retry = request_recovery_draft(work_order.name)
		self.assertEqual(retry["name"], result["name"])

		proposal = frappe.get_doc("AI Proposal", result["name"])
		self.assertEqual(proposal.proposal_type, "Exception Recovery")
		self.assertEqual(proposal.proposal_status, "Draft")
		self.assertEqual(proposal.policy_outcome, "Draft Only")
		source_fields = {source.source_field for source in proposal.sources}
		self.assertIn("reason", source_fields)
		self.assertIn("cannot_close", source_fields)
		self.assertIn("purchase or transfer request", proposal.draft_content)
		self.assertIn("cannot close the work order", proposal.draft_content)

		proposal.review("Approved", "Recovery steps match the recorded exception.")
		work_order.reload()
		self.assertEqual(work_order.status, "Cannot Close")
		exception = frappe.get_doc("Service Closure Exception", work_order.closure_exception)
		self.assertEqual(exception.status, "Open")

	def test_repair_memory_reuses_only_visible_history_and_abstains_otherwise(self):
		from ai_erp_service.repair_memory import request_repair_memory_draft

		historian = self._make_role_user(
			"service.technician.historian@example.test", ("Service Technician",)
		)
		item, warehouse = self._make_stocked_item()
		history = self._make_work_order("Historic mount replacement")
		self._schedule(history, historian)
		frappe.set_user(self.manager)
		history.reload()
		history.status = "In Progress"
		history.save()
		history.append(
			"time_entries",
			{"technician": historian, "work_date": today(), "time_type": "Work", "hours": 1},
		)
		history.append(
			"parts",
			{"item": item, "qty": 1, "bill_rate": 25, "source_warehouse": warehouse},
		)
		history.closeout_notes = "Replaced the mount kit; vibration resolved."
		history.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		history.status = "Closeout Submitted"
		history.save()
		frappe.set_user("Administrator")
		issue_parts(history.name)
		history.reload()
		history.status = "Closed"
		history.save()

		other_customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Unrelated Repair Customer"}
		).insert(ignore_if_duplicate=True)
		other_location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Unrelated Repair Site",
				"customer": other_customer.name,
			}
		).insert()
		unrelated = frappe.get_doc(
			{
				"doctype": "Service Work Order",
				"subject": "Unrelated site pump repair",
				"customer": other_customer.name,
				"service_location": other_location.name,
				"status": "Draft",
			}
		).insert()

		current = self._make_work_order("Recurring vibration diagnosis")
		self._schedule(current, self.technician)

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			request_repair_memory_draft(unrelated.name)

		current.reload()
		technician_result = request_repair_memory_draft(current.name)
		technician_proposal = frappe.get_doc("AI Proposal", technician_result["name"])
		self.assertIn("Abstention", technician_proposal.draft_content)
		self.assertNotIn(item, technician_proposal.draft_content)

		frappe.set_user(self.manager)
		manager_result = request_repair_memory_draft(current.name)
		manager_proposal = frappe.get_doc("AI Proposal", manager_result["name"])
		self.assertEqual(manager_proposal.proposal_type, "Repair Memory")
		self.assertEqual(manager_proposal.proposal_status, "Draft")
		self.assertIn(history.name, manager_proposal.draft_content)
		self.assertIn(f"{item}: used in 1 prior visit(s)", manager_proposal.draft_content)
		self.assertNotIn("Unrelated site pump repair", manager_proposal.draft_content)
		history_citations = {
			source.source_name
			for source in manager_proposal.sources
			if source.source_field == "history"
		}
		self.assertEqual(history_citations, {history.name})

		retry = request_repair_memory_draft(current.name)
		self.assertEqual(retry["name"], manager_result["name"])
		current.reload()
		self.assertEqual(current.status, "Scheduled")

	def test_repair_memory_blocks_unassigned_technician_and_unrelated_customer(self):
		from ai_erp_service.repair_memory import request_repair_memory_draft
		from ai_erp_service.retrieval import related_work_history

		other_technician = self._make_role_user(
			"service.technician.unassigned@example.test", ("Service Technician",)
		)
		history = self._make_work_order("Visible location history for repair memory")
		self._schedule(history, self.technician)
		frappe.set_user(self.manager)
		history.reload()
		history.status = "In Progress"
		history.save()
		history.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		history.closeout_notes = "Replaced gasket; torque verified."
		history.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		history.status = "Closeout Submitted"
		history.save()
		history.status = "Closed"
		history.save()

		assigned = self._make_work_order("Assigned recurring repair")
		self._schedule(assigned, self.technician)

		frappe.set_user(other_technician)
		with self.assertRaises(frappe.PermissionError):
			request_repair_memory_draft(assigned.name)

		frappe.set_user("Administrator")
		other_customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": "Same-Customer Other Site"}
		).insert(ignore_if_duplicate=True)
		# Same customer, different location: customer alone must not retrieve history.
		foreign_location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Foreign Repair Site",
				"customer": self.customer,
			}
		).insert()
		foreign = frappe.get_doc(
			{
				"doctype": "Service Work Order",
				"subject": "Foreign site recurring repair",
				"customer": self.customer,
				"service_location": foreign_location.name,
				"status": "Draft",
			}
		).insert()
		self._schedule(foreign, self.technician)
		frappe.set_user(self.manager)
		foreign.reload()
		self.assertEqual(related_work_history(foreign), [])
		frappe.set_user("Administrator")
		# Unrelated customer at another site stays empty too.
		stranger_location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Stranger Repair Site",
				"customer": other_customer.name,
			}
		).insert()
		stranger = frappe.get_doc(
			{
				"doctype": "Service Work Order",
				"subject": "Stranger customer repair",
				"customer": other_customer.name,
				"service_location": stranger_location.name,
				"status": "Draft",
			}
		).insert()
		frappe.set_user(self.manager)
		self.assertEqual(related_work_history(stranger), [])

		assigned.reload()
		visible = related_work_history(assigned)
		self.assertEqual([row.name for row in visible], [history.name])

	def test_repair_memory_abstains_on_weak_cited_history(self):
		from ai_erp_service.repair_memory import request_repair_memory_draft

		weak = self._make_work_order("Weak closed history without repair facts")
		self._schedule(weak, self.technician)
		frappe.set_user(self.manager)
		weak.reload()
		weak.status = "In Progress"
		weak.save()
		weak.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 1,
			},
		)
		# Closeout validation requires notes; strip them after close so retrieval
		# returns a cited row with no actionable repair facts.
		weak.closeout_notes = "Temporary closeout note for status transition."
		weak.closeout_evidence = "/private/files/ai-closeout-evidence.txt"
		weak.inspection_result = "Pass"
		weak.status = "Closeout Submitted"
		weak.save()
		weak.status = "Closed"
		weak.save()
		frappe.db.set_value("Service Work Order", weak.name, "closeout_notes", "")

		current = self._make_work_order("Current visit over weak history")
		self._schedule(current, self.technician)
		frappe.set_user(self.manager)
		result = request_repair_memory_draft(current.name)
		proposal = frappe.get_doc("AI Proposal", result["name"])
		self.assertIn("Abstention", proposal.draft_content)
		self.assertIn("no closeout notes, parts, or follow-up inspection", proposal.draft_content)
		self.assertNotIn("Likely fix based on cited prior work", proposal.draft_content)
		current.reload()
		self.assertEqual(current.status, "Scheduled")

	def test_demo_seed_is_idempotent_and_stays_before_transaction_actions(self):
		invoices_before = frappe.db.count("Sales Invoice")

		result = seed_service_demo()
		retry = seed_service_demo()

		self.assertEqual(retry["service_request"], result["service_request"])
		self.assertEqual(retry["service_work_order"], result["service_work_order"])
		self.assertEqual(retry["customer"], result["customer"])
		self.assertEqual(retry["part_item"], result["part_item"])
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before)

		request = frappe.get_doc("Service Request", result["service_request"])
		work_order = frappe.get_doc("Service Work Order", result["service_work_order"])

		self.assertEqual(request.status, "Triaged")
		self.assertEqual(request.service_work_order, work_order.name)
		self.assertEqual(work_order.status, "Scheduled")
		self.assertEqual(work_order.assigned_technician, result["technician_user"])
		self.assertEqual(work_order.service_billing_item, result["labor_item"])
		self.assertEqual(work_order.hourly_rate, 80)
		self.assertEqual(work_order.sales_invoice, None)
		self.assertEqual(len(work_order.parts), 1)
		self.assertEqual(work_order.parts[0].item, result["part_item"])
		self.assertEqual(work_order.parts[0].source_warehouse, result["warehouse"])
		self.assertFalse(work_order.parts[0].stock_entry)

		if result["initial_stock_entry"]:
			self.assertEqual(frappe.db.get_value("Stock Entry", result["initial_stock_entry"], "docstatus"), 1)
			self.assertEqual(frappe.db.get_value("Stock Entry", result["initial_stock_entry"], "purpose"), "Material Receipt")

	def test_e2e_preparation_requires_explicit_local_opt_in(self):
		with patch.dict("os.environ", {}, clear=True):
			with self.assertRaises(frappe.ValidationError):
				prepare_e2e_demo()

	def test_profitability_report_is_manager_only_and_permission_scoped(self):
		work_order = self._make_work_order("Profitability report work order")
		work_order.hourly_rate = 100
		work_order.append(
			"time_entries",
			{
				"technician": self.technician,
				"work_date": today(),
				"time_type": "Work",
				"hours": 2,
			},
		)
		work_order.save()

		_columns, rows = profitability_report({"customer": self.customer})
		row = next(item for item in rows if item.name == work_order.name)
		self.assertEqual(flt(row.projected_revenue), 200)
		self.assertEqual(flt(row.projected_margin_before_labor), 200)

		frappe.set_user(self.technician)
		with self.assertRaises(frappe.PermissionError):
			profitability_report({"customer": self.customer})

	def _make_customer(self):
		name = "AI ERP Service Test Customer {0}".format(frappe.generate_hash(length=8))
		customer = frappe.get_doc(
			{"doctype": "Customer", "customer_name": name, "customer_type": "Company"}
		).insert()
		return customer.name

	def _make_location(self):
		location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Test Site {0}".format(frappe.generate_hash(length=8)),
				"customer": self.customer,
			}
		).insert()
		return location.name

	def _make_stocked_item(self):
		warehouse = next(
			(
				row.name
				for row in frappe.get_all(
					"Warehouse",
					filters={"is_group": 0},
					fields=["name", "company"],
					order_by="creation asc",
				)
				if self._company_accounts_use_base_currency(row.company)
			),
			None,
		)
		self.assertTrue(warehouse)
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "AI-ERP-PART-{0}".format(frappe.generate_hash(length=8)),
				"item_name": "AI ERP Test Part",
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"is_stock_item": 1,
			}
		).insert()
		make_stock_entry(
			item_code=item.name,
			qty=5,
			to_warehouse=warehouse,
			rate=10,
			purpose="Material Receipt",
			company=company,
		)
		return item.name, warehouse

	def _company_accounts_use_base_currency(self, company):
		company_currency = frappe.db.get_value("Company", company, "default_currency")
		receivable_account = frappe.db.get_value(
			"Company", company, "default_receivable_account"
		) or frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Receivable", "is_group": 0},
			"name",
		)
		account_currency = (
			frappe.db.get_value("Account", receivable_account, "account_currency")
			if receivable_account
			else None
		)
		return bool(company_currency and account_currency == company_currency)

	def _make_service_item(self):
		uom = self._make_fractional_hour_uom()
		item = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "AI-ERP-LABOR-{0}".format(frappe.generate_hash(length=8)),
				"item_name": "AI ERP Test Labor",
				"item_group": "All Item Groups",
				"stock_uom": uom,
				"is_stock_item": 0,
				"is_sales_item": 1,
			}
		).insert()
		return item.name

	def _make_fractional_hour_uom(self):
		uom = "AI ERP Service Hour"
		if not frappe.db.exists("UOM", uom):
			frappe.get_doc(
				{
					"doctype": "UOM",
					"uom_name": uom,
					"enabled": 1,
					"must_be_whole_number": 0,
				}
			).insert()
		elif frappe.db.get_value("UOM", uom, "must_be_whole_number"):
			frappe.db.set_value("UOM", uom, "must_be_whole_number", 0)
		return uom

	def _stock_entry_cost(self, stock_entry):
		return sum(
			flt(row.amount) if row.amount is not None else flt(row.basic_amount)
			for row in frappe.get_all(
				"Stock Entry Detail",
				filters={"parent": stock_entry},
				fields=["amount", "basic_amount"],
			)
		)

	def _make_technician(self, email="service.technician@example.test"):
		if not frappe.db.exists("User", email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "Service",
					"last_name": "Technician",
					"enabled": 1,
					"send_welcome_email": 0,
					"user_type": "System User",
					"roles": [{"role": "Service Technician"}, {"role": "AI Proposal Requester"}],
				}
			).insert()
		else:
			user = frappe.get_doc("User", email)
			roles_changed = False
			for role in ("Service Technician", "AI Proposal Requester"):
				if not any(row.role == role for row in user.roles):
					user.append("roles", {"role": role})
					roles_changed = True
			if roles_changed:
				user.save()
		frappe.clear_cache(user=email)
		return user.name

	def _make_role_user(self, email, roles):
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
		else:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "AI ERP",
					"last_name": "Role Test",
					"enabled": 1,
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			).insert()
		changed = False
		for role in roles:
			if not any(row.role == role for row in user.roles):
				user.append("roles", {"role": role})
				changed = True
		if changed:
			user.save()
		frappe.clear_cache(user=email)
		return user.name

	def _make_work_order(self, subject):
		return frappe.get_doc(
			{
				"doctype": "Service Work Order",
				"subject": subject,
				"customer": self.customer,
				"service_location": self.location,
				"status": "Draft",
			}
		).insert()

	def _schedule(self, work_order, technician):
		start = now_datetime()
		work_order.assigned_technician = technician
		work_order.scheduled_start = start
		work_order.scheduled_end = add_to_date(start, hours=1)
		work_order.status = "Scheduled"
		work_order.save()
