"""Deterministic margin-leakage classification for service work orders."""

from datetime import timedelta

import frappe
from frappe.utils import flt, get_datetime

from ai_erp_service.service_utils import FINANCE_ROLES, MANAGER_ROLES, require_any_role

REPEAT_VISIT_WINDOW_DAYS = 30
CLOSEOUT_STATES = {"Closeout Submitted", "Closed", "Invoice Ready"}
WARRANTY_RISK_STATUSES = {"Unknown", "In Warranty"}
INSPECTION_RISK_RESULTS = {"Needs Follow-up", "Failed"}
MARGIN_SUMMARY_PAGE_LENGTH = 500
MARGIN_HIGH_RISK_LIMIT = 50
MARGIN_RISK_CATEGORIES = (
	"missing_billable_time",
	"zero_rate_labor",
	"missing_part_bill_rate",
	"part_cost_above_bill_rate",
	"unknown_cost_basis",
	"warranty_risk",
	"failed_inspection",
	"unresolved_exception",
	"repeat_visit_risk",
)


def annotate_margin_risks(rows):
	"""Attach a deterministic, comma-joined margin_risks category list to each row.

	Rows need name, status, hourly_rate, warranty_status, inspection_result,
	service_asset, service_location, and creation. Categories never invent a
	margin: missing cost data becomes unknown_cost_basis instead of a number.
	"""
	names = [row.name for row in rows]
	if not names:
		return rows

	hours_by_order = _hours_by_order(names)
	parts_by_order = _parts_by_order(names)
	unit_costs = _unit_costs(parts_by_order)
	open_exceptions = set(
		frappe.get_all(
			"Service Closure Exception",
			filters={"work_order": ("in", names), "status": "Open"},
			pluck="work_order",
		)
	)
	repeat_orders = _repeat_orders(rows)

	for row in rows:
		risks = []
		parts = parts_by_order.get(row.name, [])
		if row.status in CLOSEOUT_STATES and not hours_by_order.get(row.name):
			risks.append("missing_billable_time")
		if hours_by_order.get(row.name) and not flt(row.hourly_rate):
			risks.append("zero_rate_labor")
		if any(not flt(part.bill_rate) for part in parts):
			risks.append("missing_part_bill_rate")
		if any(
			flt(part.bill_rate)
			and (part.stock_entry, part.item) in unit_costs
			and unit_costs[(part.stock_entry, part.item)] > flt(part.bill_rate)
			for part in parts
		):
			risks.append("part_cost_above_bill_rate")
		if any(
			part.stock_entry and (part.stock_entry, part.item) not in unit_costs
			for part in parts
		):
			risks.append("unknown_cost_basis")
		if row.warranty_status in WARRANTY_RISK_STATUSES:
			risks.append("warranty_risk")
		if row.inspection_result in INSPECTION_RISK_RESULTS:
			risks.append("failed_inspection")
		if row.name in open_exceptions:
			risks.append("unresolved_exception")
		if row.name in repeat_orders:
			risks.append("repeat_visit_risk")
		row.margin_risks = ", ".join(risks)
	return rows


def _hours_by_order(names):
	entries = frappe.get_all(
		"Service Work Order Time",
		filters={"parent": ("in", names), "parenttype": "Service Work Order"},
		fields=["parent", "hours"],
	)
	totals = {}
	for row in entries:
		totals[row.parent] = totals.get(row.parent, 0) + flt(row.hours)
	return totals


def _parts_by_order(names):
	parts = frappe.get_all(
		"Service Work Order Part",
		filters={"parent": ("in", names), "parenttype": "Service Work Order"},
		fields=["parent", "item", "bill_rate", "stock_entry"],
	)
	grouped = {}
	for part in parts:
		grouped.setdefault(part.parent, []).append(part)
	return grouped


def _unit_costs(parts_by_order):
	stock_entries = sorted(
		{
			part.stock_entry
			for parts in parts_by_order.values()
			for part in parts
			if part.stock_entry
		}
	)
	if not stock_entries:
		return {}
	details = frappe.get_all(
		"Stock Entry Detail",
		filters={"parent": ("in", stock_entries)},
		fields=["parent", "item_code", "basic_rate"],
	)
	# Keep the highest unit cost when an SE splits the same item across lines so
	# a cheaper batch cannot hide part_cost_above_bill_rate.
	costs = {}
	for row in details:
		key = (row.parent, row.item_code)
		rate = flt(row.basic_rate)
		if key not in costs or rate > costs[key]:
			costs[key] = rate
	return costs


def _repeat_orders(rows):
	"""Return names with another work order for the same asset or location inside the window."""
	assets = sorted({row.service_asset for row in rows if row.get("service_asset")})
	locations = sorted(
		{row.service_location for row in rows if not row.get("service_asset") and row.get("service_location")}
	)
	neighbors = []
	if assets:
		neighbors.extend(
			frappe.get_all(
				"Service Work Order",
				filters={"service_asset": ("in", assets)},
				fields=["name", "service_asset", "service_location", "creation"],
			)
		)
	if locations:
		neighbors.extend(
			frappe.get_all(
				"Service Work Order",
				filters={"service_location": ("in", locations), "service_asset": ("in", ("", None))},
				fields=["name", "service_asset", "service_location", "creation"],
			)
		)
	by_key = {}
	for neighbor in neighbors:
		key = ("asset", neighbor.service_asset) if neighbor.service_asset else ("location", neighbor.service_location)
		by_key.setdefault(key, []).append(neighbor)

	window = timedelta(days=REPEAT_VISIT_WINDOW_DAYS)
	repeats = set()
	for row in rows:
		key = (
			("asset", row.service_asset)
			if row.get("service_asset")
			else ("location", row.service_location)
			if row.get("service_location")
			else None
		)
		if not key:
			continue
		row_creation = get_datetime(row.creation)
		for neighbor in by_key.get(key, []):
			if neighbor.name == row.name:
				continue
			if abs(get_datetime(neighbor.creation) - row_creation) <= window:
				repeats.add(row.name)
				break
	return repeats


@frappe.whitelist()
def margin_leakage_summary(from_date=None, to_date=None, risk_category=None, status=None):
	"""Return aggregate margin risk counts and high-risk work orders for manager review.

	Optional risk_category filters the high-risk queue to one deterministic
	category. Technicians cannot call this API.
	"""
	require_any_role(
		(*MANAGER_ROLES, *FINANCE_ROLES),
		frappe._("Only a service manager or finance user can view margin leakage summary.")
	)
	if risk_category and risk_category not in MARGIN_RISK_CATEGORIES:
		frappe.throw(frappe._("Unsupported margin risk category."))

	filters = {}
	if status:
		filters["status"] = status
	if from_date:
		filters["creation"] = [">=", from_date]
	if to_date:
		if "creation" in filters:
			filters["creation"] = ["between", [from_date, to_date]]
		else:
			filters["creation"] = ["<=", to_date]

	rows, truncated = _load_summary_work_orders(filters)
	annotated = annotate_margin_risks(rows)
	category_counts = {category: 0 for category in MARGIN_RISK_CATEGORIES}
	high_risk_orders = []

	for row in annotated:
		risks = [r.strip() for r in (row.margin_risks or "").split(",") if r.strip()]
		for risk in risks:
			category_counts[risk] = category_counts.get(risk, 0) + 1

		if risk_category and risk_category not in risks:
			continue

		if len(risks) >= 2 or flt(row.projected_margin_percent) < 15.0 or (
			risk_category and risk_category in risks
		):
			high_risk_orders.append({
				"name": row.name,
				"customer": row.customer,
				"status": row.status,
				"margin_percent": flt(row.projected_margin_percent),
				"risks": risks,
			})

	# Worst margin first, then most risk categories, so the capped queue is useful.
	high_risk_orders.sort(
		key=lambda row: (flt(row["margin_percent"]), -len(row["risks"]), row["name"])
	)
	high_risk_truncated = len(high_risk_orders) > MARGIN_HIGH_RISK_LIMIT
	high_risk_orders = high_risk_orders[:MARGIN_HIGH_RISK_LIMIT]

	return {
		"total_orders": len(rows),
		"truncated": truncated,
		"page_limit": MARGIN_SUMMARY_PAGE_LENGTH,
		"available_categories": list(MARGIN_RISK_CATEGORIES),
		"category_counts": category_counts,
		"risk_category": risk_category or "",
		"high_risk_truncated": high_risk_truncated,
		"high_risk_limit": MARGIN_HIGH_RISK_LIMIT,
		"high_risk_orders": high_risk_orders,
	}


def _load_summary_work_orders(filters):
	"""Load newest-first work orders and detect real page truncation.

	Fetching page_limit + 1 avoids the false positive where exactly page_limit
	rows exist and `len(rows) >= page_limit` would claim truncation.
	"""
	rows = frappe.get_all(
		"Service Work Order",
		filters=filters,
		fields=[
			"name",
			"status",
			"hourly_rate",
			"warranty_status",
			"inspection_result",
			"service_asset",
			"service_location",
			"creation",
			"projected_margin_percent",
			"customer",
		],
		order_by="creation desc",
		limit_page_length=MARGIN_SUMMARY_PAGE_LENGTH + 1,
	)
	truncated = len(rows) > MARGIN_SUMMARY_PAGE_LENGTH
	if truncated:
		rows = rows[:MARGIN_SUMMARY_PAGE_LENGTH]
	return rows, truncated

