# Copyright (c) 2026, AI ERP Demo and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, flt, now_datetime, today

from ai_erp_service.ai_drafts import request_closeout_summary
from ai_erp_service.ai_erp_service.doctype.service_request.service_request import create_service_work_order
from ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order import (
	issue_parts,
	make_draft_sales_invoice,
)
from ai_erp_service.demo_seed import seed_service_demo

# This focused integration suite creates its synthetic dependencies directly.
# Avoid recursively loading unrelated ERPNext test-record modules.
IGNORE_TEST_RECORD_DEPENDENCIES = [
	"Customer",
	"AI Proposal",
	"AI Proposal Source",
	"Item",
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

		frappe.set_user(self.technician)
		work_order.reload()
		work_order.status = "In Progress"
		work_order.save()
		work_order.cannot_close_reason = "Parts unavailable"
		work_order.closure_owner = "Administrator"
		work_order.closure_due_date = today()
		work_order.status = "Cannot Close"
		work_order.save()

		exception = frappe.get_doc("Service Closure Exception", work_order.closure_exception)
		self.assertEqual(exception.work_order, work_order.name)
		self.assertEqual(exception.exception_owner, "Administrator")
		self.assertEqual(exception.status, "Open")

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
		self.assertIsNone(issue_parts(work_order.name))

	def test_manager_creates_idempotent_draft_sales_invoice(self):
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

		frappe.set_user("Administrator")
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

		def control_plane_response(payload):
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
		proposal.review("Approved", "Reviewed against cited field evidence.")
		proposal.reload()
		work_order.reload()
		self.assertEqual(proposal.proposal_status, "Approved")
		self.assertEqual(proposal.reviewed_by, "Administrator")
		self.assertEqual(work_order.status, "Closeout Submitted")
		self.assertEqual(work_order.closeout_notes, "Tightened the mount and confirmed normal operation.")
		self.assertEqual(frappe.db.count("Sales Invoice"), invoices_before)
		self.assertEqual(frappe.db.count("Stock Entry"), stock_entries_before)

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
		warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")
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
