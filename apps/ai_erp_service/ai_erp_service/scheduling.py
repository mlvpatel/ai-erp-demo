"""Deterministic, propose-only technician scheduling suggestions."""

from uuid import uuid4

import frappe
from ai_erp_core.proposals import request_scheduling_explanation as store_scheduling_explanation
from frappe import _

from ai_erp_service.ai_drafts import _source
from ai_erp_service.service_utils import DISPATCHER_ROLES, require_any_role

CANDIDATE_LIMIT = 5
ACTIVE_STATUSES = ("Draft", "Scheduled", "In Progress", "Closeout Submitted", "Cannot Close")
COMPLETED_STATUSES = ("Closed", "Invoice Ready")
FAMILIARITY_WEIGHT = 2


@frappe.whitelist()
def suggest_technicians(name):
	"""Rank available technicians for one scheduled work order without assigning.

	The score is deterministic: prior completed work at the same asset or
	location counts double, open workload subtracts, ties break on workload and
	then on the technician id. Technicians with an overlapping scheduled work
	order are excluded with a reason instead of being silently hidden, and a
	missing schedule window aborts instead of guessing availability.
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

	candidates = []
	excluded = []
	for technician in technicians:
		if technician in busy:
			excluded.append({"technician": technician, "reason": "overlapping_scheduled_work"})
			continue
		technician_workload = workload.get(technician, 0)
		technician_familiarity = familiarity.get(technician, 0)
		reasons = [f"open_workload:{technician_workload}", f"completed_here:{technician_familiarity}"]
		candidates.append(
			{
				"technician": technician,
				"score": FAMILIARITY_WEIGHT * technician_familiarity - technician_workload,
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


def _scheduling_explanation_payload(work_order, suggestions):
	"""Send only ranking facts; customer, location, and contact data stay out."""
	work_order_summary = {
		"doctype": work_order.doctype,
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"service_priority": work_order.service_priority or "",
		"sla_due_at": str(work_order.sla_due_at or ""),
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
