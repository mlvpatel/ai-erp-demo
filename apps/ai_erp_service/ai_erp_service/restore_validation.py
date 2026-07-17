"""Payload-free integrity checks executed only inside a disposable recovery stack."""

import hashlib
import re

import frappe

REQUIRED_APPS = {"erpnext", "ai_erp_core", "ai_erp_service"}
REQUIRED_ROLES = {
	"Service Technician",
	"Service Dispatcher",
	"Service Manager",
	"Accounts User",
	"Accounts Manager",
	"AI Proposal Approver",
}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_restore():
	installed = set(frappe.get_installed_apps())
	if not REQUIRED_APPS.issubset(installed):
		frappe.throw("Restore validation failed: required applications are missing")
	missing_roles = [role for role in REQUIRED_ROLES if not frappe.db.exists("Role", role)]
	if missing_roles:
		frappe.throw("Restore validation failed: required roles are missing")

	dangling_invoices = frappe.db.sql(
		"""
		select count(*)
		from `tabService Work Order` work_order
		left join `tabSales Invoice` invoice on invoice.name = work_order.sales_invoice
		where work_order.sales_invoice is not null and work_order.sales_invoice != ''
		  and invoice.name is null
		"""
	)[0][0]
	dangling_stock = frappe.db.sql(
		"""
		select count(*)
		from `tabService Work Order Part` part
		left join `tabStock Entry` stock_entry on stock_entry.name = part.stock_entry
		where part.stock_entry is not null and part.stock_entry != ''
		  and stock_entry.name is null
		"""
	)[0][0]
	if dangling_invoices or dangling_stock:
		frappe.throw("Restore validation failed: transaction links are inconsistent")

	invalid_ai_audits = 0
	for proposal in frappe.get_all(
		"AI Proposal",
		fields=["name", "reference_doctype", "reference_name", "draft_content", "input_context_hash", "output_hash", "provider_response_id_hash", "model_provider"],
	):
		if proposal.reference_doctype != "Service Work Order" or not frappe.db.exists(
			"Service Work Order", proposal.reference_name
		):
			invalid_ai_audits += 1
			continue
		if not HASH_PATTERN.fullmatch(proposal.input_context_hash or "") or not HASH_PATTERN.fullmatch(
			proposal.output_hash or ""
		):
			invalid_ai_audits += 1
			continue
		if hashlib.sha256((proposal.draft_content or "").encode()).hexdigest() != proposal.output_hash:
			invalid_ai_audits += 1
		if proposal.model_provider == "openai" and not HASH_PATTERN.fullmatch(
			proposal.provider_response_id_hash or ""
		):
			invalid_ai_audits += 1
	if invalid_ai_audits:
		frappe.throw("Restore validation failed: AI audit hashes or references are inconsistent")

	private_files = frappe.get_all(
		"File",
		filters={"is_private": 1, "attached_to_doctype": ["is", "set"]},
		pluck="name",
		limit_page_length=100,
	)
	original_user = frappe.session.user
	try:
		frappe.set_user("Guest")
		if any(frappe.get_doc("File", name).has_permission("read") for name in private_files):
			frappe.throw("Restore validation failed: private file authorization is inconsistent")
	finally:
		frappe.set_user(original_user)

	from ai_erp_core.permissions import ai_proposal_query

	from ai_erp_service.permissions import service_work_order_query

	proposal_requester = frappe.db.get_value("Has Role", {"role": "AI Proposal Requester", "parenttype": "User"}, "parent")
	technician = frappe.db.get_value("Has Role", {"role": "Service Technician", "parenttype": "User"}, "parent")
	if not proposal_requester or "requested_by" not in (ai_proposal_query(proposal_requester) or ""):
		frappe.throw("Restore validation failed: AI tenant scope hook is inconsistent")
	if not technician or "assigned_technician" not in (service_work_order_query(technician) or ""):
		frappe.throw("Restore validation failed: work-order tenant scope hook is inconsistent")

	return {
		"status": "PASS",
		"required_apps": len(REQUIRED_APPS),
		"required_roles": len(REQUIRED_ROLES),
		"dangling_invoice_links": 0,
		"dangling_stock_links": 0,
		"invalid_ai_audits": 0,
		"private_files_checked": len(private_files),
		"tenant_scope_hooks_checked": 2,
	}
