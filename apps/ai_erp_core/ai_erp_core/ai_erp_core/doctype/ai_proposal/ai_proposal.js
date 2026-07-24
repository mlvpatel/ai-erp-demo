frappe.ui.form.on("AI Proposal", {
	refresh(frm) {
		_show_proposal_governance_banner(frm);

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

function _show_proposal_governance_banner(frm) {
	if (frm.is_new()) {
		return;
	}
	const escape = frappe.utils.escape_html;
	const meta = [
		frm.doc.proposal_type,
		frm.doc.policy_outcome || "Draft Only",
		frm.doc.model_provider,
		frm.doc.prompt_version,
	]
		.filter(Boolean)
		.map(escape)
		.join(" · ");
	frm.set_intro(
		__(
			"Draft-only proposal. Review does not post stock, invoices, payroll, or customer messages. {0}",
			[meta],
		),
		frm.doc.proposal_status === "Draft" ? "blue" : "green",
	);
}
