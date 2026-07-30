"""Cited repair-memory drafts from permission-scoped prior work.

Payload builders send only role-visible history facts. The control-plane
template provider cites those rows, abstains when evidence is missing or weak,
and never posts ERP state.
"""

from uuid import uuid4

import frappe
from ai_erp_core.proposals import request_repair_memory as store_repair_memory
from frappe import _
from frappe.utils import flt

from ai_erp_service.ai_drafts import _source
from ai_erp_service.retrieval import related_work_history
from ai_erp_service.service_utils import MANAGER_ROLES, has_any_role

ELIGIBLE_STATUSES = {"Scheduled", "In Progress"}


@frappe.whitelist()
def request_repair_memory_draft(name):
	"""Create one cited, draft-only repair-memory proposal for active work."""
	work_order = frappe.get_doc("Service Work Order", name)
	work_order.check_permission("read")
	if work_order.status not in ELIGIBLE_STATUSES:
		frappe.throw(_("Repair memory is available only for scheduled or in-progress work."))
	if not has_any_role(MANAGER_ROLES) and work_order.assigned_technician != frappe.session.user:
		frappe.throw(
			_("Only the assigned technician or a service manager can request repair memory."),
			frappe.PermissionError,
		)

	payload = _repair_memory_payload(work_order)
	proposal = store_repair_memory(work_order.doctype, work_order.name, payload)
	return {"name": proposal.name, "draft_content": proposal.draft_content}


def _repair_memory_payload(work_order):
	"""Send only role-visible history facts; customer and location data stay out."""
	work_order_summary = {
		"doctype": work_order.doctype,
		"name": work_order.name,
		"subject": work_order.subject,
		"status": work_order.status,
		"description": work_order.description or "",
	}
	related_history = []
	for row in related_work_history(work_order):
		parts = [
			{"item": part.item, "qty": flt(part.qty), "issued": bool(part.stock_entry)}
			for part in frappe.get_all(
				"Service Work Order Part",
				filters={"parent": row.name, "parenttype": "Service Work Order"},
				fields=["item", "qty", "stock_entry"],
				limit_page_length=200,
			)
		]
		related_history.append(
			{
				"name": row.name,
				"subject": row.subject,
				"status": row.status,
				"inspection_result": row.inspection_result or "",
				"closeout_notes": row.closeout_notes or "",
				"parts": parts,
			}
		)
	sources = [
		_source(
			work_order.doctype,
			work_order.name,
			"repair_context",
			{"subject": work_order_summary["subject"], "description": work_order_summary["description"]},
		)
	]
	for entry in related_history:
		sources.append(_source(work_order.doctype, entry["name"], "history", entry))
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": frappe.local.site,
		"requested_by": frappe.session.user,
		"work_order": work_order_summary,
		"related_history": related_history,
		"sources": sources,
	}
