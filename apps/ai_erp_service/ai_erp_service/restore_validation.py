"""Payload-free integrity checks executed only inside a disposable restore site."""

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

	return {
		"status": "PASS",
		"required_apps": len(REQUIRED_APPS),
		"required_roles": len(REQUIRED_ROLES),
		"dangling_invoice_links": 0,
		"dangling_stock_links": 0,
	}
