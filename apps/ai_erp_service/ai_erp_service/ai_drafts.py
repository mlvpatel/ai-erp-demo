"""Service-specific source selection for the governed AI control plane."""

from uuid import uuid4

import frappe
from frappe import _
from frappe.utils import flt

from ai_erp_core.proposals import content_hash, request_service_closeout_summary
from ai_erp_service.service_utils import MANAGER_ROLES, has_any_role


ELIGIBLE_STATUSES = {"Closeout Submitted", "Closed"}


@frappe.whitelist()
def request_closeout_summary(name):
	"""Create one cited, draft-only closeout summary proposal for a work order."""
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")
	if work_order.status not in ELIGIBLE_STATUSES:
		frappe.throw(_("An AI closeout draft is available only after closeout is submitted."))
	if not has_any_role(MANAGER_ROLES) and work_order.assigned_technician != frappe.session.user:
		frappe.throw(_("Only the assigned technician or a service manager can request this draft."), frappe.PermissionError)

	payload = _closeout_summary_payload(work_order)
	proposal = request_service_closeout_summary(work_order.doctype, work_order.name, payload)
	return {"name": proposal.name, "draft_content": proposal.draft_content}


def _closeout_summary_payload(work_order):
	"""Send only allow-listed operational fields, never attachment contents or contacts."""
	time_entries = [
		{
			"technician": row.technician,
			"work_date": str(row.work_date),
			"time_type": row.time_type,
			"hours": flt(row.hours),
		}
		for row in work_order.get("time_entries") or []
	]
	parts = [
		{
			"item": row.item,
			"qty": flt(row.qty),
			"source_warehouse": row.source_warehouse,
			"issued": bool(row.stock_entry),
		}
		for row in work_order.get("parts") or []
	]
	work_order_payload = {
		"doctype": work_order.doctype,
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"description": work_order.description or "",
		"closeout_notes": work_order.closeout_notes or "",
		"time_entries": time_entries,
		"parts": parts,
	}
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": frappe.local.site,
		"requested_by": frappe.session.user,
		"work_order": work_order_payload,
		"sources": _source_references(work_order, work_order_payload),
	}


def _source_references(work_order, work_order_payload):
	"""Return citations for the exact values supplied to the control plane."""
	sources = [
		_source(work_order.doctype, work_order.name, "subject", work_order_payload["subject"]),
		_source(work_order.doctype, work_order.name, "closeout_notes", work_order_payload["closeout_notes"]),
	]
	if work_order_payload["description"]:
		sources.append(_source(work_order.doctype, work_order.name, "description", work_order_payload["description"]))
	for row, payload in zip(work_order.get("time_entries") or [], work_order_payload["time_entries"], strict=True):
		sources.append(_source(row.doctype, row.name, "entry", payload))
	for row, payload in zip(work_order.get("parts") or [], work_order_payload["parts"], strict=True):
		sources.append(_source(row.doctype, row.name, "usage", payload))
	return sources


def _source(doctype, name, field, value):
	return {"doctype": doctype, "name": name, "field": field, "content_hash": content_hash(value)}
