"""Synthetic local demo data for the service-operations MVP."""

import os

import frappe
from ai_erp_core.configured_demo import seed as seed_configured_demo
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.utils import add_to_date, flt, now_datetime, today
from frappe.utils.password import update_password

from ai_erp_service.ai_erp_service.doctype.service_request.service_request import create_service_work_order

DEMO_CUSTOMER = "AI ERP Demo Customer"
DEMO_LOCATION = "AI ERP Demo Service Site"
DEMO_REQUEST_SUBJECT = "AI ERP Demo Pump Inspection"
DEMO_PART_ITEM = "AI-ERP-DEMO-PART"
DEMO_LABOR_ITEM = "AI-ERP-DEMO-LABOR"
DEMO_UOM = "AI ERP Service Hour"
DEMO_TECHNICIAN = "service.technician@example.test"
DEMO_TECHNICIAN_ALT = "service.technician.alt@example.test"
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
E2E_PROPOSAL_CONCURRENCY_PREFIX = "AI ERP E2E Proposal Concurrency"
E2E_REPAIR_MEMORY_HISTORY_PREFIX = "AI ERP E2E Repair Memory History"
E2E_REPAIR_MEMORY_CURRENT_PREFIX = "AI ERP E2E Repair Memory Current"


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
	_ensure_user(
		DEMO_TECHNICIAN_ALT,
		first_name="Service",
		last_name="Technician Alt",
		roles=("Service Technician",),
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
	update_password(DEMO_TECHNICIAN_ALT, password, logout_all_sessions=True)
	update_password(DEMO_MANAGER, password, logout_all_sessions=True)
	update_password(DEMO_DISPATCHER, password, logout_all_sessions=True)
	update_password(DEMO_FINANCE, password, logout_all_sessions=True)
	update_password(DEMO_AI_APPROVER, password, logout_all_sessions=True)
	for email in DEMO_CONCURRENT_MANAGERS:
		update_password(email, password, logout_all_sessions=True)
	update_password(DEMO_DISTRIBUTION_USER, password, logout_all_sessions=True)
	update_password(DEMO_MANUFACTURING_USER, password, logout_all_sessions=True)
	_ensure_technician_capabilities(result["warehouse"])
	other = _ensure_e2e_other_work_order(result)
	full_workflow = _make_e2e_full_workflow_order(result)
	proposal_concurrency = _make_e2e_proposal_concurrency_order(result)
	repair_history, repair_current = _make_e2e_repair_memory_pair(result)
	frappe.db.commit()
	return {
		"technician_user": DEMO_TECHNICIAN,
		"technician_alt_user": DEMO_TECHNICIAN_ALT,
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
		"proposal_concurrency_work_order": proposal_concurrency,
		"repair_memory_history_work_order": repair_history,
		"repair_memory_current_work_order": repair_current,
		"synthetic_only": True,
	}


def _ensure_technician_capabilities(warehouse):
	"""Idempotent skill/territory/van profiles for scheduling e2e and demos."""
	_upsert_technician_capability(
		DEMO_TECHNICIAN,
		skills="HVAC, Electrical",
		territories="North",
		van_warehouse=warehouse,
	)
	_upsert_technician_capability(
		DEMO_TECHNICIAN_ALT,
		skills="Plumbing",
		territories="South",
		van_warehouse="",
	)


def _upsert_technician_capability(technician, skills, territories, van_warehouse=""):
	existing = frappe.db.get_value("Service Technician Capability", {"technician": technician})
	if existing:
		doc = frappe.get_doc("Service Technician Capability", existing)
		doc.skills = skills
		doc.territories = territories
		doc.van_warehouse = van_warehouse or None
		doc.active = 1
		doc.save(ignore_permissions=True)
		return doc.name
	return (
		frappe.get_doc(
			{
				"doctype": "Service Technician Capability",
				"technician": technician,
				"skills": skills,
				"territories": territories,
				"van_warehouse": van_warehouse or None,
				"active": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _ensure_e2e_other_work_order(seed):
	"""Create a fresh unassigned record so assignment validation is repeatable."""
	# Keep this window clear of same-day / next-week e2e pollution so the
	# skill-matched technician stays available for Suggest Technicians.
	start = add_to_date(now_datetime(), days=21)
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
	document.required_skill = "HVAC"
	document.service_territory = "North"
	document.service_priority = "High"
	document.sla_due_at = add_to_date(start, days=1)
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


def _make_e2e_proposal_concurrency_order(seed):
	"""Create a closeout-submitted record so concurrent draft requests stay replayable."""
	start = now_datetime()
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{E2E_PROPOSAL_CONCURRENCY_PREFIX} {frappe.generate_hash(length=8)}",
			"customer": seed["customer"],
			"service_location": seed["service_location"],
			"description": "Synthetic concurrency fixture; no customer data.",
			"status": "Draft",
		}
	).insert()
	document.assigned_technician = DEMO_TECHNICIAN
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=1)
	document.status = "Scheduled"
	document.save()
	document.status = "In Progress"
	document.save()
	document.append(
		"time_entries",
		{
			"technician": DEMO_TECHNICIAN,
			"work_date": now_datetime().date(),
			"time_type": "Work",
			"hours": 1,
		},
	)
	document.closeout_notes = "Synthetic concurrency fixture closeout."
	document.closeout_evidence = "/private/files/synthetic-closeout-evidence.txt"
	document.status = "Closeout Submitted"
	document.save()
	return document.name


def _make_e2e_repair_memory_pair(seed):
	"""Closed history plus a scheduled current order for citation-matched repair memory.

	Uses a dedicated location so other Closed demo rows at the shared site cannot
	fill the five-row history cap and dilute the citation assertion.
	"""
	start = now_datetime()
	location = (
		frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": f"AI ERP E2E Repair Memory Site {frappe.generate_hash(length=8)}",
				"customer": seed["customer"],
				"default_warehouse": seed["warehouse"],
				"notes": "Synthetic repair-memory e2e site. Do not replace with customer data.",
			}
		)
		.insert()
		.name
	)
	history = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{E2E_REPAIR_MEMORY_HISTORY_PREFIX} {frappe.generate_hash(length=8)}",
			"customer": seed["customer"],
			"service_location": location,
			"description": "Synthetic repair-memory history; no customer data.",
			"status": "Draft",
		}
	).insert()
	history.assigned_technician = DEMO_TECHNICIAN
	history.scheduled_start = add_to_date(start, days=-7)
	history.scheduled_end = add_to_date(start, days=-7, hours=2)
	history.status = "Scheduled"
	history.save()
	history.status = "In Progress"
	history.save()
	history.append(
		"time_entries",
		{
			"technician": DEMO_TECHNICIAN,
			"work_date": now_datetime().date(),
			"time_type": "Work",
			"hours": 1,
		},
	)
	# Notes alone are actionable repair facts; skip parts so close does not
	# require a Material Issue in the e2e seed path.
	history.closeout_notes = "Synthetic prior fix: replaced demo part and verified seal."
	history.closeout_evidence = "/private/files/synthetic-closeout-evidence.txt"
	history.status = "Closeout Submitted"
	history.save()
	history.status = "Closed"
	history.save()

	current = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{E2E_REPAIR_MEMORY_CURRENT_PREFIX} {frappe.generate_hash(length=8)}",
			"customer": seed["customer"],
			"service_location": location,
			"description": "Synthetic repair-memory current visit; no customer data.",
			"status": "Draft",
		}
	).insert()
	current.assigned_technician = DEMO_TECHNICIAN
	current.scheduled_start = start
	current.scheduled_end = add_to_date(start, hours=2)
	current.status = "Scheduled"
	current.save()
	return history.name, current.name


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


RICH_SUBJECT_PREFIX = "AI ERP Rich Demo"
RICH_CUSTOMER_PREFIX = "Synthetic Facility"
RICH_CUSTOMERS = 12
RICH_TECHNICIANS = tuple(
	f"rich.technician.{index}@example.test" for index in range(1, 5)
)
RICH_STATUS_MIX = (
	"Scheduled",
	"In Progress",
	"In Progress",
	"Closeout Submitted",
	"Closed",
	"Invoice Ready",
)
RICH_SUBJECT_THEMES = (
	"HVAC quarterly service",
	"Pump vibration diagnosis",
	"Compressor belt replacement",
	"Chiller inspection",
	"Conveyor motor overhaul",
)


def seed_rich_demo():
	"""Layer a bounded, idempotent synthetic service portfolio over the base seed.

	Everything stays synthetic and reversible: fixed customer and subject
	prefixes make each record findable and re-runs skip existing records. The
	layer performs no parts issue, no invoice drafting, and no AI mutation, so
	the demo presenter still drives every transaction live.
	"""
	base = seed_service_demo()
	technicians = [
		_ensure_user(
			email,
			first_name="Rich",
			last_name=f"Technician {index}",
			roles=("Service Technician", "AI Proposal Requester"),
		)
		for index, email in enumerate(RICH_TECHNICIANS, 1)
	]
	created = {"customers": 0, "locations": 0, "work_orders": 0, "cannot_close": 0}
	start = now_datetime()
	for customer_index in range(1, RICH_CUSTOMERS + 1):
		customer_name = f"{RICH_CUSTOMER_PREFIX} {customer_index:02d}"
		customer = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
		if not customer:
			customer = (
				frappe.get_doc(
					{
						"doctype": "Customer",
						"customer_name": customer_name,
						"customer_type": "Company",
					}
				)
				.insert()
				.name
			)
			created["customers"] += 1
		location_name = f"{customer_name} Plant"
		location = frappe.db.get_value(
			"Service Location", {"location_name": location_name, "customer": customer}, "name"
		)
		if not location:
			location = (
				frappe.get_doc(
					{
						"doctype": "Service Location",
						"location_name": location_name,
						"customer": customer,
						"default_warehouse": base["warehouse"],
						"notes": "Synthetic rich demo site. Do not replace with customer data.",
					}
				)
				.insert()
				.name
			)
			created["locations"] += 1
		for order_index, status in enumerate(RICH_STATUS_MIX, 1):
			subject = (
				f"{RICH_SUBJECT_PREFIX} {customer_index:02d}-{order_index} "
				f"{RICH_SUBJECT_THEMES[(customer_index + order_index) % len(RICH_SUBJECT_THEMES)]}"
			)
			if frappe.db.exists("Service Work Order", {"subject": subject}):
				continue
			technician = technicians[(customer_index + order_index) % len(technicians)]
			_make_rich_work_order(
				subject, customer, location, technician, status, base, start, order_index
			)
			created["work_orders"] += 1
		if customer_index % 4 == 0:
			blocked_subject = f"{RICH_SUBJECT_PREFIX} {customer_index:02d}-blocked Parts delay"
			if not frappe.db.exists("Service Work Order", {"subject": blocked_subject}):
				_make_rich_cannot_close(
					blocked_subject, customer, location, technicians[0], base, start
				)
				created["cannot_close"] += 1
	frappe.db.commit()
	return {"synthetic_only": True, **created}


def _make_rich_work_order(subject, customer, location, technician, status, base, start, offset):
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": subject,
			"customer": customer,
			"service_location": location,
			"service_priority": ("Low", "Medium", "High")[offset % 3],
			"description": "Synthetic rich demo record; no customer data.",
			"status": "Draft",
		}
	).insert()
	if status == "Draft":
		return document
	document.assigned_technician = technician
	document.scheduled_start = add_to_date(start, days=offset - 3)
	document.scheduled_end = add_to_date(start, days=offset - 3, hours=2)
	document.status = "Scheduled"
	document.save()
	if status == "Scheduled":
		return document
	document.status = "In Progress"
	document.save()
	if status == "In Progress":
		if offset % 2 == 0:
			document.append(
				"parts",
				{
					"item": base["part_item"],
					"qty": 1,
					"bill_rate": 25,
					"source_warehouse": base["warehouse"],
				},
			)
			document.save()
		return document
	document.append(
		"time_entries",
		{
			"technician": technician,
			"work_date": now_datetime().date(),
			"time_type": "Work",
			"hours": 1 + (offset % 3),
		},
	)
	document.closeout_notes = "Synthetic closeout: repair completed and verified."
	document.closeout_evidence = "/private/files/synthetic-closeout-evidence.txt"
	document.status = "Closeout Submitted"
	document.save()
	if status == "Closeout Submitted":
		return document
	document.status = "Closed"
	document.save()
	if status == "Closed":
		return document
	document.status = "Invoice Ready"
	document.save()
	return document


def _make_rich_cannot_close(subject, customer, location, technician, base, start):
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": subject,
			"customer": customer,
			"service_location": location,
			"service_priority": "High",
			"description": "Synthetic rich demo record; no customer data.",
			"status": "Draft",
		}
	).insert()
	document.assigned_technician = technician
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=2)
	document.closure_owner = DEMO_MANAGER
	document.closure_due_date = today()
	document.status = "Scheduled"
	document.save()
	document.status = "In Progress"
	document.save()
	document.cannot_close_reason = "Parts unavailable"
	document.status = "Cannot Close"
	document.save()
	return document
