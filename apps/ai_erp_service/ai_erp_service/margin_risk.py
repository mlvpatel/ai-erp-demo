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
# Discount / zero-rate labor is one category: zero hourly rate with billable hours.
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
	"""Attach deterministic margin_risks and margin_risk_details to each row.

	Rows need name, status, hourly_rate, warranty_status, inspection_result,
	service_asset, service_location, and creation. Categories never invent a
	margin: missing cost data becomes unknown_cost_basis instead of a number.
	Each detail links the category to checkable source facts (hours, parts,
	neighbors, exceptions) for Desk and evidence-ledger consumers.
	"""
	names = [row.name for row in rows]
	if not names:
		return rows

	hours_by_order = _hours_by_order(names)
	parts_by_order = _parts_by_order(names)
	unit_costs = _unit_costs(parts_by_order)
	open_exceptions = _open_exceptions_by_order(names)
	repeat_neighbors = _repeat_neighbors(rows)

	for row in rows:
		details = _classify_row(
			row,
			hours=hours_by_order.get(row.name, 0),
			parts=parts_by_order.get(row.name, []),
			unit_costs=unit_costs,
			open_exceptions=open_exceptions.get(row.name, []),
			neighbor_orders=repeat_neighbors.get(row.name, []),
		)
		row.margin_risk_details = details
		row.margin_risks = ", ".join(item["category"] for item in details)
	return rows


def classify_margin_risks_for_work_order(work_order):
	"""Return categories and evidence details for one work order document."""
	row = frappe._dict(
		{
			"name": work_order.name,
			"status": work_order.status,
			"hourly_rate": work_order.hourly_rate,
			"warranty_status": work_order.warranty_status,
			"inspection_result": work_order.inspection_result,
			"service_asset": work_order.service_asset,
			"service_location": work_order.service_location,
			"creation": work_order.creation,
		}
	)
	annotate_margin_risks([row])
	return {
		"categories": [item["category"] for item in row.margin_risk_details],
		"details": list(row.margin_risk_details),
	}


def _classify_row(row, hours, parts, unit_costs, open_exceptions, neighbor_orders):
	details = []
	if row.status in CLOSEOUT_STATES and not hours:
		details.append(
			{
				"category": "missing_billable_time",
				"evidence": {
					"status": row.status,
					"billable_hours": 0,
					"source": "Service Work Order Time",
				},
			}
		)
	if hours and not flt(row.hourly_rate):
		details.append(
			{
				"category": "zero_rate_labor",
				"evidence": {
					"hourly_rate": flt(row.hourly_rate),
					"billable_hours": flt(hours),
					"note": "Discount or zero-rate labor: hours present with zero hourly rate.",
					"source": "Service Work Order.hourly_rate",
				},
			}
		)

	missing_bill_items = [part.item for part in parts if not flt(part.bill_rate)]
	if missing_bill_items:
		details.append(
			{
				"category": "missing_part_bill_rate",
				"evidence": {
					"items": missing_bill_items,
					"source": "Service Work Order Part.bill_rate",
				},
			}
		)

	above_cost = []
	unknown_cost = []
	for part in parts:
		if part.stock_entry and (part.stock_entry, part.item) not in unit_costs:
			unknown_cost.append({"item": part.item, "stock_entry": part.stock_entry})
		elif (
			flt(part.bill_rate)
			and (part.stock_entry, part.item) in unit_costs
			and unit_costs[(part.stock_entry, part.item)] > flt(part.bill_rate)
		):
			above_cost.append(
				{
					"item": part.item,
					"stock_entry": part.stock_entry,
					"bill_rate": flt(part.bill_rate),
					"unit_cost": unit_costs[(part.stock_entry, part.item)],
				}
			)
	if above_cost:
		details.append(
			{
				"category": "part_cost_above_bill_rate",
				"evidence": {
					"items": above_cost,
					"source": "Stock Entry Detail.basic_rate",
				},
			}
		)
	if unknown_cost:
		details.append(
			{
				"category": "unknown_cost_basis",
				"evidence": {
					"items": unknown_cost,
					"source": "Stock Entry Detail",
					"note": "Linked stock entry has no usable unit cost; margin not invented.",
				},
			}
		)

	if row.warranty_status in WARRANTY_RISK_STATUSES:
		details.append(
			{
				"category": "warranty_risk",
				"evidence": {
					"warranty_status": row.warranty_status,
					"source": "Service Work Order.warranty_status",
				},
			}
		)
	if row.inspection_result in INSPECTION_RISK_RESULTS:
		details.append(
			{
				"category": "failed_inspection",
				"evidence": {
					"inspection_result": row.inspection_result,
					"source": "Service Work Order.inspection_result",
				},
			}
		)
	if open_exceptions:
		details.append(
			{
				"category": "unresolved_exception",
				"evidence": {
					"exceptions": open_exceptions,
					"source": "Service Closure Exception",
				},
			}
		)
	if neighbor_orders:
		# Cap linked neighbors in evidence payloads so Desk/summary JSON stays bounded.
		neighbor_cap = 10
		details.append(
			{
				"category": "repeat_visit_risk",
				"evidence": {
					"neighbor_work_orders": neighbor_orders[:neighbor_cap],
					"neighbor_count": len(neighbor_orders),
					"neighbors_truncated": len(neighbor_orders) > neighbor_cap,
					"window_days": REPEAT_VISIT_WINDOW_DAYS,
					"match": (
						{"service_asset": row.service_asset}
						if row.get("service_asset")
						else {"service_location": row.service_location}
					),
					"source": "Service Work Order",
				},
			}
		)
	return details


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


def _open_exceptions_by_order(names):
	rows = frappe.get_all(
		"Service Closure Exception",
		filters={"work_order": ("in", names), "status": "Open"},
		fields=["name", "work_order"],
		order_by="name asc",
	)
	grouped = {}
	for row in rows:
		grouped.setdefault(row.work_order, []).append(row.name)
	return grouped


def _repeat_neighbors(rows):
	"""Return work-order name → neighbor names inside the repeat-visit window."""
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
	repeats = {}
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
		matched = []
		for neighbor in by_key.get(key, []):
			if neighbor.name == row.name:
				continue
			if abs(get_datetime(neighbor.creation) - row_creation) <= window:
				matched.append(neighbor.name)
		if matched:
			repeats[row.name] = sorted(set(matched))
	return repeats


@frappe.whitelist()
def margin_leakage_summary(from_date=None, to_date=None, risk_category=None, status=None):
	"""Return aggregate margin risk counts and high-risk work orders for manager review.

	Optional risk_category, status, and date range filter the scan. Technicians
	cannot call this API.
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
		details = list(row.margin_risk_details or [])
		risks = [item["category"] for item in details]
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
				"risk_details": details,
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
		"status": status or "",
		"from_date": from_date or "",
		"to_date": to_date or "",
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
