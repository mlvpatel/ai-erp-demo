frappe.ui.form.on("Service Work Order", {
	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		const is_manager = ["Service Manager", "System Manager"].some((role) =>
			frappe.user_roles.includes(role),
		);
		const is_dispatcher =
			is_manager || frappe.user_roles.includes("Service Dispatcher");
		const is_finance = ["Accounts User", "Accounts Manager"].some((role) =>
			frappe.user_roles.includes(role),
		);
		const has_unissued_parts = (frm.doc.parts || []).some((row) => !row.stock_entry);

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

		if (
			is_manager &&
			["Closeout Submitted", "Closed"].includes(frm.doc.status) &&
			has_unissued_parts
		) {
			frm.add_custom_button(__("Issue Parts"), async () => {
				const response = await frappe.call({
					method:
						"ai_erp_service.ai_erp_service.doctype.service_work_order.service_work_order.issue_parts",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Issuing declared parts..."),
				});
				await frm.reload_doc();
				if (response.message) {
					frappe.show_alert({ message: __("Material Issue submitted."), indicator: "green" });
					frappe.set_route("Form", "Stock Entry", response.message);
				}
			});
		}

		if (is_finance && frm.doc.status === "Invoice Ready" && !frm.doc.sales_invoice) {
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

		frm.add_custom_button(__("Evidence Replay"), async () => {
			const response = await frappe.call({
				method: "ai_erp_service.evidence.get_evidence_chain",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Assembling evidence chain..."),
			});
			show_evidence_replay(response.message);
		});

		if (is_dispatcher && ["Draft", "Scheduled"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Suggest Technicians"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.scheduling.suggest_technicians",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Ranking available technicians..."),
				});
				show_technician_suggestions(frm, response.message);
			});
		}

		if (is_manager && frm.doc.status === "Cannot Close") {
			frm.add_custom_button(__("Draft Recovery Steps"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.recovery.request_recovery_draft",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Drafting cited recovery steps..."),
				});
				frappe.show_alert({ message: __("Recovery draft created for human review."), indicator: "green" });
				frappe.set_route("Form", "AI Proposal", response.message.name);
			});
		}

		if (is_manager) {
			frm.add_custom_button(__("Evidence Packet"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.evidence.get_evidence_packet",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Exporting sanitized evidence packet..."),
				});
				const packet = JSON.stringify(response.message, null, 2);
				const blob = new Blob([packet], { type: "application/json" });
				const url = URL.createObjectURL(blob);
				const anchor = document.createElement("a");
				anchor.href = url;
				anchor.download = `evidence-packet-${frm.doc.name}.json`;
				anchor.click();
				URL.revokeObjectURL(url);
			});
		}
	},
});

function show_technician_suggestions(frm, suggestions) {
	const escape = frappe.utils.escape_html;
	const rows = suggestions.candidates
		.map(
			(candidate) => `
			<tr>
				<td>${escape(candidate.technician)}</td>
				<td>${candidate.score}</td>
				<td>${escape(candidate.reasons.join(", "))}</td>
				<td>
					<button type="button" class="btn btn-xs btn-primary suggestion-assign"
						data-technician="${escape(candidate.technician)}">
						${__("Use Suggestion")}
					</button>
				</td>
			</tr>`,
		)
		.join("");
	const excluded = suggestions.excluded
		.map((row) => `<li>${escape(row.technician)}: ${escape(row.reason)}</li>`)
		.join("");
	const dialog = new frappe.ui.Dialog({ title: __("Technician Suggestions"), size: "large" });
	dialog.$body.html(`
		<table class="table table-bordered">
			<thead><tr><th>${__("Technician")}</th><th>${__("Score")}</th><th>${__("Reasons")}</th><th></th></tr></thead>
			<tbody>${rows || `<tr><td colspan="4">${__("No available technician")}</td></tr>`}</tbody>
		</table>
		${excluded ? `<p>${__("Excluded")}:</p><ul>${excluded}</ul>` : ""}
		<p>${escape(suggestions.assignment_note)}</p>`);
	dialog.$body.find(".suggestion-assign").on("click", (event) => {
		const technician = event.currentTarget.dataset.technician;
		dialog.hide();
		frm.set_value("assigned_technician", technician);
		frappe.show_alert({
			message: __("Suggestion applied. Review and save to assign."),
			indicator: "blue",
		});
	});
	dialog.show();
}

function show_evidence_replay(chain) {
	const escape = frappe.utils.escape_html;
	const sections = chain.sections;
	const completeness = chain.completeness;
	const parts = sections.execution.parts || [];
	const issued = parts.filter((row) => row.stock_entry).length;
	const proposals = sections.ai_proposals || [];
	const latest = proposals.length ? proposals[proposals.length - 1] : null;

	const rows = [
		[__("Evidence complete"), completeness.complete ? __("Yes") : __("No")],
		[
			__("Missing evidence"),
			completeness.missing.length ? escape(completeness.missing.join(", ")) : __("None"),
		],
		[__("Open closure exceptions"), String(completeness.open_exceptions)],
		[__("Parts issued"), `${issued} / ${parts.length}`],
		[
			__("AI proposal status"),
			latest ? escape(`${latest.name}: ${latest.proposal_status}`) : __("None requested"),
		],
	];
	if (sections.finance) {
		rows.push([
			__("Invoice handoff"),
			sections.finance.sales_invoice
				? escape(sections.finance.sales_invoice)
				: sections.finance.invoice_ready
					? __("Invoice Ready")
					: __("Not ready"),
		]);
		rows.push([__("Projected margin percent"), String(sections.finance.projected_margin_percent)]);
	}
	rows.push([__("Chain hash"), escape(chain.chain_hash)]);

	const body = rows
		.map(([label, value]) => `<tr><th scope="row">${label}</th><td>${value}</td></tr>`)
		.join("");
	const dialog = new frappe.ui.Dialog({ title: __("Evidence Replay"), size: "large" });
	dialog.$body.html(`<table class="table table-bordered"><tbody>${body}</tbody></table>`);
	if (sections.finance && sections.finance.sales_invoice) {
		dialog.set_primary_action(__("Open Draft Invoice"), () => {
			dialog.hide();
			frappe.set_route("Form", "Sales Invoice", sections.finance.sales_invoice);
		});
	}
	dialog.show();
}
