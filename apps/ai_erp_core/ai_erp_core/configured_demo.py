"""Local-only synthetic seeds for standard-ERPNext configured demos."""

from __future__ import annotations

import os

import frappe
from frappe.utils import add_days, today

ALLOW_ENV = "AI_ERP_CONFIGURED_DEMO_ALLOW"
SAVEPOINT = "ai_erp_configured_demo"

PACKS = {"distribution", "light_manufacturing"}

DIST_CUSTOMER = "AI ERP Distribution Demo Customer"
DIST_PO = "AI-ERP-CONFIG-DEMO-DISTRIBUTION"
DIST_WAREHOUSES = ("AI ERP Distribution Source", "AI ERP Distribution Overflow")
DIST_ITEMS = ("AI-ERP-DIST-AVAILABLE", "AI-ERP-DIST-SHORTAGE")

MFG_CUSTOMER = "AI ERP Manufacturing Demo Customer"
MFG_PO = "AI-ERP-CONFIG-DEMO-MANUFACTURING"
MFG_WAREHOUSES = (
	"AI ERP Manufacturing Raw",
	"AI ERP Manufacturing WIP",
	"AI ERP Manufacturing Finished",
)
MFG_COMPONENTS = ("AI-ERP-MFG-COMPONENT-A", "AI-ERP-MFG-COMPONENT-SHORTAGE")
MFG_FINISHED_ITEM = "AI-ERP-MFG-FINISHED"


def seed(pack):
	"""Create idempotent draft-only records for a configured demo."""
	_preflight()
	pack = _pack(pack)
	company = _company()
	if pack == "distribution":
		result = _seed_distribution(company)
	else:
		result = _seed_light_manufacturing(company)
	return {"pack": pack, "synthetic_only": True, "draft_only": True, **result}


def reset(pack):
	"""Delete only draft configured-demo records; never cancel submitted work."""
	_preflight()
	pack = _pack(pack)
	frappe.db.savepoint(SAVEPOINT)
	try:
		if pack == "distribution":
			_reset_distribution()
		else:
			_reset_light_manufacturing()
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		raise
	return {"pack": pack, "reset": True, "submitted_records_cancelled": False}


def _preflight():
	if os.environ.get(ALLOW_ENV) != "1":
		frappe.throw(f"Configured demo requires explicit {ALLOW_ENV}=1.", frappe.PermissionError)
	if not str(frappe.local.site).endswith(".localhost"):
		frappe.throw("Configured demos run only on a .localhost site.", frappe.PermissionError)
	frappe.only_for("System Manager")


def _pack(pack):
	value = str(pack or "").strip()
	if value not in PACKS:
		raise ValueError(f"pack must be one of: {', '.join(sorted(PACKS))}")
	return value


def _company():
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	if not company:
		frappe.throw("Complete ERPNext company setup before seeding a configured demo.")
	return company


def _seed_distribution(company):
	warehouses = [_ensure_warehouse(name, company) for name in DIST_WAREHOUSES]
	items = [_ensure_item(code, code.replace("AI-ERP-", "AI ERP ").replace("-", " ")) for code in DIST_ITEMS]
	customer = _ensure_customer(DIST_CUSTOMER)
	order = _ensure_sales_order(
		marker=DIST_PO,
		customer=customer,
		company=company,
		warehouse=warehouses[0],
		items=[(items[0], 3, 25), (items[1], 10, 40)],
	)
	return {
		"company": company,
		"customer": customer,
		"warehouses": warehouses,
		"items": items,
		"sales_order": order,
		"next_step": "An authorized Sales Manager reviews and manually submits the draft Sales Order.",
	}


def _seed_light_manufacturing(company):
	warehouses = [_ensure_warehouse(name, company) for name in MFG_WAREHOUSES]
	components = [
		_ensure_item(code, code.replace("AI-ERP-", "AI ERP ").replace("-", " "))
		for code in MFG_COMPONENTS
	]
	finished_item = _ensure_item(MFG_FINISHED_ITEM, "AI ERP Manufacturing Finished Product")
	customer = _ensure_customer(MFG_CUSTOMER)
	bom = _ensure_bom(finished_item, company, components)
	order = _ensure_sales_order(
		marker=MFG_PO,
		customer=customer,
		company=company,
		warehouse=warehouses[2],
		items=[(finished_item, 2, 150)],
	)
	return {
		"company": company,
		"customer": customer,
		"warehouses": warehouses,
		"components": components,
		"finished_item": finished_item,
		"bom": bom,
		"sales_order": order,
		"next_step": "Authorized managers review and manually submit the BOM and Sales Order.",
	}


def _ensure_customer(customer_name):
	name = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
	if name:
		return name
	return frappe.get_doc(
		{"doctype": "Customer", "customer_name": customer_name, "customer_type": "Company"}
	).insert().name


def _ensure_item(item_code, item_name):
	if frappe.db.exists("Item", item_code):
		return item_code
	return frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_sales_item": 1,
			"is_purchase_item": 1,
		}
	).insert().name


def _ensure_warehouse(warehouse_name, company):
	name = frappe.db.get_value(
		"Warehouse", {"warehouse_name": warehouse_name, "company": company}, "name"
	)
	if name:
		return name
	parents = frappe.get_all(
		"Warehouse",
		filters={"company": company, "is_group": 1},
		pluck="name",
		order_by="lft asc",
		limit=1,
	)
	if not parents:
		frappe.throw(f"Company {company} requires a group Warehouse before configured-demo setup.")
	return frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": warehouse_name,
			"company": company,
			"parent_warehouse": parents[0],
			"is_group": 0,
		}
	).insert().name


def _ensure_sales_order(marker, customer, company, warehouse, items):
	name = frappe.db.get_value("Sales Order", {"po_no": marker}, "name")
	if name:
		docstatus = frappe.db.get_value("Sales Order", name, "docstatus")
		if docstatus != 0:
			frappe.throw(
				f"Configured-demo Sales Order {name} has advanced. Cancel it through an authorized ERP workflow before reset."
			)
		return name
	delivery_date = add_days(today(), 7)
	return frappe.get_doc(
		{
			"doctype": "Sales Order",
			"customer": customer,
			"company": company,
			"po_no": marker,
			"delivery_date": delivery_date,
			"items": [
				{
					"item_code": item_code,
					"qty": qty,
					"rate": rate,
					"warehouse": warehouse,
					"delivery_date": delivery_date,
				}
				for item_code, qty, rate in items
			],
		}
	).insert().name


def _ensure_bom(item_code, company, components):
	name = frappe.db.get_value("BOM", {"item": item_code, "docstatus": 0}, "name")
	if name:
		return name
	advanced = frappe.db.get_value("BOM", {"item": item_code, "docstatus": ["!=", 0]}, "name")
	if advanced:
		frappe.throw(
			f"Configured-demo BOM {advanced} has advanced. Cancel it through an authorized ERP workflow before reset."
		)
	return frappe.get_doc(
		{
			"doctype": "BOM",
			"item": item_code,
			"company": company,
			"quantity": 1,
			"is_active": 1,
			"is_default": 1,
			"items": [
				{"item_code": components[0], "qty": 2, "uom": "Nos", "rate": 5},
				{"item_code": components[1], "qty": 4, "uom": "Nos", "rate": 8},
			],
		}
	).insert().name


def _reset_distribution():
	_delete_draft_sales_order(DIST_PO)
	_delete_named_records("Customer", {"customer_name": DIST_CUSTOMER})
	for item in reversed(DIST_ITEMS):
		_delete_named_records("Item", {"name": item})
	for warehouse in reversed(DIST_WAREHOUSES):
		_delete_named_records("Warehouse", {"warehouse_name": warehouse})


def _reset_light_manufacturing():
	_delete_draft_sales_order(MFG_PO)
	for name in frappe.get_all("BOM", filters={"item": MFG_FINISHED_ITEM}, pluck="name"):
		_require_draft("BOM", name)
		frappe.delete_doc("BOM", name)
	_delete_named_records("Customer", {"customer_name": MFG_CUSTOMER})
	for item in reversed((*MFG_COMPONENTS, MFG_FINISHED_ITEM)):
		_delete_named_records("Item", {"name": item})
	for warehouse in reversed(MFG_WAREHOUSES):
		_delete_named_records("Warehouse", {"warehouse_name": warehouse})


def _delete_draft_sales_order(marker):
	for name in frappe.get_all("Sales Order", filters={"po_no": marker}, pluck="name"):
		_require_draft("Sales Order", name)
		frappe.delete_doc("Sales Order", name)


def _delete_named_records(doctype, filters):
	for name in frappe.get_all(doctype, filters=filters, pluck="name"):
		if doctype == "Warehouse" and frappe.db.exists(
			"Bin", {"warehouse": name, "actual_qty": ["!=", 0]}
		):
			continue
		frappe.delete_doc(doctype, name)


def _require_draft(doctype, name):
	if frappe.db.get_value(doctype, name, "docstatus") != 0:
		frappe.throw(
			f"Reset refuses to cancel or delete submitted {doctype} {name}. Use an authorized ERP workflow."
		)
