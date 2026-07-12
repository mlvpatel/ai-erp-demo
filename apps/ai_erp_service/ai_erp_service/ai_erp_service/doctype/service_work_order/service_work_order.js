frappe.ui.form.on("Service Work Order", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		if (["Closeout Submitted", "Closed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Draft AI Closeout Summary"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.ai_drafts.request_closeout_summary",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating a cited draft..."),
				});
				frappe.show_alert({ message: __("Draft created for human review."), indicator: "green" });
				frappe.set_route("Form", "AI Proposal", response.message.name);
			});
		}

		if (frm.doc.status === "Invoice Ready" && !frm.doc.sales_invoice) {
			frm.add_custom_button(__("Draft Sales Invoice"), async () => {
				const response = await frappe.call({
					method:
						"ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.make_draft_sales_invoice",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Drafting Sales Invoice..."),
				});
				frappe.show_alert({ message: __("Draft Sales Invoice created."), indicator: "green" });
				frappe.set_route("Form", "Sales Invoice", response.message);
			});
		}

		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("View Sales Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			});
		}
	},
});
