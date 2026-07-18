"""Manager-owned recovery drafts for Cannot Close work orders."""

from uuid import uuid4

import frappe
from ai_erp_core.proposals import request_exception_recovery as store_exception_recovery
from frappe import _

from ai_erp_service.ai_drafts import _source
from ai_erp_service.retrieval import related_work_history
from ai_erp_service.service_utils import MANAGER_ROLES, require_any_role


@frappe.whitelist()
def request_recovery_draft(name):
	"""Create one cited, draft-only recovery proposal for an open closure exception."""
	require_any_role(MANAGER_ROLES, _("Only a service manager can request a recovery draft."))
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")
	exceptions = frappe.get_list(
		"Service Closure Exception",
		filters={"work_order": work_order.name, "status": "Open"},
		fields=["name", "reason", "status", "due_date"],
		order_by="name asc",
		limit_page_length=1,
	)
	if not exceptions:
		frappe.throw(_("An open closure exception is required before requesting a recovery draft."))

	payload = _recovery_payload(work_order, exceptions[0])
	proposal = store_exception_recovery(work_order.doctype, work_order.name, payload)
	return {"name": proposal.name, "draft_content": proposal.draft_content}


def _recovery_payload(work_order, exception):
	"""Send only recovery facts; customer, location, and contact data stay out."""
	work_order_summary = {
		"doctype": work_order.doctype,
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"cannot_close_reason": work_order.cannot_close_reason or "",
		"inspection_result": work_order.inspection_result or "",
	}
	exception_summary = {
		"name": exception.name,
		"reason": exception.reason,
		"status": exception.status,
		"due_date": str(exception.due_date or ""),
	}
	parts = [
		{"item": row.item, "qty": row.qty, "issued": bool(row.stock_entry)}
		for row in work_order.get("parts") or []
	]
	related_history = [
		{
			"name": row.name,
			"subject": row.subject,
			"status": row.status,
			"inspection_result": row.inspection_result or "",
			"closeout_notes": row.closeout_notes or "",
		}
		for row in related_work_history(work_order)
	]
	sources = [
		_source("Service Closure Exception", exception_summary["name"], "reason", exception_summary),
		_source(
			work_order.doctype,
			work_order.name,
			"cannot_close",
			{
				"cannot_close_reason": work_order_summary["cannot_close_reason"],
				"inspection_result": work_order_summary["inspection_result"],
				"parts": parts,
			},
		),
	]
	for entry in related_history:
		sources.append(_source(work_order.doctype, entry["name"], "history", entry))
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": frappe.local.site,
		"requested_by": frappe.session.user,
		"work_order": work_order_summary,
		"exception": exception_summary,
		"parts": parts,
		"related_history": related_history,
		"sources": sources,
	}
