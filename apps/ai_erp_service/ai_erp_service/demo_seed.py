"""Synthetic local demo data for the service-operations MVP."""

import os

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils import add_to_date, flt, now_datetime
from frappe.utils.password import update_password

from ai_erp_service.ai_erp_service.doctype.service_request.service_request import create_service_work_order

DEMO_CUSTOMER = "AI ERP Demo Customer"
DEMO_LOCATION = "AI ERP Demo Service Site"
DEMO_REQUEST_SUBJECT = "AI ERP Demo Pump Inspection"
DEMO_PART_ITEM = "AI-ERP-DEMO-PART"
DEMO_LABOR_ITEM = "AI-ERP-DEMO-LABOR"
DEMO_UOM = "AI ERP Service Hour"
DEMO_TECHNICIAN = "service.technician@example.test"
DEMO_MANAGER = "service.manager@example.test"
E2E_OTHER_SUBJECT = "AI ERP E2E Unassigned Work Order"


def seed_service_demo():
	"""Create idempotent, synthetic records for the local service demo.

	This helper is intentionally local/demo oriented. It creates master data, a
	service request, a scheduled service work order, and initial demo stock. It
	does not issue parts from the work order, create a Sales Invoice, approve an
	AI Proposal, or perform any AI-driven ERP mutation.
	"""

	warehouse = _default_warehouse()
	company = frappe.db.get_value("Warehouse", warehouse, "company")

	customer = _ensure_customer()
	technician = _ensure_user(
		DEMO_TECHNICIAN,
		first_name="Service",
		last_name="Technician",
		roles=("Service Technician", "AI Proposal Requester"),
	)
	manager = _ensure_user(
		DEMO_MANAGER,
		first_name="Service",
		last_name="Manager",
		roles=("Service Manager", "AI Proposal Approver"),
	)
	uom = _ensure_fractional_hour_uom()
	part_item = _ensure_part_item()
	labor_item = _ensure_labor_item(uom)
	stock_entry = _ensure_initial_stock(part_item, warehouse, company)
	location = _ensure_location(customer, warehouse)
	request = _ensure_request(customer, location)
	work_order = _ensure_work_order(request.name, technician, part_item, warehouse, labor_item)

	frappe.db.commit()

	return {
		"customer": customer,
		"service_location": location,
		"technician_user": technician,
		"manager_user": manager,
		"warehouse": warehouse,
		"part_item": part_item,
		"labor_item": labor_item,
		"service_request": request.name,
		"service_work_order": work_order.name,
		"initial_stock_entry": stock_entry,
		"next_step": "Open the Service Work Order and continue from Scheduled to In Progress.",
	}


def prepare_e2e_demo():
	"""Prepare local-only synthetic users and isolation records for browser tests."""
	if os.environ.get("AI_ERP_E2E_ALLOW") != "1" or not str(frappe.local.site).endswith(".localhost"):
		frappe.throw("E2E preparation is restricted to an explicitly enabled .localhost site.")
	password = os.environ.get("E2E_USER_PASSWORD", "")
	if len(password) < 12:
		frappe.throw("E2E_USER_PASSWORD must contain at least 12 characters.")

	result = seed_service_demo()
	update_password(DEMO_TECHNICIAN, password, logout_all_sessions=True)
	update_password(DEMO_MANAGER, password, logout_all_sessions=True)
	other = _ensure_e2e_other_work_order(result)
	frappe.db.commit()
	return {
		"technician_user": DEMO_TECHNICIAN,
		"manager_user": DEMO_MANAGER,
		"assigned_work_order": result["service_work_order"],
		"unassigned_work_order": other,
		"synthetic_only": True,
	}


def _ensure_e2e_other_work_order(seed):
	existing = frappe.db.get_value("Service Work Order", {"subject": E2E_OTHER_SUBJECT}, "name")
	if existing:
		return existing
	start = now_datetime()
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": E2E_OTHER_SUBJECT,
			"customer": seed["customer"],
			"service_location": seed["service_location"],
			"status": "Draft",
		}
	).insert()
	document.assigned_technician = DEMO_MANAGER
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=1)
	document.status = "Scheduled"
	document.save()
	return document.name


def _default_warehouse():
	warehouse = frappe.db.get_value("Warehouse", {"is_group": 0}, "name")
	if not warehouse:
		frappe.throw("No non-group Warehouse exists. Complete ERPNext setup before seeding the demo.")
	return warehouse


def _ensure_customer():
	customer = frappe.db.get_value("Customer", {"customer_name": DEMO_CUSTOMER}, "name")
	if customer:
		return customer

	doc = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": DEMO_CUSTOMER,
			"customer_type": "Company",
		}
	).insert()
	return doc.name


def _ensure_location(customer, warehouse):
	location = frappe.db.get_value(
		"Service Location",
		{"location_name": DEMO_LOCATION, "customer": customer},
		"name",
	)
	if location:
		doc = frappe.get_doc("Service Location", location)
		if doc.default_warehouse != warehouse:
			doc.default_warehouse = warehouse
			doc.save()
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Service Location",
			"location_name": DEMO_LOCATION,
			"customer": customer,
			"default_warehouse": warehouse,
			"notes": "Synthetic local demo site. Do not replace with customer data.",
		}
	).insert()
	return doc.name


def _ensure_user(email, first_name, last_name, roles):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
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


def _ensure_fractional_hour_uom():
	if not frappe.db.exists("UOM", DEMO_UOM):
		frappe.get_doc(
			{
				"doctype": "UOM",
				"uom_name": DEMO_UOM,
				"enabled": 1,
				"must_be_whole_number": 0,
			}
		).insert()
	elif frappe.db.get_value("UOM", DEMO_UOM, "must_be_whole_number"):
		frappe.db.set_value("UOM", DEMO_UOM, "must_be_whole_number", 0)
	return DEMO_UOM


def _ensure_part_item():
	if frappe.db.exists("Item", DEMO_PART_ITEM):
		return DEMO_PART_ITEM

	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": DEMO_PART_ITEM,
			"item_name": "AI ERP Demo Replacement Part",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_sales_item": 1,
		}
	).insert()
	return DEMO_PART_ITEM


def _ensure_labor_item(uom):
	if frappe.db.exists("Item", DEMO_LABOR_ITEM):
		return DEMO_LABOR_ITEM

	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": DEMO_LABOR_ITEM,
			"item_name": "AI ERP Demo Service Labor",
			"item_group": "All Item Groups",
			"stock_uom": uom,
			"is_stock_item": 0,
			"is_sales_item": 1,
		}
	).insert()
	return DEMO_LABOR_ITEM


def _ensure_initial_stock(item_code, warehouse, company):
	actual_qty = flt(frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty"))
	if actual_qty >= 5:
		return None

	stock_entry = make_stock_entry(
		item_code=item_code,
		qty=5 - actual_qty,
		to_warehouse=warehouse,
		rate=10,
		purpose="Material Receipt",
		company=company,
	)
	return stock_entry.name


def _ensure_request(customer, location):
	request_name = frappe.db.get_value(
		"Service Request",
		{"subject": DEMO_REQUEST_SUBJECT, "customer": customer},
		"name",
	)
	if request_name:
		return frappe.get_doc("Service Request", request_name)

	return frappe.get_doc(
		{
			"doctype": "Service Request",
			"subject": DEMO_REQUEST_SUBJECT,
			"customer": customer,
			"service_location": location,
			"description": "Synthetic demo request: inspect a pump that is vibrating under load.",
		}
	).insert()


def _ensure_work_order(request_name, technician, part_item, warehouse, labor_item):
	work_order_name = create_service_work_order(request_name)
	work_order = frappe.get_doc("Service Work Order", work_order_name)

	if work_order.status != "Draft":
		return work_order

	start = now_datetime()
	work_order.description = work_order.description or "Synthetic demo work order for local service workflow."
	work_order.assigned_technician = technician
	work_order.scheduled_start = start
	work_order.scheduled_end = add_to_date(start, hours=2)
	work_order.service_billing_item = labor_item
	work_order.hourly_rate = 80

	if not work_order.get("parts"):
		work_order.append(
			"parts",
			{
				"item": part_item,
				"qty": 1,
				"bill_rate": 25,
				"source_warehouse": warehouse,
			},
		)

	work_order.status = "Scheduled"
	work_order.save()
	return work_order
