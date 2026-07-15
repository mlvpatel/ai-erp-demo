"""Disposable, synthetic-only full capacity profile for the production pilot."""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter, sleep

import frappe
import requests
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from frappe.core.doctype.user.user import generate_keys
from frappe.utils import add_to_date, now_datetime, today

from ai_erp_service.ai_drafts import request_closeout_summary
from ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order import (
	issue_parts,
	make_draft_sales_invoice,
)
from ai_erp_service.performance import (
	_profile_order,
	_run_list_scenario,
	_run_profitability_report_scenario,
	_run_queue_scenario,
	_run_search_scenario,
	_target,
	_timed_result,
	validate_profile,
)

ALLOW_VALUE = "I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY"
PROFILE_PATH = Path("/opt/ai-erp/contracts/service-operations-load-profile.json")
WARMUP_SAMPLES = 3
LIST_WORK_ORDERS = 3000
INVOICE_WORK_ORDERS = 1000
AI_WORK_ORDERS = 1000
RECEIPT_STOCK_ENTRIES = 999
CONCURRENT_REQUESTS = 10
CONCURRENT_USERS = 5


class CapacityProfileError(RuntimeError):
	"""Raised when a full-profile safety or acceptance invariant fails."""


def run(samples=100):
	"""Seed and measure the exact tracked profile on a disposable capacity site."""
	samples = int(samples)
	_preflight(samples)
	profile = validate_profile(json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
	original_user = frappe.session.user
	results = []
	context = None
	try:
		context = _seed(profile)
		results.append(_run_list_scenario(context, profile, samples))
		results.append(_run_search_scenario(context, profile, samples))
		results.append(_run_profitability_report_scenario(context, profile, samples))
		results.append(_run_queue_scenario(context, profile, samples))
		results.append(_run_invoice_capacity(context, profile))
		results.append(_run_ai_capacity(context, profile))
		concurrency = _run_parts_concurrency(context, profile)
		results.append(concurrency["scenario_result"])
		counts = _record_counts(context)
		_require(counts == profile["data_profile"], "full-profile record counts do not match the tracked contract")
		_require(all(item["status"] == "PASS" for item in results), "one or more capacity targets failed")
		evidence = {
			"schema_version": 1,
			"profile_id": profile["profile_id"],
			"mode": "disposable-synthetic-full-profile",
			"status": "PASS",
			"full_profile": True,
			"synthetic_only": True,
			"sample_count": samples,
			"record_counts": counts,
			"results": _profile_order(results, profile),
			"concurrency": concurrency["evidence"],
		}
		_write_evidence(evidence)
		return {"status": "PASS", "full_profile": True, "synthetic_only": True}
	finally:
		frappe.set_user(original_user or "Administrator")


def _preflight(samples):
	if os.environ.get("AI_ERP_FULL_CAPACITY_ALLOW") != ALLOW_VALUE:
		raise CapacityProfileError("full capacity requires the explicit disposable-run acknowledgement")
	if not str(frappe.local.site).startswith("capacity-run-") or not str(frappe.local.site).endswith(".internal"):
		raise CapacityProfileError("full capacity runs only on a generated disposable capacity site")
	if os.environ.get("AI_ERP_PROVIDER") != "template":
		raise CapacityProfileError("full capacity requires the deterministic template provider")
	if os.environ.get("AI_CONTROL_PLANE_URL", "").rstrip("/") != "http://127.0.0.1:8090":
		raise CapacityProfileError("full capacity requires its task-local control plane")
	if not os.environ.get("AI_CONTROL_PLANE_SHARED_SECRET"):
		raise CapacityProfileError("full capacity requires a task-local control-plane credential")
	if samples < 20 or samples > 250:
		raise CapacityProfileError("full capacity samples must be between 20 and 250")
	if not PROFILE_PATH.is_file():
		raise CapacityProfileError("the immutable capacity profile is unavailable")


def _seed(profile):
	frappe.set_user("Administrator")
	prefix = "CAPACITY"
	baseline = _make_accounting_baseline(prefix)
	users = _make_users(baseline)
	customers = _make_customers(profile, prefix, baseline)
	locations = _make_locations(profile, prefix, customers, baseline["warehouse"])
	service_item, stock_items = _make_items(profile, prefix)
	_make_service_requests(profile, prefix, customers, locations)
	_make_receipts(stock_items, baseline)

	list_orders = []
	invoice_orders = []
	ai_orders = []
	for index in range(profile["data_profile"]["service_work_orders"]):
		kind = "list" if index < LIST_WORK_ORDERS else "invoice" if index < LIST_WORK_ORDERS + INVOICE_WORK_ORDERS else "ai"
		work_order = _make_work_order(
			prefix=prefix,
			index=index,
			customer=customers[0],
			location=locations[0],
			technician=users["technician"],
			warehouse=baseline["warehouse"],
			stock_items=stock_items,
			service_item=service_item,
			closeout=kind != "list",
		)
		if kind == "list":
			list_orders.append(work_order)
		elif kind == "invoice":
			invoice_orders.append(work_order)
		else:
			ai_orders.append(work_order)
		if (index + 1) % 100 == 0:
			frappe.db.commit()

	_require(len(list_orders) == LIST_WORK_ORDERS, "list workload count is invalid")
	_require(len(invoice_orders) == INVOICE_WORK_ORDERS, "invoice workload count is invalid")
	_require(len(ai_orders) == AI_WORK_ORDERS, "AI workload count is invalid")
	frappe.db.commit()
	return {
		"prefix": prefix,
		"technician": users["technician"],
		"manager": users["manager"],
		"finance": users["finance"],
		"concurrent_managers": users["concurrent_managers"],
		"customer": customers[0],
		"company": baseline["company"],
		"warehouse": baseline["warehouse"],
		"service_item": service_item,
		"list_work_orders": list_orders,
		"technician_work_orders": list_orders[::2],
		"invoice_work_orders": invoice_orders,
		"ai_work_orders": ai_orders,
	}


def _make_accounting_baseline(prefix):
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": f"{prefix} Synthetic Company",
			"abbr": "CAP",
			"default_currency": "EUR",
			"country": "Germany",
			"chart_of_accounts": "Standard",
		}
	).insert(ignore_permissions=True)
	frappe.db.set_single_value("Global Defaults", "default_company", company.name)
	frappe.db.set_single_value("Global Defaults", "default_currency", "EUR")
	price_list = frappe.db.get_value("Price List", {"selling": 1, "enabled": 1}, "name")
	if not price_list:
		price_list = frappe.get_doc(
			{
				"doctype": "Price List",
				"price_list_name": f"{prefix} Selling",
				"currency": "EUR",
				"selling": 1,
				"enabled": 1,
			}
		).insert(ignore_permissions=True).name
	frappe.db.set_single_value("Selling Settings", "selling_price_list", price_list)
	parent = frappe.db.get_value("Warehouse", {"company": company.name, "is_group": 1}, "name")
	warehouse = frappe.get_doc(
		{
			"doctype": "Warehouse",
			"warehouse_name": f"{prefix} Parts",
			"company": company.name,
			"parent_warehouse": parent,
			"is_group": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
	return {"company": company.name, "currency": "EUR", "price_list": price_list, "warehouse": warehouse.name}


def _make_users(baseline):
	technician = _make_user("capacity.technician@example.test", ["Service Technician", "AI Proposal Requester"])
	manager = _make_user("capacity.manager@example.test", ["Service Manager", "Stock User"])
	finance = _make_user("capacity.finance@example.test", ["Accounts User"])
	concurrent = [
		_make_user(f"capacity.concurrent.manager.{index}@example.test", ["Service Manager", "Stock User"])
		for index in range(1, CONCURRENT_USERS + 1)
	]
	for user in [manager, finance, *concurrent]:
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": baseline["company"],
				"is_default": 1,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("Company", baseline["company"], user=user)
		frappe.defaults.set_user_default("Selling Price List", baseline["price_list"], user=user)
		frappe.defaults.set_user_default("Currency", baseline["currency"], user=user)
		frappe.clear_cache(user=user)
	return {"technician": technician, "manager": manager, "finance": finance, "concurrent_managers": concurrent}


def _make_user(email, roles):
	return frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Synthetic Capacity",
			"enabled": 1,
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role} for role in roles],
		}
	).insert(ignore_permissions=True).name


def _make_customers(profile, prefix, baseline):
	customers = []
	for index in range(profile["data_profile"]["customers"]):
		customers.append(
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": f"{prefix} Synthetic Customer {index:04d}",
					"customer_type": "Company",
					"default_currency": baseline["currency"],
					"default_price_list": baseline["price_list"],
				}
			).insert(ignore_permissions=True).name
		)
	return customers


def _make_locations(profile, prefix, customers, warehouse):
	locations = []
	for index in range(profile["data_profile"]["service_locations"]):
		locations.append(
			frappe.get_doc(
				{
					"doctype": "Service Location",
					"location_name": f"{prefix} Synthetic Location {index:04d}",
					"customer": customers[index % len(customers)],
					"default_warehouse": warehouse,
					"notes": "Synthetic capacity record; no customer data.",
				}
			).insert(ignore_permissions=True).name
		)
	return locations


def _make_items(profile, prefix):
	if not frappe.db.exists("UOM", "Capacity Service Hour"):
		frappe.get_doc(
			{
				"doctype": "UOM",
				"uom_name": "Capacity Service Hour",
				"enabled": 1,
				"must_be_whole_number": 0,
			}
		).insert(ignore_permissions=True)
	service_item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": f"{prefix}-LABOR",
			"item_name": f"{prefix} Synthetic Labor",
			"item_group": "All Item Groups",
			"stock_uom": "Capacity Service Hour",
			"is_stock_item": 0,
			"is_sales_item": 1,
		}
	).insert(ignore_permissions=True).name
	stock_items = []
	for index in range(profile["data_profile"]["items"] - 1):
		stock_items.append(
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": f"{prefix}-PART-{index:04d}",
					"item_name": f"{prefix} Synthetic Part {index:04d}",
					"item_group": "All Item Groups",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"is_sales_item": 1,
				}
			).insert(ignore_permissions=True).name
		)
	return service_item, stock_items


def _make_service_requests(profile, prefix, customers, locations):
	for index in range(profile["data_profile"]["service_requests"]):
		customer_index = index % len(customers)
		frappe.get_doc(
			{
				"doctype": "Service Request",
				"subject": f"{prefix} Synthetic Request {index:05d}",
				"customer": customers[customer_index],
				"service_location": locations[customer_index * 2],
				"description": "Synthetic capacity request; no customer data.",
			}
		).insert(ignore_permissions=True)
		if (index + 1) % 100 == 0:
			frappe.db.commit()


def _make_receipts(stock_items, baseline):
	for index in range(RECEIPT_STOCK_ENTRIES):
		make_stock_entry(
			item_code=stock_items[index % len(stock_items)],
			qty=100,
			to_warehouse=baseline["warehouse"],
			rate=10,
			purpose="Material Receipt",
			company=baseline["company"],
		)
		if (index + 1) % 25 == 0:
			frappe.db.commit()
	frappe.db.commit()


def _make_work_order(prefix, index, customer, location, technician, warehouse, stock_items, service_item, closeout):
	frappe.set_user("Administrator")
	document = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{prefix} Synthetic Work Order {index:05d}",
			"customer": customer,
			"service_location": location,
			"status": "Draft",
		}
	).insert(ignore_permissions=True)
	start = now_datetime()
	document.assigned_technician = technician if index % 2 == 0 else "Administrator"
	document.scheduled_start = start
	document.scheduled_end = add_to_date(start, hours=1)
	document.status = "Scheduled"
	document.save(ignore_permissions=True)
	if closeout:
		document.assigned_technician = technician
		document.status = "In Progress"
		document.save(ignore_permissions=True)
	for row_index in range(2):
		document.append(
			"time_entries",
			{
				"technician": document.assigned_technician,
				"work_date": today(),
				"time_type": "Work" if row_index == 0 else "Travel",
				"hours": 1,
			},
		)
		document.append(
			"parts",
			{
				"item": stock_items[(index * 2 + row_index) % len(stock_items)],
				"qty": 1,
				"bill_rate": 25,
				"source_warehouse": warehouse,
			},
		)
	document.service_billing_item = service_item
	document.hourly_rate = 80
	if closeout:
		document.closeout_notes = "Synthetic capacity closeout; no customer data."
		document.closeout_evidence = "/private/files/synthetic-capacity-evidence.txt"
		document.status = "Closeout Submitted"
	document.save(ignore_permissions=True)
	return document.name


def _run_invoice_capacity(context, profile):
	scenario_id = "invoice-ready-draft-invoice"
	target = _target(profile, scenario_id)
	measurements = []
	invoices = []
	frappe.set_user(context["manager"])
	for index, name in enumerate(context["invoice_work_orders"]):
		issue_parts(name)
		document = frappe.get_doc("Service Work Order", name)
		document.status = "Closed"
		document.save()
		document.status = "Invoice Ready"
		document.save()
		frappe.set_user(context["finance"])
		started = perf_counter()
		invoice = make_draft_sales_invoice(name)
		frappe.db.commit()
		measurements.append(perf_counter() - started)
		invoices.append(invoice)
		frappe.set_user(context["manager"])
		if (index + 1) % 25 == 0:
			frappe.clear_cache()
	frappe.set_user(context["finance"])
	for name, invoice in zip(context["invoice_work_orders"], invoices, strict=True):
		_require(make_draft_sales_invoice(name) == invoice, "invoice retry created a duplicate")
	_require(len(set(invoices)) == INVOICE_WORK_ORDERS, "invoice count is not unique")
	return _timed_result(scenario_id, measurements[WARMUP_SAMPLES:], target)


def _run_ai_capacity(context, profile):
	scenario_id = "ai-closeout-draft"
	target = _target(profile, scenario_id)
	measurements = []
	proposals = []
	frappe.set_user(context["technician"])
	for name in context["ai_work_orders"]:
		started = perf_counter()
		proposal = request_closeout_summary(name)["name"]
		frappe.db.commit()
		measurements.append(perf_counter() - started)
		proposals.append(proposal)
	for name, proposal in zip(context["ai_work_orders"], proposals, strict=True):
		_require(request_closeout_summary(name)["name"] == proposal, "AI retry created a duplicate")
	_require(len(set(proposals)) == AI_WORK_ORDERS, "AI proposal count is not unique")
	return _timed_result(scenario_id, measurements[WARMUP_SAMPLES:], target)


def _run_parts_concurrency(context, profile):
	scenario_id = "parts-issue-idempotency"
	target = _target(profile, scenario_id)
	work_order = context["ai_work_orders"][0]
	credentials = _make_api_credentials(context["concurrent_managers"])
	frappe.db.commit()
	server = _start_local_web()
	try:
		_wait_for_web(server)
		with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
			responses = list(
				pool.map(
					lambda index: _issue_over_http(work_order, credentials[index % CONCURRENT_USERS]),
					range(CONCURRENT_REQUESTS),
				)
			)
	finally:
		server.terminate()
		try:
			server.wait(timeout=10)
		except subprocess.TimeoutExpired:
			server.kill()
	frappe.db.rollback()
	entries = set(frappe.get_all("Service Work Order Part", filters={"parent": work_order}, pluck="stock_entry"))
	entries.discard(None)
	entry_results = {result["stock_entry"] for result in responses}
	measurements = [result["elapsed"] for result in responses]
	document = frappe.get_doc("Service Work Order", work_order)
	_require(len(entries) == 1, "concurrent parts issue created an unexpected number of Stock Entries")
	_require(entry_results == entries, "concurrent retries did not return the existing Stock Entry")
	_require(all(row.stock_entry for row in document.parts), "concurrent issue left a partial parts state")
	result = _timed_result(scenario_id, measurements, target)
	return {
		"scenario_result": result,
		"evidence": {
			"request_count": CONCURRENT_REQUESTS,
			"authenticated_sessions": CONCURRENT_REQUESTS,
			"distinct_users": CONCURRENT_USERS,
			"stock_entries_created": 1,
			"unique_result_count": len(entry_results),
			"partial_issue": False,
			"retry_idempotent": True,
		},
	}


def _make_api_credentials(users):
	credentials = []
	for user_name in users:
		generate_keys(user_name)
		user = frappe.get_doc("User", user_name)
		credentials.append((user.get("api_key"), user.get_password("api_secret")))
	return credentials


def _start_local_web():
	return subprocess.Popen(
		[
			"./env/bin/gunicorn",
			"--chdir=sites",
			"--bind=127.0.0.1:8000",
			"--worker-class=gthread",
			"--threads=2",
			"--workers=5",
			"--timeout=120",
			"--access-logfile=/dev/null",
			"--error-logfile=/dev/null",
			"frappe.app:application",
		],
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
		start_new_session=True,
	)


def _wait_for_web(server):
	for _attempt in range(60):
		if server.poll() is not None:
			raise CapacityProfileError("the isolated capacity web process exited early")
		try:
			response = requests.get(
				"http://127.0.0.1:8000/api/method/ping",
				headers={"Host": str(frappe.local.site)},
				timeout=2,
			)
			if response.status_code == 200:
				return
		except requests.RequestException:
			pass
		sleep(1)
	raise CapacityProfileError("the isolated capacity web process did not become ready")


def _issue_over_http(work_order, credential):
	api_key, api_credential = credential
	session = requests.Session()
	started = perf_counter()
	response = session.post(
		"http://127.0.0.1:8000/api/method/ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.issue_parts",
		headers={
			"Host": str(frappe.local.site),
			"Authorization": f"token {api_key}:{api_credential}",
		},
		data={"name": work_order},
		timeout=120,
	)
	elapsed = perf_counter() - started
	if response.status_code != 200:
		raise CapacityProfileError("an authenticated concurrent parts request failed")
	message = response.json().get("message")
	if not message:
		raise CapacityProfileError("an authenticated concurrent retry returned no Stock Entry")
	return {"stock_entry": message, "elapsed": elapsed}


def _record_counts(context):
	prefix = context["prefix"]
	time_rows = frappe.db.sql(
		"""
		select count(*)
		from `tabService Work Order Time` child
		inner join `tabService Work Order` work_order on work_order.name = child.parent
		where child.parenttype = 'Service Work Order'
		  and child.parentfield = 'time_entries'
		  and work_order.subject like %s
		""",
		(f"{prefix}%",),
	)[0][0]
	part_rows = frappe.db.sql(
		"""
		select count(*)
		from `tabService Work Order Part` child
		inner join `tabService Work Order` work_order on work_order.name = child.parent
		where child.parenttype = 'Service Work Order'
		  and child.parentfield = 'parts'
		  and work_order.subject like %s
		""",
		(f"{prefix}%",),
	)[0][0]
	return {
		"customers": frappe.db.count("Customer", {"customer_name": ["like", f"{prefix}%"]}),
		"service_locations": frappe.db.count("Service Location", {"location_name": ["like", f"{prefix}%"]}),
		"items": frappe.db.count("Item", {"item_code": ["like", f"{prefix}%"]}),
		"service_requests": frappe.db.count("Service Request", {"subject": ["like", f"{prefix}%"]}),
		"service_work_orders": frappe.db.count("Service Work Order", {"subject": ["like", f"{prefix}%"]}),
		"service_work_order_time_rows": int(time_rows),
		"service_work_order_part_rows": int(part_rows),
		"ai_proposals": frappe.db.count("AI Proposal"),
		"stock_entries": frappe.db.count("Stock Entry"),
		"draft_sales_invoices": frappe.db.count("Sales Invoice", {"docstatus": 0}),
	}


def _write_evidence(evidence):
	path = Path(os.environ.get("CAPACITY_EVIDENCE_PATH", ""))
	if path != Path("/tmp/ai-erp-capacity-evidence.json"):
		raise CapacityProfileError("capacity evidence path is not the approved task-local path")
	path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _require(condition, message):
	if not condition:
		raise CapacityProfileError(message)
