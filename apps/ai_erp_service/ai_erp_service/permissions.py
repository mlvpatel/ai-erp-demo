import frappe

from ai_erp_service.service_utils import (
	DISPATCHER_ROLES,
	FINANCE_ROLES,
	MANAGER_ROLES,
	has_any_role,
	user_roles,
)


def _is_privileged(user):
	return user == "Administrator" or has_any_role(DISPATCHER_ROLES, user)


def service_work_order_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return None
	if has_any_role(FINANCE_ROLES, user):
		return "(`tabService Work Order`.`status` = 'Invoice Ready' OR `tabService Work Order`.`sales_invoice` IS NOT NULL)"
	if "Service Technician" in user_roles(user):
		return "`tabService Work Order`.`assigned_technician` = {0}".format(frappe.db.escape(user))
	return "1=0"


def service_work_order_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return True
	if has_any_role(FINANCE_ROLES, user):
		return permission_type in {None, "read", "select", "print", "email"} and (
			doc.status == "Invoice Ready" or bool(doc.sales_invoice)
		)
	if "Service Technician" in user_roles(user):
		return permission_type in {None, "read", "select", "write", "print"} and doc.assigned_technician == user
	return False


def service_request_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return None
	if "Service Technician" in user_roles(user):
		return (
			"`tabService Request`.`name` IN "
			"(SELECT `service_request` FROM `tabService Work Order` "
			"WHERE `assigned_technician` = {0} AND `service_request` IS NOT NULL)"
		).format(frappe.db.escape(user))
	return "1=0"


def service_request_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return True
	if "Service Technician" not in user_roles(user) or permission_type not in {None, "read", "select", "print"}:
		return False
	return bool(
		frappe.db.exists(
			"Service Work Order",
			{"service_request": doc.name, "assigned_technician": user},
		)
	)


def service_location_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return None
	if "Service Technician" in user_roles(user):
		return (
			"`tabService Location`.`name` IN "
			"(SELECT `service_location` FROM `tabService Work Order` "
			"WHERE `assigned_technician` = {0} AND `service_location` IS NOT NULL)"
		).format(frappe.db.escape(user))
	return "1=0"


def service_location_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return True
	if "Service Technician" not in user_roles(user) or permission_type not in {None, "read", "select", "print"}:
		return False
	return bool(
		frappe.db.exists(
			"Service Work Order",
			{"service_location": doc.name, "assigned_technician": user},
		)
	)


def service_closure_exception_query(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or has_any_role(MANAGER_ROLES, user):
		return None
	if "Service Closure Owner" in user_roles(user):
		return "`tabService Closure Exception`.`exception_owner` = {0}".format(frappe.db.escape(user))
	if "Service Technician" in user_roles(user):
		return (
			"`tabService Closure Exception`.`work_order` IN "
			"(SELECT `name` FROM `tabService Work Order` "
			"WHERE `assigned_technician` = {0})"
		).format(frappe.db.escape(user))
	return "1=0"


def service_closure_exception_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator" or has_any_role(MANAGER_ROLES, user):
		return True
	if "Service Closure Owner" in user_roles(user):
		return doc.exception_owner == user
	if "Service Technician" in user_roles(user):
		return frappe.db.get_value("Service Work Order", doc.work_order, "assigned_technician") == user
	return False


def service_technician_capability_query(user=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return None
	if "Service Technician" in user_roles(user):
		return "`tabService Technician Capability`.`technician` = {0}".format(frappe.db.escape(user))
	return "1=0"


def service_technician_capability_has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if _is_privileged(user):
		return True
	if "Service Technician" in user_roles(user):
		return permission_type in {None, "read", "select", "print"} and doc.technician == user
	return False
