// Copyright (c) 2026, AI ERP Demo and contributors
// For license information, please see license.txt

frappe.ui.form.on("Service Technician Capability", {
	refresh(frm) {
		frm.set_intro(
			__(
				"Skills and territories feed deterministic scheduling suggestions only. Dispatchers still assign technicians manually."
			)
		);
	},
});
