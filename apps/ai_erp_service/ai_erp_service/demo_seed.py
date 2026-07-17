"""Synthetic local demo data for the service-operations MVP."""

import os

import frappe
from ai_erp_core.configured_demo import seed as seed_configured_demo
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
DEMO_DISPATCHER = "service.dispatcher@example.test"
DEMO_FINANCE = "service.finance@example.test"
DEMO_AI_APPROVER = "service.ai.approver@example.test"
DEMO_CONCURRENT_MANAGERS = tuple(
	f"service.manager.concurrent.{index}@example.test" for index in range(1, 6)
)
DEMO_DISTRIBUTION_USER = "distribution.user@example.test"
DEMO_MANUFACTURING_USER = "manufacturing.user@example.test"
LOCAL_SETUP_ALLOW_ENV = "AI_ERP_LOCAL_SETUP_ALLOW"
DEMO_COMPANY = "AI ERP Synthetic Demo Company"
E2E_OTHER_SUBJECT = "AI ERP E2E Assignment"
E2E_FULL_WORKFLOW_PREFIX = "AI ERP E2E Full Workflow"


def initialize_local_demo_site():
	"""Complete ERPNext setup using synthetic defaults on an opted-in local site."""
	if os.environ.get(LOCAL_SETUP_ALLOW_ENV) != "1" or not str(frappe.local.site).endswith(
		".localhost"
	):
		frappe.throw(
			f"Local setup requires {LOCAL_SETUP_ALLOW_ENV}=1 on a .localhost site.",
			frappe.PermissionError,
		)

	company = frappe.db.get_value("Company", {}, "name")
	if frappe.is_setup_complete():
		if not company:
			frappe.throw("ERPNext reports setup complete but has no Company record.")
		return {"company": company, "created": False, "synthetic_only": True}

	year = now_datetime().year
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	result = setup_complete(
		{
			"language": "English",
			"email": "demo.admin@example.test",
			"full_name": "AI ERP Demo Administrator",
			"country": "Germany",
			"timezone": "Europe/Berlin",
			"currency": "EUR",
			"enable_telemetry": 0,
			"company_name": DEMO_COMPANY,
			"company_abbr": "AIERP",
			"chart_of_accounts": "Standard",
			"fy_start_date": f"{year}-01-01",
			"fy_end_date": f"{year}-12-31",
			"domain": "Services",
			"setup_demo": 0,
		}
	)
	company = frappe.db.get_value("Company", {"company_name": DEMO_COMPANY}, "name")
	if result != {"status": "ok"} or not company or not frappe.db.exists(
		"Warehouse", {"company": company, "is_group": 0}
	):
		frappe.throw("Synthetic local ERPNext setup did not create the required accounting baseline.")
	frappe.db.commit()
	return {"company": company, "created": True, "synthetic_only": True}


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
		roles=("Service Manager", "AI Proposal Approver", "Stock User"),
	)
	_remove_roles(DEMO_MANAGER, ("Accounts User", "Accounts Manager"))
	concurrent_managers = []
	for index, email in enumerate(DEMO_CONCURRENT_MANAGERS, 1):
		concurrent_managers.append(
			_ensure_user(
				email,
				first_name="Concurrent",
				last_name=f"Manager {index}",
				roles=("Service Manager", "Stock User"),
			)
		)
		_remove_roles(email, ("Accounts User", "Accounts Manager"))
	dispatcher = _ensure_user(
		DEMO_DISPATCHER,
		first_name="Service",
		last_name="Dispatcher",
		roles=("Service Dispatcher",),
	)
	finance = _ensure_user(
		DEMO_FINANCE,
		first_name="Service",
		last_name="Finance",
		roles=("Accounts User",),
	)
	ai_approver = _ensure_user(
		DEMO_AI_APPROVER,
		first_name="AI",
		last_name="Approver",
		roles=("AI Proposal Approver",),
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
		"dispatcher_user": dispatcher,
		"finance_user": finance,
		"ai_approver_user": ai_approver,
		"concurrent_manager_users": concurrent_managers,
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
	distribution_user = _ensure_user(
		DEMO_DISTRIBUTION_USER,
		first_name="Distribution",
		last_name="User",
		roles=("Sales User", "Stock User"),
	)
	manufacturing_user = _ensure_user(
		DEMO_MANUFACTURING_USER,
		first_name="Manufacturing",
		last_name="User",
		roles=("Manufacturing User", "Stock User", "Sales User"),
	)
	distribution_demo = seed_configured_demo("distribution")
	manufacturing_demo = seed_configured_demo("light_manufacturing")
	update_password(DEMO_TECHNICIAN, password, logout_all_sessions=True)
	update_password(DEMO_MANAGER, password, logout_all_sessions=True)
	update_password(DEMO_DISPATCHER, password, logout_all_sessions=True)
	update_password(DEMO_FINANCE, password, logout_all_sessions=True)
	update_password(DEMO_AI_APPROVER, password, logout_all_sessions=True)
	for email in DEMO_CONCURRENT_MANAGERS:
		update_password(email, password, logout_all_sessions=True)
	update_password(DEMO_DISTRIBUTION_USER, password, logout_all_sessions=True)
	update_password(DEMO_MANUFACTURING_USER, password, logout_all_sessions=True)
	other = _ensure_e2e_other_work_order(result)
	full_workflow = _make_e2e_full_workflow_order(result)
	frappe.db.commit()
	return {
		"technician_user": DEMO_TECHNICIAN,
		"manager_user": DEMO_MANAGER,
		"dispatcher_user": DEMO_DISPATCHER,
		"finance_user": DEMO_FINANCE,
		"ai_approver_user": DEMO_AI_APPROVER,
		"concurrent_manager_users": list(DEMO_CONCURRENT_MANAGERS),
		"distribution_user": distribution_user,
		"manufacturing_user": manufacturing_user,
		"distribution_sales_order": distribution_demo["sales_order"],
		"manufacturing_sales_order": manufacturing_demo["sales_order"],
		"manufacturing_bom": manufacturing_demo["bom"],
		"assigned_work_order": result["service_work_order"],
		"unassigned_work_order": other,
		"full_workflow_work_order": full_workflow,
		"synthetic_only": True,
	}


def _ensure_e2e_other_work_order(seed):
	"""Create a fresh unassigned record so assignment validation is repeatable."""
	start = now_datetime()
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{E2E_OTHER_SUBJECT} {frappe.generate_hash(length=8)}",
			"customer": seed["customer"],
			"service_location": seed["service_location"],
			"status": "Draft",
		}
	).insert()
	document.assigned_technician = DEMO_MANAGER
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=1)
	document.assigned_technician = None
	document.status = "Draft"
	document.save()
	return document.name


def _make_e2e_full_workflow_order(seed):
	"""Create a fresh synthetic record so repeated browser runs never reuse posted transactions."""
	request = frappe.get_doc(
		{
			"doctype": "Service Request",
			"subject": f"{E2E_FULL_WORKFLOW_PREFIX} {frappe.generate_hash(length=8)}",
			"customer": seed["customer"],
			"service_location": seed["service_location"],
			"description": "Synthetic browser workflow; no customer data.",
		}
	).insert()
	document = frappe.get_doc("Service Work Order", create_service_work_order(request.name))
	start = now_datetime()
	document.assigned_technician = DEMO_TECHNICIAN
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=2)
	document.service_billing_item = seed["labor_item"]
	document.hourly_rate = 80
	document.append(
		"time_entries",
		{
			"technician": DEMO_TECHNICIAN,
			"work_date": now_datetime().date(),
			"time_type": "Work",
			"hours": 1,
		},
	)
	document.append(
		"parts",
		{
			"item": seed["part_item"],
			"qty": 1,
			"bill_rate": 25,
			"source_warehouse": seed["warehouse"],
		},
	)
	document.status = "Scheduled"
	document.save()
	return document.name


def _default_warehouse():
	existing_work_order = frappe.db.get_value(
		"Service Request",
		{"subject": DEMO_REQUEST_SUBJECT},
		"service_work_order",
	)
	existing_work_order_warehouse = (
		frappe.db.get_value(
			"Service Work Order Part",
			{"parent": existing_work_order},
			"source_warehouse",
		)
		if existing_work_order
		else None
	)
	if existing_work_order_warehouse and frappe.db.exists(
		"Warehouse", existing_work_order_warehouse
	):
		return existing_work_order_warehouse

	existing_demo_warehouse = frappe.db.get_value(
		"Service Location",
		{"location_name": DEMO_LOCATION},
		"default_warehouse",
	)
	if existing_demo_warehouse and frappe.db.exists("Warehouse", existing_demo_warehouse):
		return existing_demo_warehouse

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


def _remove_roles(email, roles):
	"""Keep synthetic separation-of-duties users from accumulating conflicting roles."""
	user = frappe.get_doc("User", email)
	blocked = set(roles)
	kept = [row for row in user.roles if row.role not in blocked]
	if len(kept) != len(user.roles):
		user.set("roles", kept)
		user.save()
		frappe.clear_cache(user=email)


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
