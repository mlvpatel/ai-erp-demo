"""Deterministic, propose-only technician scheduling suggestions."""

from uuid import uuid4

import frappe
from ai_erp_core.proposals import request_scheduling_explanation as store_scheduling_explanation
from frappe import _

from ai_erp_service.ai_drafts import _source
from ai_erp_service.ai_erp_service.doctype.service_technician_capability.service_technician_capability import (
	normalize_capability_labels,
)
from ai_erp_service.service_utils import DISPATCHER_ROLES, require_any_role

CANDIDATE_LIMIT = 5
ACTIVE_STATUSES = ("Draft", "Scheduled", "In Progress", "Closeout Submitted", "Cannot Close")
COMPLETED_STATUSES = ("Closed", "Invoice Ready")
FAMILIARITY_WEIGHT = 2
SLA_HIGH_PRIORITY_WEIGHT = 3
PARTS_READINESS_WEIGHT = 2
CAPABILITY_MATCH_WEIGHT = 3


@frappe.whitelist()
def suggest_technicians(name):
	"""Rank available technicians for one scheduled work order without assigning.

	The score is deterministic: prior completed work at the same asset or
	location counts double, high SLA priority / urgent SLA adds bonus points,
	parts readiness adds bonus points, skill/territory capability matches add
	bonus points, open workload subtracts, ties break on workload and then on
	the technician id. Technicians with overlapping scheduled work or missing
	required capability evidence are excluded with a reason instead of being
	silently hidden, and a missing schedule window aborts instead of guessing
	availability. This method never assigns a technician.
	"""
	require_any_role(DISPATCHER_ROLES, _("Only a dispatcher or manager can request scheduling suggestions."))
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")
	if not work_order.scheduled_start or not work_order.scheduled_end:
		frappe.throw(_("Set the scheduled window before requesting technician suggestions."))

	technicians = _service_technicians()
	if not technicians:
		frappe.throw(_("No enabled Service Technician users exist."))

	busy = _overlapping_technicians(work_order, technicians)
	workload = _open_workload(technicians)
	familiarity = _completed_familiarity(work_order, technicians)
	parts_ready = _parts_readiness(work_order, technicians)
	capabilities = _technician_capabilities(technicians)
	required_skill = _single_capability_label(work_order.get("required_skill"))
	required_territory = _single_capability_label(work_order.get("service_territory"))

	sla_bonus = SLA_HIGH_PRIORITY_WEIGHT if work_order.service_priority in {"Emergency", "Urgent", "High"} else 0

	candidates = []
	excluded = []
	for technician in technicians:
		if technician in busy:
			excluded.append({"technician": technician, "reason": "overlapping_scheduled_work"})
			continue

		capability = capabilities.get(technician)
		capability_exclusion = _capability_exclusion_reason(
			capability, required_skill, required_territory
		)
		if capability_exclusion:
			excluded.append({"technician": technician, "reason": capability_exclusion})
			continue

		technician_workload = workload.get(technician, 0)
		technician_familiarity = familiarity.get(technician, 0)
		technician_parts = parts_ready.get(technician, False)
		parts_bonus = PARTS_READINESS_WEIGHT if technician_parts else 0
		capability_bonus = 0
		if required_skill or required_territory:
			capability_bonus = CAPABILITY_MATCH_WEIGHT

		score = (
			FAMILIARITY_WEIGHT * technician_familiarity
			+ sla_bonus
			+ parts_bonus
			+ capability_bonus
			- technician_workload
		)
		reasons = [
			f"open_workload:{technician_workload}",
			f"completed_here:{technician_familiarity}",
		]
		if sla_bonus:
			reasons.append(f"sla_priority:{work_order.service_priority}")
		if technician_parts:
			reasons.append("parts_ready:true")
		if required_skill:
			reasons.append(f"skill_match:{required_skill}")
		if required_territory:
			reasons.append(f"territory_match:{required_territory}")

		candidates.append(
			{
				"technician": technician,
				"score": score,
				"workload": technician_workload,
				"familiarity": technician_familiarity,
				"reasons": reasons,
			}
		)

	candidates.sort(key=lambda row: (-row["score"], row["workload"], row["technician"]))
	return {
		"work_order": work_order.name,
		"scheduled_start": str(work_order.scheduled_start),
		"scheduled_end": str(work_order.scheduled_end),
		"required_skill": required_skill or "",
		"service_territory": required_territory or "",
		"candidates": candidates[:CANDIDATE_LIMIT],
		"excluded": excluded,
		"assignment_note": "Suggestions only. Assignment happens through the dispatcher-saved form.",
	}


def _service_technicians():
	role_holders = frappe.get_all(
		"Has Role",
		filters={"role": "Service Technician", "parenttype": "User"},
		pluck="parent",
	)
	if not role_holders:
		return []
	return sorted(
		frappe.get_all(
			"User",
			filters={"name": ("in", sorted(set(role_holders))), "enabled": 1},
			pluck="name",
			limit_page_length=200,
		)
	)


def _overlapping_technicians(work_order, technicians):
	overlapping = frappe.get_all(
		"Service Work Order",
		filters={
			"name": ("!=", work_order.name),
			"assigned_technician": ("in", technicians),
			"status": ("in", ACTIVE_STATUSES),
			"scheduled_start": ("<", work_order.scheduled_end),
			"scheduled_end": (">", work_order.scheduled_start),
		},
		pluck="assigned_technician",
	)
	return set(overlapping)


def _open_workload(technicians):
	rows = frappe.get_all(
		"Service Work Order",
		filters={"assigned_technician": ("in", technicians), "status": ("in", ACTIVE_STATUSES)},
		fields=["assigned_technician"],
	)
	workload = {}
	for row in rows:
		workload[row.assigned_technician] = workload.get(row.assigned_technician, 0) + 1
	return workload


def _completed_familiarity(work_order, technicians):
	filters = {
		"assigned_technician": ("in", technicians),
		"status": ("in", COMPLETED_STATUSES),
		"name": ("!=", work_order.name),
	}
	if work_order.service_asset:
		filters["service_asset"] = work_order.service_asset
	elif work_order.service_location:
		filters["service_location"] = work_order.service_location
	else:
		return {}
	rows = frappe.get_all("Service Work Order", filters=filters, fields=["assigned_technician"])
	familiarity = {}
	for row in rows:
		familiarity[row.assigned_technician] = familiarity.get(row.assigned_technician, 0) + 1
	return familiarity


def _parts_warehouse(work_order):
	"""Resolve the stock warehouse for readiness checks.

	Demo seed and service locations bind stock via Service Location.default_warehouse
	or part source_warehouse rows. User.default_warehouse is not used because the
	demo does not set it and standard User has no such field.
	"""
	location = work_order.get("service_location")
	if location:
		warehouse = frappe.db.get_value("Service Location", location, "default_warehouse")
		if warehouse:
			return warehouse
	for row in work_order.get("parts") or []:
		if getattr(row, "source_warehouse", None):
			return row.source_warehouse
	return ""


def _parts_readiness(work_order, technicians):
	"""Return a map of technician -> bool indicating if declared parts are available."""
	parts = work_order.get("parts") or []
	if not parts:
		return {tech: True for tech in technicians}

	warehouse = _parts_warehouse(work_order)
	if not warehouse:
		return {tech: False for tech in technicians}

	required_items = {row.item: row.qty for row in parts}
	has_all = True
	for item, req_qty in required_items.items():
		bin_qty = frappe.db.get_value("Bin", {"item_code": item, "warehouse": warehouse}, "actual_qty") or 0
		if bin_qty < req_qty:
			has_all = False
			break
	return {tech: has_all for tech in technicians}


def _single_capability_label(raw_value):
	labels = normalize_capability_labels(raw_value)
	if not labels:
		return ""
	return sorted(labels)[0]


def _technician_capabilities(technicians):
	"""Return active skill/territory capability maps keyed by technician user."""
	if not technicians:
		return {}
	rows = frappe.get_all(
		"Service Technician Capability",
		filters={"technician": ("in", technicians), "active": 1},
		fields=["technician", "skills", "territories"],
		limit_page_length=200,
	)
	capabilities = {}
	for row in rows:
		capabilities[row.technician] = {
			"skills": normalize_capability_labels(row.skills),
			"territories": normalize_capability_labels(row.territories),
		}
	return capabilities


def _capability_exclusion_reason(capability, required_skill, required_territory):
	"""Exclude when the work order requires capability evidence the technician lacks.

	If the work order does not declare a required skill or territory, capability
	filtering is skipped so existing demos stay backward compatible.
	"""
	if not required_skill and not required_territory:
		return None
	if not capability:
		return "missing_capability_record"
	if required_skill and required_skill not in capability["skills"]:
		return "missing_skill"
	if required_territory and required_territory not in capability["territories"]:
		return "missing_territory"
	return None


@frappe.whitelist()
def request_scheduling_explanation(name):
	"""Create one cited, draft-only explanation of the current deterministic ranking."""
	require_any_role(
		DISPATCHER_ROLES, _("Only a dispatcher or manager can request a scheduling explanation.")
	)
	suggestions = suggest_technicians(name)
	work_order = frappe.get_doc("Service Work Order", name)
	payload = _scheduling_explanation_payload(work_order, suggestions)
	proposal = store_scheduling_explanation(work_order.doctype, work_order.name, payload)
	return {"name": proposal.name, "draft_content": proposal.draft_content}


REJECTION_REASON_CATEGORIES = {
	"Wrong skill or territory",
	"Parts not ready",
	"Workload conflict",
	"Customer preference",
	"Other",
}


@frappe.whitelist()
def record_suggestion_feedback(name, technician, reason_category, note=None):
	"""Capture lightweight dispatcher rejection feedback for the ranking loop.

	Feedback is stored as a Comment on the work order. It never assigns a
	technician and never posts stock, invoices, or AI proposals.
	"""
	require_any_role(
		DISPATCHER_ROLES, _("Only a dispatcher or manager can record scheduling feedback.")
	)
	if reason_category not in REJECTION_REASON_CATEGORIES:
		frappe.throw(_("Unsupported rejection reason category."))
	if not technician:
		frappe.throw(_("A rejected technician is required."))
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("write")
	safe_note = (note or "").strip()[:500]
	content = (
		f"Scheduling suggestion rejected for {technician}. "
		f"Reason: {reason_category}."
		+ (f" Note: {safe_note}" if safe_note else "")
	)
	work_order.add_comment("Info", content)
	return {
		"work_order": work_order.name,
		"technician": technician,
		"reason_category": reason_category,
		"recorded": True,
	}


def _scheduling_explanation_payload(work_order, suggestions):
	"""Send only ranking facts; customer, location, and contact data stay out."""
	work_order_summary = {
		"doctype": work_order.doctype,
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"service_priority": work_order.service_priority or "",
		"sla_due_at": str(work_order.sla_due_at or ""),
		"required_skill": suggestions.get("required_skill") or "",
		"service_territory": suggestions.get("service_territory") or "",
	}
	candidates = suggestions["candidates"]
	excluded = suggestions["excluded"]
	sources = [
		_source(
			work_order.doctype,
			work_order.name,
			"priority",
			{
				"service_priority": work_order_summary["service_priority"],
				"sla_due_at": work_order_summary["sla_due_at"],
			},
		),
		_source(
			work_order.doctype,
			work_order.name,
			"schedule",
			{
				"scheduled_start": suggestions["scheduled_start"],
				"scheduled_end": suggestions["scheduled_end"],
			},
		),
		_source(
			work_order.doctype,
			work_order.name,
			"capability",
			{
				"required_skill": work_order_summary["required_skill"],
				"service_territory": work_order_summary["service_territory"],
			},
		),
		_source(
			work_order.doctype,
			work_order.name,
			"ranking",
			{"candidates": candidates, "excluded": excluded},
		),
	]
	for candidate in candidates:
		sources.append(_source("User", candidate["technician"], "workload", candidate))
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": frappe.local.site,
		"requested_by": frappe.session.user,
		"work_order": work_order_summary,
		"candidates": candidates,
		"excluded": excluded,
		"sources": sources,
	}
