frappe.ui.form.on("AI Proposal", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.proposal_status !== "Draft" || !frm.perm[0].write) {
			return;
		}

		frm.add_custom_button(__("Approve Draft"), async () => {
			await frappe.call({
				method: "ai_erp_core.ai_erp_core.doctype.ai_proposal.ai_proposal.approve",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Recording approval…"),
			});
			frm.reload_doc();
		});

		frm.add_custom_button(__("Reject Draft"), () => {
			frappe.prompt(
				[{ fieldname: "reviewer_note", fieldtype: "Small Text", label: __("Reason"), reqd: 1 }],
				async (values) => {
					await frappe.call({
						method: "ai_erp_core.ai_erp_core.doctype.ai_proposal.ai_proposal.reject",
						args: { name: frm.doc.name, reviewer_note: values.reviewer_note },
						freeze: true,
						freeze_message: __("Recording rejection…"),
					});
					frm.reload_doc();
				},
				__("Reject AI Draft"),
				__("Reject")
			);
		});
	},
});
