import frappe
from frappe import _

MANAGER_ROLES = frozenset({"System Manager", "Service Manager"})
DISPATCHER_ROLES = MANAGER_ROLES | {"Service Dispatcher"}
FINANCE_ROLES = frozenset({"Accounts User", "Accounts Manager"})


def user_roles(user=None):
	return set(frappe.get_roles(user or frappe.session.user))


def has_any_role(roles, user=None):
	return bool(user_roles(user) & set(roles))


def require_any_role(roles, message):
	if not has_any_role(roles):
		frappe.throw(_(message), frappe.PermissionError)


def validate_location_customer(customer, service_location):
	if not service_location:
		return

	location_customer = frappe.db.get_value("Service Location", service_location, "customer")
	if location_customer and location_customer != customer:
		frappe.throw(
			_("Service Location {0} belongs to Customer {1}, not {2}.").format(
				service_location, location_customer, customer
			)
		)
