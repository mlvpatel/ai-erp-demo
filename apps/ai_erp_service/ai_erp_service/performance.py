"""Synthetic, rollback-only performance smoke checks for service operations."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from time import perf_counter, sleep

import frappe
from frappe.desk.search import search_link
from frappe.utils import add_to_date, now_datetime, today

from ai_erp_service.ai_drafts import request_closeout_summary
from ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order import (
	make_draft_sales_invoice,
)
from ai_erp_service.ai_erp_service.report.service_profitability.service_profitability import (
	execute as profitability_report,
)

PROFILE_NAME = "service-operations-load-profile.example.json"
SAVEPOINT = "ai_erp_performance_smoke"
WARMUP_SAMPLES = 3
MAX_SMOKE_SCALE = 0.1
REQUIRED_PRIVACY_TERMS = (
	"customer exports",
	"production logs",
	"production database snapshots",
	"prompt bodies",
)
IMPLEMENTED_SCENARIOS = {
	"service-work-order-list",
	"service-work-order-search",
	"invoice-ready-draft-invoice",
	"ai-closeout-draft",
	"service-profitability-report",
	"queue-and-scheduler-backlog",
}
EXTERNAL_SCENARIOS = {
	"parts-issue-idempotency": "Executed by the five-session browser concurrency gate.",
}


class PerformanceSmokeError(RuntimeError):
	"""Raised when a smoke safety invariant is not satisfied."""


def nearest_rank_p95(values):
	"""Return the nearest-rank 95th percentile for positive measurements."""
	measurements = sorted(float(value) for value in values)
	if not measurements:
		raise ValueError("at least one measurement is required")
	if any(value < 0 for value in measurements):
		raise ValueError("measurements cannot be negative")
	return measurements[math.ceil(0.95 * len(measurements)) - 1]


def scaled_count(value, scale):
	"""Keep a scaled synthetic record count represented in smoke mode."""
	return max(2, math.ceil(int(value) * float(scale)))


def validate_profile(profile):
	"""Reject anything except the tracked synthetic planning contract."""
	if not isinstance(profile, dict) or profile.get("schema_version") != 1:
		raise ValueError("performance profile schema_version must be 1")
	if profile.get("profile_id") != "service-operations-mvp-v1":
		raise ValueError("unexpected performance profile")
	if profile.get("synthetic_only") is not True:
		raise ValueError("performance smoke accepts synthetic-only profiles")
	data_profile = profile.get("data_profile")
	targets = profile.get("targets")
	if not isinstance(data_profile, dict) or not data_profile:
		raise ValueError("performance profile is missing data or targets")
	if any(not isinstance(value, int) or value <= 0 for value in data_profile.values()):
		raise ValueError("performance profile data counts must be positive integers")
	if not isinstance(targets, dict) or not targets:
		raise ValueError("performance profile targets must be a non-empty object")
	if any(not isinstance(value, (int, float)) or value <= 0 for value in targets.values()):
		raise ValueError("performance profile targets must be positive numbers")
	privacy_rules = profile.get("privacy_rules")
	if not isinstance(privacy_rules, list) or not privacy_rules or not all(isinstance(rule, str) for rule in privacy_rules):
		raise ValueError("performance profile requires synthetic privacy rules")
	privacy_text = " ".join(privacy_rules).casefold()
	if any(term not in privacy_text for term in REQUIRED_PRIVACY_TERMS):
		raise ValueError("performance profile is missing required privacy boundaries")
	scenarios = profile.get("scenarios")
	if not isinstance(scenarios, list) or not scenarios or not all(isinstance(item, dict) for item in scenarios):
		raise ValueError("performance profile scenarios must be a non-empty list")
	scenario_ids = [scenario.get("id") for scenario in scenarios]
	if any(not isinstance(scenario_id, str) or not scenario_id for scenario_id in scenario_ids):
		raise ValueError("performance profile scenario IDs must be non-empty strings")
	if len(scenario_ids) != len(set(scenario_ids)):
		raise ValueError("performance profile scenario IDs must be unique")
	if set(scenario_ids) != IMPLEMENTED_SCENARIOS | set(EXTERNAL_SCENARIOS):
		raise ValueError("performance profile scenario catalog does not match the smoke harness")
	for scenario in scenarios:
		if scenario.get("target") not in targets:
			raise ValueError("every performance scenario must map to a configured target")
	return profile


def run(scale=0.01, samples=20, strict=True, allow_local=False):
	"""Run scaled synthetic checks and roll back their database transaction.

	This is deliberately a smoke check, not a full-profile benchmark. The return
	value contains no host names, container identifiers, secrets, or record names.
	"""
	scale = float(scale)
	samples = int(samples)
	strict = _as_bool(strict)
	allow_local = _as_bool(allow_local)
	if not allow_local:
		raise ValueError("performance smoke requires explicit allow_local=True")
	if not strict:
		raise ValueError("performance smoke requires strict threshold enforcement")
	if scale <= 0 or scale > MAX_SMOKE_SCALE:
		raise ValueError(f"smoke scale must be greater than zero and at most {MAX_SMOKE_SCALE}")
	if samples < 20:
		raise ValueError("at least 20 measured samples are required for p95")

	profile = validate_profile(json.loads(_profile_path().read_text(encoding="utf-8")))
	preflight = _preflight()
	results = []
	failures = []
	current_scenario = "preflight"
	original_user = frappe.session.user
	frappe.db.savepoint(SAVEPOINT)
	try:
		context = _seed_context(profile, scale, preflight)

		current_scenario = "service-work-order-list"
		results.append(_run_list_scenario(context, profile, samples))

		current_scenario = "service-work-order-search"
		results.append(_run_search_scenario(context, profile, samples))

		current_scenario = "service-profitability-report"
		results.append(_run_profitability_report_scenario(context, profile, samples))

		current_scenario = "queue-and-scheduler-backlog"
		results.append(_run_queue_scenario(context, profile, samples))

		current_scenario = "invoice-ready-draft-invoice"
		results.append(_run_invoice_scenario(context, profile, samples))

		current_scenario = "ai-closeout-draft"
		results.append(_run_ai_scenario(context, profile, samples))

		for scenario in profile["scenarios"]:
			if scenario["id"] in EXTERNAL_SCENARIOS:
				results.append(
					{
						"scenario": scenario["id"],
						"status": "EXTERNAL_CROSS_SESSION_GATE",
						"reason": EXTERNAL_SCENARIOS[scenario["id"]],
					}
				)

		for result in results:
			if result["status"] == "FAIL":
				failures.append(f"{result['scenario']}: p95 exceeded its smoke target")
	except Exception as exc:
		failures.append(f"{current_scenario}: execution error ({type(exc).__name__})")
	finally:
		frappe.set_user("Administrator")
		try:
			frappe.db.rollback(save_point=SAVEPOINT)
		except Exception:
			failures.append("cleanup: rollback failed")
		frappe.clear_cache()
		if original_user and frappe.db.exists("User", original_user):
			frappe.set_user(original_user)

	if failures:
		frappe.throw("Performance smoke failed: " + "; ".join(failures), frappe.ValidationError)

	return {
		"profile_id": profile["profile_id"],
		"mode": "scaled-synthetic-smoke",
		"status": "SMOKE_PASS_NOT_FULL_PROFILE",
		"full_profile": False,
		"synthetic_only": True,
		"scale": scale,
		"samples": samples,
		"strict_thresholds": strict,
		"record_counts": {
			"list_work_orders": len(context["list_work_orders"]),
			"invoice_work_orders": samples + WARMUP_SAMPLES,
			"draft_sales_invoices": samples + WARMUP_SAMPLES,
			"ai_work_orders": samples + WARMUP_SAMPLES,
			"ai_proposals": samples + WARMUP_SAMPLES,
			"service_work_orders_total": len(context["list_work_orders"]) + 2 * (samples + WARMUP_SAMPLES),
		},
		"results": _profile_order(results, profile),
	}


def _profile_path():
	for parent in Path(__file__).resolve().parents:
		candidate = parent / "tests" / "performance" / PROFILE_NAME
		if candidate.is_file():
			return candidate
	workspace_candidate = Path("/workspace/tests/performance") / PROFILE_NAME
	if workspace_candidate.is_file():
		return workspace_candidate
	raise FileNotFoundError("tracked synthetic performance profile is unavailable")


def _as_bool(value):
	if isinstance(value, bool):
		return value
	if isinstance(value, str) and value.casefold() in {"true", "1", "yes"}:
		return True
	if isinstance(value, str) and value.casefold() in {"false", "0", "no"}:
		return False
	raise ValueError("strict must be a boolean")


def _preflight():
	if os.environ.get("AI_ERP_PERFORMANCE_ALLOW") != "1":
		raise ValueError("performance smoke requires explicit local allow flag")
	if not str(frappe.local.site).endswith(".localhost"):
		raise ValueError("performance smoke runs only on a .localhost site")
	if os.environ.get("AI_ERP_PROVIDER") != "template":
		raise ValueError("performance smoke requires the deterministic template provider")
	if os.environ.get("AI_CONTROL_PLANE_URL", "").rstrip("/") != "http://ai-control-plane:8090":
		raise ValueError("performance smoke requires the local Docker control plane")
	if not os.environ.get("AI_CONTROL_PLANE_SHARED_SECRET"):
		raise ValueError("performance smoke requires a configured local control-plane credential")

	price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	price_list_values = frappe.db.get_value(
		"Price List", price_list, ["currency", "selling", "enabled"], as_dict=True
	)
	if not price_list_values or not price_list_values.selling or not price_list_values.enabled:
		raise ValueError("performance smoke requires an enabled selling price list")
	for company in frappe.get_all(
		"Company", fields=["name", "default_receivable_account"], order_by="name asc"
	):
		account_currency = frappe.db.get_value(
			"Account", company.default_receivable_account, "account_currency"
		)
		income_account = frappe.db.get_value("Company", company.name, "default_income_account") or frappe.db.get_value(
			"Account", {"company": company.name, "root_type": "Income", "is_group": 0}, "name"
		)
		cost_center = frappe.db.get_value("Company", company.name, "cost_center") or frappe.db.get_value(
			"Cost Center", {"company": company.name, "is_group": 0}, "name"
		)
		if account_currency == price_list_values.currency and income_account and cost_center:
			return {
				"company": company.name,
				"currency": account_currency,
				"price_list": price_list,
			}
	raise ValueError("no company accounting baseline matches the selling price-list currency")


def _seed_context(profile, scale, preflight):
	run_key = frappe.generate_hash(length=10).lower()
	prefix = f"PERF-{run_key.upper()}"
	frappe.set_user("Administrator")
	technician = _make_user(f"perf.tech.{run_key}@example.test", ["Service Technician", "AI Proposal Requester"])
	manager = _make_user(f"perf.manager.{run_key}@example.test", ["Service Manager"])
	finance = _make_user(f"perf.finance.{run_key}@example.test", ["Accounts User"])
	for user in (manager, finance):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": preflight["company"],
				"is_default": 1,
				"apply_to_all_doctypes": 1,
			}
		).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("Company", preflight["company"], user=user)
		frappe.defaults.set_user_default("Selling Price List", preflight["price_list"], user=user)
		frappe.defaults.set_user_default("Currency", preflight["currency"], user=user)
		frappe.clear_cache(user=user)
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": f"{prefix} Synthetic Customer",
			"customer_type": "Company",
			"default_currency": preflight["currency"],
			"default_price_list": preflight["price_list"],
		}
	).insert()
	location = frappe.get_doc(
		{
			"doctype": "Service Location",
			"location_name": f"{prefix} Synthetic Site",
			"customer": customer.name,
		}
	).insert()
	service_item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": f"{prefix}-LABOR",
			"item_name": f"{prefix} Synthetic Labor",
			"item_group": "All Item Groups",
			"stock_uom": "Nos",
			"is_stock_item": 0,
			"is_sales_item": 1,
		}
	).insert()
	work_order_count = scaled_count(profile["data_profile"]["service_work_orders"], scale)
	list_work_orders = []
	for index in range(work_order_count):
		assigned = technician if index % 2 == 0 else "Administrator"
		list_work_orders.append(
			_make_scheduled_work_order(prefix, index, customer.name, location.name, assigned).name
		)

	return {
		"prefix": prefix,
		"technician": technician,
		"manager": manager,
		"finance": finance,
		"customer": customer.name,
		"location": location.name,
		"service_item": service_item.name,
		"company": preflight["company"],
		"list_work_orders": list_work_orders,
		"technician_work_orders": list_work_orders[::2],
	}


def _make_user(email, roles):
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Synthetic Performance",
			"enabled": 1,
			"send_welcome_email": 0,
			"user_type": "System User",
			"roles": [{"role": role} for role in roles],
		}
	).insert()
	frappe.clear_cache(user=user.name)
	return user.name


def _make_scheduled_work_order(prefix, index, customer, location, technician):
	frappe.set_user("Administrator")
	work_order = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": f"{prefix} Synthetic Work Order {index:05d}",
			"customer": customer,
			"service_location": location,
			"status": "Draft",
		}
	).insert()
	start = now_datetime()
	work_order.assigned_technician = technician
	work_order.scheduled_start = start
	work_order.scheduled_end = add_to_date(start, hours=1)
	work_order.status = "Scheduled"
	work_order.save()
	return work_order


def _run_list_scenario(context, profile, samples):
	scenario_id = "service-work-order-list"
	target = _target(profile, scenario_id)
	prefix = context["prefix"]
	limit = len(context["list_work_orders"]) + 1

	def query(user):
		frappe.set_user(user)
		filters = {"subject": ["like", f"{prefix}%"], "status": "Scheduled"}
		return frappe.get_list(
			"Service Work Order",
			filters=filters,
			pluck="name",
			limit_page_length=limit,
		)

	technician_visible = set(query(context["technician"]))
	manager_visible = set(query(context["manager"]))
	_require(technician_visible == set(context["technician_work_orders"]), "technician isolation failed")
	_require(manager_visible == set(context["list_work_orders"]), "manager visibility failed")

	technician_measurements = _measure(lambda: query(context["technician"]), samples)
	manager_measurements = _measure(lambda: query(context["manager"]), samples)
	technician_p95 = nearest_rank_p95(technician_measurements)
	manager_p95 = nearest_rank_p95(manager_measurements)
	return {
		"scenario": scenario_id,
		"status": "PASS" if max(technician_p95, manager_p95) <= target else "FAIL",
		"target_seconds": target,
		"roles": {
			"Service Technician": {
				"p95_seconds": round(technician_p95, 6),
				"sample_count": len(technician_measurements),
			},
			"Service Manager": {
				"p95_seconds": round(manager_p95, 6),
				"sample_count": len(manager_measurements),
			},
		},
		"safety_invariants": "PASS",
	}


def _run_invoice_scenario(context, profile, samples):
	scenario_id = "invoice-ready-draft-invoice"
	target = _target(profile, scenario_id)
	work_orders = [
		_make_closeout_work_order(context, f"INV-{index:03d}", invoice_ready=True)
		for index in range(samples + WARMUP_SAMPLES)
	]
	measurements = []
	invoices = []
	frappe.set_user(context["finance"])
	_require(
		frappe.defaults.get_user_default("Company") == context["company"],
		"synthetic finance company default was not applied",
	)
	for work_order in work_orders:
		started = perf_counter()
		invoice = make_draft_sales_invoice(work_order)
		measurements.append(perf_counter() - started)
		invoices.append(invoice)

	for work_order, invoice in zip(work_orders, invoices, strict=True):
		_require(make_draft_sales_invoice(work_order) == invoice, "invoice retry was not idempotent")
		document = frappe.get_doc("Sales Invoice", invoice)
		_require(document.docstatus == 0 and not document.update_stock, "invoice escaped draft-only policy")
	_require(len(set(invoices)) == len(work_orders), "invoice action created an unexpected duplicate")
	return _timed_result(scenario_id, measurements[WARMUP_SAMPLES:], target)


def _run_search_scenario(context, profile, samples):
	scenario_id = "service-work-order-search"
	target = _target(profile, scenario_id)
	limit = len(context["list_work_orders"]) + 1

	def query(user):
		frappe.set_user(user)
		return search_link(
			"Service Work Order",
			context["prefix"],
			filters={"status": "Scheduled"},
			page_length=limit,
		)

	technician_visible = {row["value"] for row in query(context["technician"])}
	manager_visible = {row["value"] for row in query(context["manager"])}
	_require(technician_visible == set(context["technician_work_orders"]), "link search leaked technician scope")
	_require(manager_visible == set(context["list_work_orders"]), "link search omitted manager scope")

	technician_measurements = _measure(lambda: query(context["technician"]), samples)
	manager_measurements = _measure(lambda: query(context["manager"]), samples)
	technician_p95 = nearest_rank_p95(technician_measurements)
	manager_p95 = nearest_rank_p95(manager_measurements)
	return {
		"scenario": scenario_id,
		"status": "PASS" if max(technician_p95, manager_p95) <= target else "FAIL",
		"target_seconds": target,
		"roles": {
			"Service Technician": {"p95_seconds": round(technician_p95, 6), "sample_count": samples},
			"Service Manager": {"p95_seconds": round(manager_p95, 6), "sample_count": samples},
		},
		"safety_invariants": "PASS",
	}


def _run_profitability_report_scenario(context, profile, samples):
	scenario_id = "service-profitability-report"
	target = _target(profile, scenario_id)
	frappe.set_user(context["manager"])

	def query():
		_columns, rows = profitability_report({"customer": context["customer"]})
		return rows

	rows = query()
	visible = {row.name for row in rows}
	_require(set(context["list_work_orders"]).issubset(visible), "profitability report omitted permitted work orders")
	measurements = _measure(query, samples)
	return _timed_result(scenario_id, measurements, target)


def synthetic_queue_probe():
	"""Side-effect-free worker probe used only by an approved synthetic harness."""
	local_smoke = str(frappe.local.site).endswith(".localhost")
	capacity_acknowledgement = "I_ACKNOWLEDGE_DISPOSABLE_SYNTHETIC_CAPACITY"
	capacity_run = str(frappe.local.site).startswith("capacity-run-") and (
		os.environ.get("AI_ERP_FULL_CAPACITY_ALLOW") == capacity_acknowledgement
		or frappe.conf.get("ai_erp_full_capacity_allow") == capacity_acknowledgement
	)
	if not (local_smoke or capacity_run):
		raise PerformanceSmokeError("synthetic queue probe is restricted to an approved performance harness")
	return "ok"


def _run_queue_scenario(context, profile, samples):
	scenario_id = "queue-and-scheduler-backlog"
	target = _target(profile, scenario_id)
	frappe.set_user(context["manager"])
	started = perf_counter()
	jobs = [
		frappe.enqueue(
			"ai_erp_service.performance.synthetic_queue_probe",
			queue="short",
			timeout=30,
			enqueue_after_commit=False,
			job_id=f"{context['prefix']}-queue-{index:03d}",
		)
		for index in range(samples + WARMUP_SAMPLES)
	]
	deadline = started + target
	pending = list(jobs)
	while pending and perf_counter() < deadline:
		next_pending = []
		for job in pending:
			status = job.get_status(refresh=True)
			status_value = getattr(status, "value", str(status)).casefold()
			if status_value == "finished":
				continue
			if status_value in {"failed", "stopped", "canceled", "cancelled"}:
				raise PerformanceSmokeError("synthetic worker probe failed")
			next_pending.append(job)
		pending = next_pending
		if pending:
			sleep(0.05)
	clear_seconds = perf_counter() - started
	_require(not pending, "synthetic worker backlog did not clear within target")
	return {
		"scenario": scenario_id,
		"status": "PASS" if clear_seconds <= target else "FAIL",
		"clear_seconds": round(clear_seconds, 6),
		"target_seconds": target,
		"job_count": len(jobs),
		"safety_invariants": "PASS",
	}


def _run_ai_scenario(context, profile, samples):
	scenario_id = "ai-closeout-draft"
	target = _target(profile, scenario_id)
	work_orders = [
		_make_closeout_work_order(context, f"AI-{index:03d}", invoice_ready=False)
		for index in range(samples + WARMUP_SAMPLES)
	]
	invoices_before = frappe.db.count("Sales Invoice")
	stock_before = frappe.db.count("Stock Entry")
	measurements = []
	proposals = []
	frappe.set_user(context["technician"])
	for work_order in work_orders:
		started = perf_counter()
		result = request_closeout_summary(work_order)
		measurements.append(perf_counter() - started)
		proposals.append(result["name"])

	for work_order, proposal_name in zip(work_orders, proposals, strict=True):
		_require(request_closeout_summary(work_order)["name"] == proposal_name, "AI retry was not idempotent")
		proposal = frappe.get_doc("AI Proposal", proposal_name)
		_require(proposal.proposal_status == "Draft", "AI proposal escaped draft-only policy")
		_require(proposal.model_provider == "development-template", "AI smoke used a non-template provider")
		_require(bool(proposal.sources), "AI proposal has no citations")
	_require(frappe.db.count("Sales Invoice") == invoices_before, "AI smoke created an invoice")
	_require(frappe.db.count("Stock Entry") == stock_before, "AI smoke created a stock transaction")
	return _timed_result(scenario_id, measurements[WARMUP_SAMPLES:], target)


def _make_closeout_work_order(context, suffix, invoice_ready):
	work_order = _make_scheduled_work_order(
		f"{context['prefix']}-{suffix}",
		0,
		context["customer"],
		context["location"],
		context["technician"],
	)
	frappe.set_user(context["manager"])
	work_order.reload()
	work_order.service_billing_item = context["service_item"]
	work_order.hourly_rate = 1
	work_order.save()
	frappe.set_user(context["technician"])
	work_order.reload()
	work_order.status = "In Progress"
	work_order.save()
	work_order.append(
		"time_entries",
		{
			"technician": context["technician"],
			"work_date": today(),
			"time_type": "Work",
			"hours": 1,
		},
	)
	work_order.closeout_notes = "Synthetic performance closeout; no customer data."
	work_order.closeout_evidence = "/private/files/synthetic-performance-evidence.txt"
	work_order.status = "Closeout Submitted"
	work_order.save()
	if invoice_ready:
		frappe.set_user(context["manager"])
		work_order.reload()
		work_order.status = "Closed"
		work_order.save()
		work_order.status = "Invoice Ready"
		work_order.save()
	return work_order.name


def _measure(operation, samples):
	measurements = []
	for index in range(samples + WARMUP_SAMPLES):
		started = perf_counter()
		operation()
		elapsed = perf_counter() - started
		if index >= WARMUP_SAMPLES:
			measurements.append(elapsed)
	return measurements


def _target(profile, scenario_id):
	scenario = next(item for item in profile["scenarios"] if item["id"] == scenario_id)
	return float(profile["targets"][scenario["target"]])


def _timed_result(scenario_id, measurements, target):
	p95 = nearest_rank_p95(measurements)
	return {
		"scenario": scenario_id,
		"status": "PASS" if p95 <= target else "FAIL",
		"p95_seconds": round(p95, 6),
		"target_seconds": target,
		"sample_count": len(measurements),
		"safety_invariants": "PASS",
	}


def _require(condition, message):
	if not condition:
		raise PerformanceSmokeError(message)


def _profile_order(results, profile):
	by_id = {result["scenario"]: result for result in results}
	return [by_id[scenario["id"]] for scenario in profile["scenarios"]]
