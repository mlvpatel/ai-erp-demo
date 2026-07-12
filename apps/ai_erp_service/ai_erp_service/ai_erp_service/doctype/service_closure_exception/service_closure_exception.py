# Copyright (c) 2026, AI ERP Demo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ai_erp_service.service_utils import MANAGER_ROLES, has_any_role


class ServiceClosureException(Document):
	def validate(self):
		if self.status == "Resolved" and not self.resolution_note:
			frappe.throw(_("A Resolution Note is required to resolve a closure exception."))
		if self.status == "Resolved" and self.exception_owner != frappe.session.user and not has_any_role(MANAGER_ROLES):
			frappe.throw(_("Only the exception owner or a service manager can resolve this exception."), frappe.PermissionError)
