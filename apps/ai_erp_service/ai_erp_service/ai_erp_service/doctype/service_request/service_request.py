# Copyright (c) 2026, AI ERP Demo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from ai_erp_service.service_utils import DISPATCHER_ROLES, require_any_role, validate_location_customer


class ServiceRequest(Document):
	def validate(self):
		validate_location_customer(self.customer, self.service_location)
		if self.service_work_order and self.status != "Triaged":
			frappe.throw(_("A request linked to a work order must be Triaged."))


@frappe.whitelist()
def create_service_work_order(name):
	request = frappe.get_doc("Service Request", name)
	request.check_permission("write")
	require_any_role(DISPATCHER_ROLES, "Only a dispatcher or service manager can create a work order.")

	if request.service_work_order:
		return request.service_work_order

	work_order = frappe.get_doc(
		{
			"doctype": "Service Work Order",
			"subject": request.subject,
			"customer": request.customer,
			"service_location": request.service_location,
			"service_request": request.name,
			"description": request.description,
			"status": "Draft",
		}
	)
	work_order.insert()

	request.service_work_order = work_order.name
	request.status = "Triaged"
	request.save()
	return work_order.name
