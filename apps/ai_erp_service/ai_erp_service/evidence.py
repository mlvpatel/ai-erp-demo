"""Deterministic, role-scoped evidence chain for a Service Work Order."""

import json

import frappe
from ai_erp_core.proposals import content_hash
from frappe import _
from frappe.utils import flt, get_datetime

from ai_erp_service.margin_risk import annotate_margin_risks
from ai_erp_service.service_utils import (
	FINANCE_ROLES,
	MANAGER_ROLES,
	has_any_role,
	require_any_role,
)

CLOSEOUT_STATES = {"Closeout Submitted", "Closed", "Invoice Ready"}


@frappe.whitelist()
def get_evidence_chain(name):
	"""Return the replayable request-to-invoice evidence visible to the current role.

	Every section is permission-scoped: the work order read uses the document
	permission model, related records go through frappe.get_list, and the
	finance section exists only for manager and accounts roles. Section hashes
	and the chain hash make two replays of the same visible state comparable.
	"""
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")

	sections = {
		"work_order": _identity_section(work_order),
		"service_request": _service_request_section(work_order),
		"execution": _execution_section(work_order),
		"exceptions": _exception_section(work_order),
		"ai_proposals": _proposal_section(work_order),
	}
	if has_any_role(MANAGER_ROLES) or has_any_role(FINANCE_ROLES):
		sections["finance"] = _finance_section(work_order)

	section_hashes = {key: content_hash(value) for key, value in sorted(sections.items())}
	chain = {
		"schema_version": 1,
		"work_order": work_order.name,
		"generated_for": frappe.session.user,
		"sections": sections,
		"completeness": _completeness_section(work_order),
		"section_hashes": section_hashes,
		"chain_hash": content_hash(section_hashes),
	}
	# Compact stage narrative for Desk replay; packet export still builds the
	# fuller citation-backed narrative from loaded proposal sources.
	chain["ledger_narrative"] = _ledger_narrative(
		chain,
		_proposal_citation_stubs(sections["ai_proposals"]),
		sections.get("finance") or {},
	)
	return chain


@frappe.whitelist()
def get_evidence_packet(name):
	"""Return a sanitized, manager-only export of the evidence chain.

	The packet carries identifiers, hashes, statuses, and links only: no draft
	text, prompts, provider responses, or attachment contents. Synthetic packet
	output is technical evidence, never human acceptance evidence.
	"""
	require_any_role(MANAGER_ROLES, _("Only a service manager can export the evidence packet."))
	chain = get_evidence_chain(name)
	sections = chain["sections"]
	citations = []
	for proposal in sections["ai_proposals"]:
		document = frappe.get_doc("AI Proposal", proposal["name"])
		citations.extend(
			{
				"proposal": proposal["name"],
				"source_doctype": row.source_doctype,
				"source_name": row.source_name,
				"source_field": row.source_field,
				"content_hash": row.content_hash,
			}
			for row in document.get("sources") or []
		)
	finance = sections.get("finance") or {}
	work_order = sections["work_order"]
	ledger_narrative = _ledger_narrative(chain, citations, finance)
	return {
		"schema_version": 1,
		"packet_kind": "evidence_to_cash_ledger",
		"title": f"Evidence-to-cash ledger for {work_order.get('name')}",
		"generated_for": chain["generated_for"],
		"work_order": work_order,
		"ledger_narrative": ledger_narrative,
		"proposals": sections["ai_proposals"],
		"policy_decisions": sorted({row["policy_outcome"] for row in sections["ai_proposals"]}),
		"citations": citations,
		"stock_entries": finance.get("stock_entries", []),
		"sales_invoice": finance.get("sales_invoice", ""),
		"margin_risks": finance.get("margin_risks", []),
		"unresolved_exceptions": [
			row for row in sections["exceptions"] if row.get("status") == "Open"
		],
		"completeness": chain["completeness"],
		"section_hashes": chain["section_hashes"],
		"chain_hash": chain["chain_hash"],
		"synthetic_note": (
			"Synthetic export evidence; not human acceptance evidence, "
			"production audit proof, or GDPR compliance evidence."
		),
	}


def _identity_section(work_order):
	return {
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"customer": work_order.customer,
		"service_location": work_order.service_location,
		"service_asset": work_order.service_asset or "",
		"service_priority": work_order.service_priority or "",
		"sla_due_at": str(work_order.sla_due_at or ""),
		"warranty_status": work_order.warranty_status or "",
		"inspection_required": bool(work_order.inspection_required),
		"assigned_technician": work_order.assigned_technician or "",
		"scheduled_start": str(work_order.scheduled_start or ""),
		"scheduled_end": str(work_order.scheduled_end or ""),
	}


def _service_request_section(work_order):
	if not work_order.service_request or not frappe.has_permission("Service Request", "read"):
		return {}
	summary = frappe.get_list(
		"Service Request",
		filters={"name": work_order.service_request},
		fields=["name", "subject", "status"],
		limit_page_length=1,
	)
	return summary[0] if summary else {"name": work_order.service_request, "visible": False}


def _execution_section(work_order):
	return {
		"time_entries": [
			{
				"technician": row.technician,
				"work_date": str(row.work_date),
				"time_type": row.time_type,
				"hours": flt(row.hours),
			}
			for row in work_order.get("time_entries") or []
		],
		"parts": [
			{
				"item": row.item,
				"qty": flt(row.qty),
				"source_warehouse": row.source_warehouse,
				"stock_entry": row.stock_entry or "",
			}
			for row in work_order.get("parts") or []
		],
		"inspection_result": work_order.inspection_result or "",
		"inspection_notes": work_order.inspection_notes or "",
		"closeout_notes": work_order.closeout_notes or "",
		"closeout_evidence": work_order.closeout_evidence or "",
		"cannot_close_reason": work_order.cannot_close_reason or "",
	}


def _exception_section(work_order):
	if not frappe.has_permission("Service Closure Exception", "read"):
		return []
	return frappe.get_list(
		"Service Closure Exception",
		filters={"work_order": work_order.name},
		fields=["name", "status", "reason", "exception_owner", "due_date", "resolution_note"],
		order_by="name asc",
		limit_page_length=50,
	)


def _proposal_section(work_order):
	if not frappe.has_permission("AI Proposal", "read"):
		return []
	return frappe.get_list(
		"AI Proposal",
		filters={"reference_doctype": "Service Work Order", "reference_name": work_order.name},
		fields=[
			"name",
			"proposal_status",
			"policy_outcome",
			"model_provider",
			"model_name",
			"input_context_hash",
			"output_hash",
			"reviewed_by",
		],
		order_by="name asc",
		limit_page_length=50,
	)


def _finance_section(work_order):
	stock_entries = sorted(
		{row.stock_entry for row in work_order.get("parts") or [] if row.stock_entry}
	)
	return {
		"invoice_ready": work_order.status == "Invoice Ready" or bool(work_order.sales_invoice),
		"sales_invoice": work_order.sales_invoice or "",
		"service_billing_item": work_order.service_billing_item or "",
		"hourly_rate": flt(work_order.hourly_rate),
		"projected_revenue": flt(work_order.projected_revenue),
		"issued_parts_cost": flt(work_order.issued_parts_cost),
		"projected_margin_before_labor": flt(work_order.projected_margin_before_labor),
		"projected_margin_percent": flt(work_order.projected_margin_percent),
		"profitability_basis": work_order.profitability_basis or "",
		"stock_entries": stock_entries,
		"margin_risks": _margin_risk_categories(work_order),
	}


def _margin_risk_categories(work_order):
	"""Return deterministic margin-risk category labels for one work order."""
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
	return [risk.strip() for risk in (row.margin_risks or "").split(",") if risk.strip()]


def _proposal_citation_stubs(proposals):
	"""Count citation rows without loading full proposal draft content."""
	names = [row.get("name") for row in proposals or [] if row.get("name")]
	if not names:
		return []
	rows = frappe.get_all(
		"AI Proposal Source",
		filters={"parent": ("in", names)},
		fields=["parent"],
		limit_page_length=500,
	)
	return [{"proposal": row.parent} for row in rows]


def _ledger_narrative(chain, citations, finance):
	"""Build a finished, publication-safe ledger narrative without draft text."""
	completeness = chain["completeness"]
	sections = chain["sections"]
	identity = sections["work_order"]
	stages = [
		{
			"stage": "request_identity",
			"summary": (
				f"{identity.get('status')} work order {identity.get('name')} "
				f"for customer {identity.get('customer') or 'unspecified'}."
			),
		},
		{
			"stage": "execution",
			"summary": (
				f"{len((sections.get('execution') or {}).get('time_entries') or [])} time "
				f"entries; {len((sections.get('execution') or {}).get('parts') or [])} part rows."
			),
		},
		{
			"stage": "exceptions",
			"summary": f"{len(sections.get('exceptions') or [])} closure exception record(s).",
		},
		{
			"stage": "ai_proposals",
			"summary": (
				f"{len(sections.get('ai_proposals') or [])} draft-only proposal(s); "
				f"{len(citations)} citation row(s)."
			),
		},
	]
	# Finance stage only when the chain already exposed the finance section.
	if "finance" in sections:
		stages.append(
			{
				"stage": "finance_handoff",
				"summary": (
					f"Invoice {finance.get('sales_invoice') or 'not drafted'}; "
					f"margin risks: {', '.join(finance.get('margin_risks') or []) or 'none'}."
				),
			}
		)
	stages.append(
		{
			"stage": "completeness",
			"summary": (
				"complete"
				if completeness.get("complete")
				else f"missing: {', '.join(completeness.get('missing') or []) or 'none'}"
			),
		}
	)
	return {
		"headline": "Request → execution → cited proposals → finance handoff",
		"stages": stages,
		"integrity": {
			"chain_hash": chain["chain_hash"],
			"section_hashes": chain["section_hashes"],
		},
	}


def _completeness_section(work_order):
	missing = []
	if not work_order.get("time_entries"):
		missing.append("time_entries")
	if work_order.status in CLOSEOUT_STATES:
		if not work_order.closeout_notes:
			missing.append("closeout_notes")
		if not work_order.closeout_evidence:
			missing.append("closeout_evidence")
	if any(not row.stock_entry for row in work_order.get("parts") or []):
		missing.append("parts_issue")
	open_exceptions = frappe.db.count(
		"Service Closure Exception", {"work_order": work_order.name, "status": "Open"}
	)
	return {
		"complete": not missing and not open_exceptions,
		"missing": missing,
		"open_exceptions": open_exceptions,
	}


@frappe.whitelist()
def get_evidence_timeline(name):
	"""Return a chronological sequence of evidence events for replay visualization."""
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")

	timeline = [
		{
			"stage": "Created",
			"label": _("Work Order Created"),
			"timestamp": str(work_order.creation),
			"actor": work_order.owner,
			"details": f"Status: {work_order.status}",
		}
	]

	for entry in work_order.get("time_entries") or []:
		timeline.append({
			"stage": "Execution",
			"label": _("Time Recorded"),
			"timestamp": str(getattr(entry, "creation", None) or _timeline_day_timestamp(entry.work_date)),
			"actor": entry.technician,
			"details": f"{entry.hours:g} hrs ({entry.time_type}) on {entry.work_date}",
		})

	if work_order.closeout_notes:
		timeline.append({
			"stage": "Closeout",
			"label": _("Closeout Submitted"),
			"timestamp": str(_closeout_timeline_timestamp(work_order)),
			"actor": work_order.assigned_technician or work_order.owner,
			"details": f"Result: {work_order.inspection_result or 'Submitted'}",
		})

	stock_entries = sorted({row.stock_entry for row in work_order.get("parts") or [] if row.stock_entry})
	for se_name in stock_entries:
		se_date = frappe.db.get_value("Stock Entry", se_name, "creation")
		timeline.append({
			"stage": "Inventory",
			"label": _("Parts Issued"),
			"timestamp": str(se_date or work_order.creation),
			"actor": _("Service Manager"),
			"details": f"Stock Entry: {se_name}",
		})

	if frappe.has_permission("AI Proposal", "read"):
		proposals = frappe.get_all(
			"AI Proposal",
			filters={"reference_doctype": "Service Work Order", "reference_name": work_order.name},
			fields=["name", "proposal_type", "proposal_status", "creation", "reviewed_by"],
		)
		for prop in proposals:
			timeline.append({
				"stage": "AI Proposal",
				"label": _("AI Proposal {0}").format(prop.proposal_type),
				"timestamp": str(prop.creation),
				"actor": prop.reviewed_by or _("AI System"),
				"details": f"Status: {prop.proposal_status}",
			})

	if work_order.sales_invoice and (has_any_role(MANAGER_ROLES) or has_any_role(FINANCE_ROLES)):
		inv_date = frappe.db.get_value("Sales Invoice", work_order.sales_invoice, "creation")
		timeline.append({
			"stage": "Finance",
			"label": _("Draft Sales Invoice"),
			"timestamp": str(inv_date or work_order.creation),
			"actor": _("Accounts User"),
			"details": f"Invoice: {work_order.sales_invoice}",
		})

	timeline.sort(key=_timeline_sort_key)
	return timeline


def _timeline_day_timestamp(work_date):
	"""Normalize date-only work_date values to a sortable datetime string."""
	if not work_date:
		return ""
	value = get_datetime(work_date)
	# Date-only fields sort at start-of-day so they stay before same-day datetimes
	# only when they truly precede them; keep midnight for stable chronology.
	return str(value)


def _closeout_timeline_timestamp(work_order):
	"""Prefer the Version timestamp when status became Closeout Submitted.

	Falling back to modified would move the Closeout event whenever the document
	is saved later, which breaks replay chronology.
	"""
	# Filter on the closeout status string so early edit noise does not push the
	# real Closeout Submitted Version past an unfiltered first-page limit.
	versions = frappe.get_all(
		"Version",
		filters={
			"ref_doctype": "Service Work Order",
			"docname": work_order.name,
			"data": ("like", "%Closeout Submitted%"),
		},
		fields=["creation", "data"],
		order_by="creation asc",
		limit_page_length=100,
	)
	for version in versions:
		if _version_marks_closeout(version.get("data")):
			return version.creation

	# Stable fallbacks: last time entry day, then work-order creation — never modified.
	time_dates = [entry.work_date for entry in (work_order.get("time_entries") or []) if entry.work_date]
	if time_dates:
		return get_datetime(max(time_dates))
	return work_order.creation


def _version_marks_closeout(raw_data):
	if not raw_data:
		return False
	try:
		payload = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
	except (TypeError, ValueError, json.JSONDecodeError):
		return False
	if not isinstance(payload, dict):
		return False
	for change in payload.get("changed") or []:
		if not isinstance(change, (list, tuple)) or len(change) < 3:
			continue
		field, _old, new = change[0], change[1], change[2]
		if field == "status" and new == "Closeout Submitted":
			return True
	return False


def _timeline_sort_key(event):
	timestamp = event.get("timestamp") or ""
	try:
		return (0, get_datetime(timestamp))
	except (TypeError, ValueError):
		return (1, timestamp)
