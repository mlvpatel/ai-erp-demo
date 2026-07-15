# Copyright (c) 2026, AI ERP Demo and contributors
# For license information, please see license.txt

from time import sleep

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from ai_erp_service.service_utils import (
	DISPATCHER_ROLES,
	FINANCE_ROLES,
	MANAGER_ROLES,
	has_any_role,
	require_any_role,
	validate_location_customer,
)

TRANSITIONS = {
	"Draft": {"Scheduled", "Cancelled"},
	"Scheduled": {"In Progress", "Cancelled"},
	"In Progress": {"Closeout Submitted", "Cannot Close", "Cancelled"},
	"Closeout Submitted": {"In Progress", "Closed"},
	"Cannot Close": {"Scheduled", "In Progress", "Cancelled"},
	"Closed": {"Invoice Ready"},
	"Invoice Ready": set(),
	"Cancelled": set(),
}

TECHNICIAN_STATES = {"In Progress", "Closeout Submitted", "Cannot Close"}
CLOSEOUT_STATES = {"Closeout Submitted", "Closed", "Invoice Ready"}
FINAL_STATES = {"Closed", "Invoice Ready"}
MAX_TRANSACTION_RETRIES = 3


class ServiceWorkOrder(Document):
	def validate(self):
		self._validate_location()
		self._validate_schedule()
		self._validate_assignment()
		self._validate_time_entries()
		self._validate_parts()
		self._validate_issued_parts_are_immutable()
		self._validate_sales_invoice_link()
		self._validate_billing_basis_is_immutable_after_invoice()
		self._validate_transition()
		self._validate_closeout()
		self._validate_cannot_close()
		self._validate_invoice_ready()
		self._update_profitability_projection()

	def _validate_location(self):
		validate_location_customer(self.customer, self.service_location)

	def _validate_schedule(self):
		if self.scheduled_start and self.scheduled_end and self.scheduled_end <= self.scheduled_start:
			frappe.throw(_("Scheduled End must be later than Scheduled Start."))

	def _validate_assignment(self):
		if self.status in {"Scheduled", *TECHNICIAN_STATES, *FINAL_STATES} and not self.assigned_technician:
			frappe.throw(_("An Assigned Technician is required for the current work-order status."))

	def _validate_time_entries(self):
		for row in self.get("time_entries") or []:
			if flt(row.hours) <= 0:
				frappe.throw(_("Time-entry hours must be greater than zero."))
			# ponytail: Support multiple technicians only after scheduling discovery proves the need.
			if self.assigned_technician and row.technician != self.assigned_technician:
				frappe.throw(_("Time entries must belong to the assigned technician."))
			if self._is_technician_only() and row.technician != frappe.session.user:
				frappe.throw(_("Technicians can record only their own time."), frappe.PermissionError)

	def _validate_parts(self):
		for row in self.get("parts") or []:
			if flt(row.qty) <= 0:
				frappe.throw(_("Part quantity must be greater than zero."))
			if flt(row.bill_rate) < 0:
				frappe.throw(_("Part Bill Rate cannot be negative."))
			if not row.source_warehouse:
				frappe.throw(_("Each part requires a Source Warehouse."))

	def _validate_issued_parts_are_immutable(self):
		if self.is_new():
			if any(row.stock_entry for row in self.get("parts") or []):
				frappe.throw(_("Part rows cannot be linked to a Stock Entry during creation."))
			return

		stored_rows = {
			row.name: row
			for row in frappe.get_all(
				"Service Work Order Part",
				filters={"parent": self.name, "parenttype": self.doctype, "parentfield": "parts"},
				fields=["name", "item", "qty", "source_warehouse", "stock_entry"],
			)
		}
		current_rows = {row.name: row for row in self.get("parts") or [] if row.name}

		for stored_name, stored in stored_rows.items():
			current = current_rows.get(stored_name)
			if stored.stock_entry:
				if not current or (
					current.stock_entry != stored.stock_entry
					or current.item != stored.item
					or flt(current.qty) != flt(stored.qty)
					or current.source_warehouse != stored.source_warehouse
				):
					frappe.throw(_("Issued part rows are immutable."))
			elif current and current.stock_entry and not self.flags.from_stock_issue:
				frappe.throw(_("Only the deterministic stock-issue action can link a Stock Entry."))

		if not self.flags.from_stock_issue:
			for row in self.get("parts") or []:
				if row.stock_entry and row.name not in stored_rows:
					frappe.throw(_("Only the deterministic stock-issue action can link a Stock Entry."))

	def _validate_sales_invoice_link(self):
		if self.is_new():
			if self.sales_invoice:
				frappe.throw(_("Sales Invoice can only be linked by the draft invoice action."))
			return

		stored_invoice = frappe.db.get_value(self.doctype, self.name, "sales_invoice")
		if self.sales_invoice != stored_invoice and not self.flags.from_invoice_creation:
			frappe.throw(_("Sales Invoice can only be linked by the draft invoice action."))

	def _validate_billing_basis_is_immutable_after_invoice(self):
		if self.is_new() or not frappe.db.get_value(self.doctype, self.name, "sales_invoice"):
			return

		stored = frappe.db.get_value(
			self.doctype,
			self.name,
			["service_billing_item", "hourly_rate"],
			as_dict=True,
		)
		if self.service_billing_item != stored.service_billing_item or flt(self.hourly_rate) != flt(
			stored.hourly_rate
		):
			frappe.throw(_("Billing fields cannot change after a Sales Invoice has been created."))

		stored_time = {
			row.name: row
			for row in frappe.get_all(
				"Service Work Order Time",
				filters={"parent": self.name, "parenttype": self.doctype, "parentfield": "time_entries"},
				fields=["name", "technician", "work_date", "time_type", "hours"],
			)
		}
		current_time = {row.name: row for row in self.get("time_entries") or [] if row.name}
		if set(stored_time) != set(current_time):
			frappe.throw(_("Time entries cannot change after a Sales Invoice has been created."))
		for row_name, stored_row in stored_time.items():
			current_row = current_time[row_name]
			if (
				current_row.technician != stored_row.technician
				or getdate(current_row.work_date) != getdate(stored_row.work_date)
				or current_row.time_type != stored_row.time_type
				or flt(current_row.hours) != flt(stored_row.hours)
			):
				frappe.throw(_("Time entries cannot change after a Sales Invoice has been created."))

		stored_parts = {
			row.name: row
			for row in frappe.get_all(
				"Service Work Order Part",
				filters={"parent": self.name, "parenttype": self.doctype, "parentfield": "parts"},
				fields=["name", "item", "qty", "bill_rate", "source_warehouse", "stock_entry"],
			)
		}
		current_parts = {row.name: row for row in self.get("parts") or [] if row.name}
		if set(stored_parts) != set(current_parts):
			frappe.throw(_("Part rows cannot change after a Sales Invoice has been created."))
		for row_name, stored_row in stored_parts.items():
			current_row = current_parts[row_name]
			if (
				current_row.item != stored_row.item
				or flt(current_row.qty) != flt(stored_row.qty)
				or flt(current_row.bill_rate) != flt(stored_row.bill_rate)
				or current_row.source_warehouse != stored_row.source_warehouse
				or current_row.stock_entry != stored_row.stock_entry
			):
				frappe.throw(_("Part rows cannot change after a Sales Invoice has been created."))

	def _validate_transition(self):
		if self.is_new():
			if self.status != "Draft":
				frappe.throw(_("A new Service Work Order must start in Draft."))
			return

		previous_status = frappe.db.get_value(self.doctype, self.name, "status")
		if previous_status == self.status:
			return

		if self.status not in TRANSITIONS.get(previous_status, set()):
			frappe.throw(_("Transition from {0} to {1} is not allowed.").format(previous_status, self.status))

		if self.status in TECHNICIAN_STATES:
			if not has_any_role(DISPATCHER_ROLES) and not self._is_assigned_technician():
				frappe.throw(_("Only the assigned technician can update execution status."), frappe.PermissionError)
		elif self.status in {"Scheduled", "Cancelled"}:
			require_any_role(DISPATCHER_ROLES, "Only a dispatcher or service manager can schedule or cancel work.")
		elif self.status in FINAL_STATES:
			require_any_role(MANAGER_ROLES, "Only a service manager can close work or make it invoice-ready.")

	def _validate_closeout(self):
		if self.status not in CLOSEOUT_STATES:
			return
		if not self.get("time_entries"):
			frappe.throw(_("At least one time entry is required before submitting closeout."))
		if not self.closeout_notes:
			frappe.throw(_("Closeout Notes are required before submitting closeout."))
		if not self.closeout_evidence:
			frappe.throw(_("Closeout Evidence is required before submitting closeout."))
		if self.status in FINAL_STATES and any(not row.stock_entry for row in self.get("parts") or []):
			frappe.throw(_("All declared parts must be issued before the work order can close."))

	def _validate_cannot_close(self):
		if self.status != "Cannot Close":
			return
		if not self.cannot_close_reason or not self.closure_owner or not self.closure_due_date:
			frappe.throw(_("Cannot Close requires a reason, closure owner, and due date."))
		if getdate(self.closure_due_date) < getdate(today()):
			frappe.throw(_("Closure Due Date cannot be in the past."))
		self._sync_closure_exception()

	def _validate_invoice_ready(self):
		if self.invoice_ready and self.status != "Invoice Ready":
			frappe.throw(_("Invoice Ready can only be set by the invoice-ready transition."))
		if self.status != "Invoice Ready":
			return
		if frappe.db.exists("Service Closure Exception", {"work_order": self.name, "status": "Open"}):
			frappe.throw(_("Open closure exceptions block invoice readiness."))
		self.invoice_ready = 1

	def _update_profitability_projection(self):
		revenue = _projected_revenue(self)
		parts_cost = _issued_parts_cost(self)
		self.projected_revenue = revenue
		self.issued_parts_cost = parts_cost
		self.projected_margin_before_labor = revenue - parts_cost
		self.projected_margin_percent = (self.projected_margin_before_labor / revenue * 100) if revenue else 0
		self.profitability_basis = _(
			"Projected from labor/part bill rates and submitted ERPNext Stock Entry costs. Labor overhead is excluded."
		)

	def _sync_closure_exception(self):
		if self.closure_exception:
			exception = frappe.get_doc("Service Closure Exception", self.closure_exception)
			exception.reason = self.cannot_close_reason
			exception.exception_owner = self.closure_owner
			exception.due_date = self.closure_due_date
			exception.status = "Open"
			exception.save(ignore_permissions=True)
			return

		exception = frappe.get_doc(
			{
				"doctype": "Service Closure Exception",
				"work_order": self.name,
				"reason": self.cannot_close_reason,
				"exception_owner": self.closure_owner,
				"due_date": self.closure_due_date,
				"status": "Open",
			}
		)
		exception.flags.from_work_order = True
		exception.insert(ignore_permissions=True)
		self.closure_exception = exception.name

	def _is_assigned_technician(self):
		return self.assigned_technician == frappe.session.user

	def _is_technician_only(self):
		roles = {"Service Technician"}
		return "Service Technician" in frappe.get_roles() and not has_any_role(DISPATCHER_ROLES | roles)

	def _require_manager(self):
		require_any_role(MANAGER_ROLES, "Only a service manager can issue inventory for a work order.")

	def _require_finance(self):
		require_any_role(
			FINANCE_ROLES,
			"Only an Accounts User or Accounts Manager can draft a Sales Invoice.",
		)


@frappe.whitelist()
def issue_parts(name):
	return _with_transaction_retry(lambda: _issue_parts(name))


def _issue_parts(name):
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("write")
	work_order._require_manager()

	# Lock the parent record before checking unissued rows, so retries cannot create duplicate stock issues.
	frappe.db.sql("SELECT `name` FROM `tabService Work Order` WHERE `name` = %s FOR UPDATE", name)
	work_order.reload()

	if work_order.status not in {"Closeout Submitted", "Closed"}:
		frappe.throw(_("Parts can be issued only after closeout is submitted."))

	unissued_parts = [row for row in work_order.get("parts") or [] if not row.stock_entry]
	if not unissued_parts:
		existing_entries = {row.stock_entry for row in work_order.get("parts") or [] if row.stock_entry}
		if len(existing_entries) == 1:
			return existing_entries.pop()
		if existing_entries:
			frappe.throw(_("Issued parts must reference exactly one Stock Entry for an idempotent retry."))
		return None

	company = _company_for_parts(unissued_parts)

	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"purpose": "Material Issue",
			"stock_entry_type": "Material Issue",
			"company": company,
			"remarks": _("Issued from Service Work Order {0}").format(work_order.name),
			"items": [
				{"item_code": row.item, "qty": row.qty, "s_warehouse": row.source_warehouse}
				for row in unissued_parts
			],
		}
	)
	stock_entry.insert()
	stock_entry.submit()

	work_order.flags.from_stock_issue = True
	for row in unissued_parts:
		row.stock_entry = stock_entry.name
	work_order.save()
	return stock_entry.name


@frappe.whitelist()
def make_draft_sales_invoice(name):
	return _with_transaction_retry(lambda: _make_draft_sales_invoice(name))


def _make_draft_sales_invoice(name):
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")
	work_order._require_finance()
	frappe.has_permission("Sales Invoice", ptype="create", throw=True)

	frappe.db.sql("SELECT `name` FROM `tabService Work Order` WHERE `name` = %s FOR UPDATE", name)
	work_order.reload()

	existing_invoice = _existing_sales_invoice(work_order)
	if existing_invoice:
		if work_order.sales_invoice != existing_invoice:
			work_order.flags.from_invoice_creation = True
			work_order.sales_invoice = existing_invoice
			work_order.save(ignore_permissions=True)
		return existing_invoice

	_validate_invoice_creation(work_order)
	invoice = _build_sales_invoice(work_order)
	invoice.insert()

	work_order.flags.from_invoice_creation = True
	work_order.sales_invoice = invoice.name
	work_order.save(ignore_permissions=True)
	return invoice.name


def _with_transaction_retry(operation):
	"""Retry only Frappe's transient row-change/deadlock signal."""
	for attempt in range(MAX_TRANSACTION_RETRIES):
		try:
			return operation()
		except frappe.QueryDeadlockError:
			frappe.db.rollback()
			if attempt + 1 == MAX_TRANSACTION_RETRIES:
				raise
			sleep(0.05 * (attempt + 1))


def _existing_sales_invoice(work_order):
	if work_order.sales_invoice and frappe.db.exists("Sales Invoice", work_order.sales_invoice):
		return work_order.sales_invoice

	if frappe.get_meta("Sales Invoice").has_field("service_work_order"):
		return frappe.db.get_value(
			"Sales Invoice",
			{"service_work_order": work_order.name, "docstatus": ["<", 2]},
			"name",
			order_by="creation asc",
		)

	return None


def _validate_invoice_creation(work_order):
	if work_order.status != "Invoice Ready" or not work_order.invoice_ready:
		frappe.throw(_("A Sales Invoice can be drafted only from an invoice-ready work order."))
	if frappe.db.exists("Service Closure Exception", {"work_order": work_order.name, "status": "Open"}):
		frappe.throw(_("Open closure exceptions block invoice drafting."))
	if any(not row.stock_entry for row in work_order.get("parts") or []):
		frappe.throw(_("All declared parts must be issued before drafting a Sales Invoice."))


def _build_sales_invoice(work_order):
	company = _company_for_work_order(work_order)
	income_account = _income_account(company)
	cost_center = _cost_center(company)
	items = _invoice_items(work_order, income_account, cost_center)
	if not items:
		frappe.throw(_("At least one billable time entry or part is required to draft a Sales Invoice."))

	invoice = frappe.new_doc("Sales Invoice")
	invoice.company = company
	invoice.customer = work_order.customer
	invoice.posting_date = today()
	invoice.set_posting_time = 1
	invoice.update_stock = 0
	invoice.remarks = _("Drafted from Service Work Order {0}.").format(work_order.name)
	if frappe.get_meta("Sales Invoice").has_field("service_work_order"):
		invoice.service_work_order = work_order.name

	for item in items:
		invoice.append("items", item)

	invoice.set_missing_values()
	return invoice


def _invoice_items(work_order, income_account, cost_center):
	items = []
	total_hours = sum(flt(row.hours) for row in work_order.get("time_entries") or [])
	if total_hours:
		if not work_order.service_billing_item:
			frappe.throw(_("Labor Billing Item is required before drafting a Sales Invoice."))
		if frappe.db.get_value("Item", work_order.service_billing_item, "is_stock_item"):
			frappe.throw(_("Labor Billing Item must be a non-stock Item."))
		_validate_fractional_uom(work_order.service_billing_item, total_hours, "Labor Billing Item")
		if flt(work_order.hourly_rate) <= 0:
			frappe.throw(_("Hourly Rate must be greater than zero before drafting a Sales Invoice."))
		items.append(
			_invoice_item(
				work_order.service_billing_item,
				total_hours,
				work_order.hourly_rate,
				income_account,
				cost_center,
				_("Service labor for {0}: {1}").format(work_order.name, work_order.subject),
			)
		)

	for row in work_order.get("parts") or []:
		if flt(row.bill_rate) <= 0:
			frappe.throw(_("Part Bill Rate is required for every invoiced part."))
		items.append(
			_invoice_item(
				row.item,
				row.qty,
				row.bill_rate,
				income_account,
				cost_center,
				_("Part used on Service Work Order {0}").format(work_order.name),
			)
		)

	return items


def _projected_revenue(work_order):
	labor_revenue = sum(flt(row.hours) for row in work_order.get("time_entries") or []) * flt(
		work_order.hourly_rate
	)
	parts_revenue = sum(flt(row.qty) * flt(row.bill_rate) for row in work_order.get("parts") or [])
	return labor_revenue + parts_revenue


def _issued_parts_cost(work_order):
	stock_entries = {row.stock_entry for row in work_order.get("parts") or [] if row.stock_entry}
	if not stock_entries:
		return 0

	cost = 0
	for row in frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ["in", list(stock_entries)]},
		fields=["amount", "basic_amount"],
	):
		cost += flt(row.amount) if row.amount is not None else flt(row.basic_amount)
	return cost


def _invoice_item(item_code, qty, rate, income_account, cost_center, description):
	if not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item {0} does not exist.").format(item_code))
	return {
		"item_code": item_code,
		"qty": flt(qty),
		"rate": flt(rate),
		"price_list_rate": flt(rate),
		"income_account": income_account,
		"cost_center": cost_center,
		"description": description,
	}


def _validate_fractional_uom(item_code, qty, label):
	if flt(qty) == int(flt(qty)):
		return
	stock_uom = frappe.db.get_value("Item", item_code, "stock_uom")
	if stock_uom and frappe.db.get_value("UOM", stock_uom, "must_be_whole_number"):
		frappe.throw(
			_("{0} uses UOM {1}, which does not allow fractional quantities.").format(label, stock_uom)
		)


def _company_for_work_order(work_order):
	if work_order.get("parts"):
		return _company_for_parts(work_order.get("parts"))

	company = (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)
	if not company:
		frappe.throw(_("A default Company is required before drafting a Sales Invoice."))
	return company


def _income_account(company):
	account = frappe.db.get_value("Company", company, "default_income_account") or frappe.db.get_value(
		"Account", {"company": company, "root_type": "Income", "is_group": 0}, "name"
	)
	if not account:
		frappe.throw(_("Company {0} needs a default income account for service invoicing.").format(company))
	return account


def _cost_center(company):
	cost_center = frappe.db.get_value("Company", company, "cost_center") or frappe.db.get_value(
		"Cost Center", {"company": company, "is_group": 0}, "name"
	)
	if not cost_center:
		frappe.throw(_("Company {0} needs a cost center for service invoicing.").format(company))
	return cost_center


def _company_for_parts(parts):
	companies = {frappe.db.get_value("Warehouse", row.source_warehouse, "company") for row in parts}
	if None in companies or not companies:
		frappe.throw(_("Each source warehouse must belong to a Company."))
	# ponytail: Create one Stock Entry per company when multi-company service work is a verified requirement.
	if len(companies) != 1:
		frappe.throw(_("All parts in one service issue must come from the same Company."))
	return companies.pop()
