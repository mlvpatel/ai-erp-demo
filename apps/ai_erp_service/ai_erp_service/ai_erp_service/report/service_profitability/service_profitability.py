"""Permission-scoped service profitability projection report."""

import frappe
from frappe import _

from ai_erp_service.margin_risk import MARGIN_RISK_CATEGORIES, annotate_margin_risks
from ai_erp_service.service_utils import FINANCE_ROLES, MANAGER_ROLES, require_any_role

PROFITABILITY_PAGE_LENGTH = 10_000


def execute(filters=None):
	require_any_role(
		(*MANAGER_ROLES, *FINANCE_ROLES),
		"Only a service manager or finance user can view service profitability.",
	)
	filters = frappe._dict(filters or {})
	query_filters = {}
	if filters.status:
		query_filters["status"] = filters.status
	if filters.customer:
		query_filters["customer"] = filters.customer
	if filters.from_date:
		query_filters["creation"] = [">=", filters.from_date]
	if filters.to_date:
		if "creation" in query_filters:
			query_filters["creation"] = ["between", [filters.from_date, filters.to_date]]
		else:
			query_filters["creation"] = ["<=", filters.to_date]

	rows = frappe.get_list(
		"Service Work Order",
		filters=query_filters,
		fields=[
			"name",
			"customer",
			"status",
			"projected_revenue",
			"issued_parts_cost",
			"projected_margin_before_labor",
			"projected_margin_percent",
			"invoice_ready",
			"closure_exception",
			"sales_invoice",
			"hourly_rate",
			"warranty_status",
			"inspection_result",
			"service_asset",
			"service_location",
			"creation",
		],
		order_by="modified desc",
		# Bounded by the tracked full-capacity profile: a filtered manager view
		# must return every permitted row at 5,000 work orders with headroom.
		# Fetch limit+1 so exactly PROFITABILITY_PAGE_LENGTH rows is not truncation.
		limit=PROFITABILITY_PAGE_LENGTH + 1,
	)
	truncated = len(rows) > PROFITABILITY_PAGE_LENGTH
	if truncated:
		rows = rows[:PROFITABILITY_PAGE_LENGTH]
		frappe.msgprint(
			_(
				"Showing the first {0} work orders. Narrow status, customer, or date filters; "
				"counts may understate the full queue."
			).format(PROFITABILITY_PAGE_LENGTH),
			indicator="orange",
			alert=True,
		)
	annotated = annotate_margin_risks(rows)
	risk_category = (filters.margin_risk_category or "").strip()
	if risk_category:
		if risk_category not in MARGIN_RISK_CATEGORIES:
			frappe.throw(_("Unsupported margin risk category."))
		annotated = [
			row
			for row in annotated
			if risk_category in {risk.strip() for risk in (row.margin_risks or "").split(",") if risk.strip()}
		]
	return _columns(), annotated


def _columns():
	return [
		{"fieldname": "name", "label": _("Service Work Order"), "fieldtype": "Link", "options": "Service Work Order", "width": 180},
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 180},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130},
		{"fieldname": "projected_revenue", "label": _("Projected Revenue"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "issued_parts_cost", "label": _("Issued Parts Cost"), "fieldtype": "Currency", "width": 130},
		{
			"fieldname": "projected_margin_before_labor",
			"label": _("Margin Before Labor Overhead"),
			"fieldtype": "Currency",
			"width": 190,
		},
		{"fieldname": "projected_margin_percent", "label": _("Projected Margin %"), "fieldtype": "Percent", "width": 140},
		{"fieldname": "invoice_ready", "label": _("Invoice Ready"), "fieldtype": "Check", "width": 105},
		{
			"fieldname": "closure_exception",
			"label": _("Closure Exception"),
			"fieldtype": "Link",
			"options": "Service Closure Exception",
			"width": 160,
		},
		{"fieldname": "sales_invoice", "label": _("Draft Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
		{"fieldname": "margin_risks", "label": _("Margin Risks"), "fieldtype": "Data", "width": 260},
	]
