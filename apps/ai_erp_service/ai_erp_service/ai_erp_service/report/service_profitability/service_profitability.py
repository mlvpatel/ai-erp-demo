"""Permission-scoped service profitability projection report."""

import frappe
from frappe import _

from ai_erp_service.service_utils import MANAGER_ROLES, require_any_role


def execute(filters=None):
	require_any_role(MANAGER_ROLES, "Only a service manager can view service profitability.")
	filters = frappe._dict(filters or {})
	query_filters = {}
	if filters.status:
		query_filters["status"] = filters.status
	if filters.customer:
		query_filters["customer"] = filters.customer

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
		],
		order_by="modified desc",
		limit=500,
	)
	return _columns(), rows


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
	]
