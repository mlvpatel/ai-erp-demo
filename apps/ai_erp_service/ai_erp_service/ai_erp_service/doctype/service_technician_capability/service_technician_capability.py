# Copyright (c) 2026, AI ERP Demo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def normalize_capability_labels(raw_value):
	"""Split comma/newline labels into a stable lowercase set."""
	if not raw_value:
		return set()
	labels = []
	for chunk in str(raw_value).replace("\n", ",").split(","):
		label = chunk.strip().lower()
		if label:
			labels.append(label)
	return set(labels)


class ServiceTechnicianCapability(Document):
	def validate(self):
		if not self.technician:
			frappe.throw(_("Technician is required."))
		skills = normalize_capability_labels(self.skills)
		territories = normalize_capability_labels(self.territories)
		if not skills:
			frappe.throw(_("At least one skill label is required."))
		if not territories:
			frappe.throw(_("At least one territory label is required."))
		# Store a canonical sorted CSV so matching and demos stay deterministic.
		self.skills = ", ".join(sorted(skills))
		self.territories = ", ".join(sorted(territories))
		if self.van_warehouse:
			if not frappe.db.exists("Warehouse", self.van_warehouse):
				frappe.throw(_("Van Warehouse must be an existing Warehouse."))
			if frappe.db.get_value("Warehouse", self.van_warehouse, "is_group"):
				frappe.throw(_("Van Warehouse cannot be a group warehouse."))
