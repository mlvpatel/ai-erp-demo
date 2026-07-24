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

		if (["Scheduled", "In Progress"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Draft Repair Memory"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.repair_memory.request_repair_memory_draft",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Collecting cited prior work..."),
				});
				frappe.show_alert({
					message: __("Repair memory draft created for human review."),
					indicator: "green",
				});
				frappe.set_route("Form", "AI Proposal", response.message.name);
			});
		}

		if (["Closeout Submitted", "Closed"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Draft AI Closeout Summary"), async () => {
				const response = await frappe.call({
					method: "ai_erp_service.ai_drafts.request_closeout_summary",
					args: { name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating a cited draft..."),
				});
				frappe.show_alert({
					message: __("Draft created for human review."),
					indicator: "green",
				});
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
					frappe.show_alert({
						message: __("Material Issue submitted."),
						indicator: "green",
					});
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
				frappe.show_alert({
					message: __("Draft Sales Invoice created."),
					indicator: "green",
				});
				frappe.set_route("Form", "Sales Invoice", response.message);
			});
		}

		if (frm.doc.sales_invoice) {
			frm.add_custom_button(__("View Sales Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
			});
		}

		frm.add_custom_button(__("Evidence Replay"), () => {
			show_evidence_replay_dialog(frm);
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
				frappe.show_alert({
					message: __("Recovery draft created for human review."),
					indicator: "green",
				});
				frappe.set_route("Form", "AI Proposal", response.message.name);
			});
		}

		if (is_manager) {
			frm.add_custom_button(__("Evidence Packet"), () => {
				export_evidence_packet(frm);
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
					<button type="button" class="btn btn-xs btn-default suggestion-reject"
						data-technician="${escape(candidate.technician)}">
						${__("Reject")}
					</button>
				</td>
			</tr>`,
		)
		.join("");
	const excluded = suggestions.excluded
		.map((row) => `<li>${escape(row.technician)}: ${escape(row.reason)}</li>`)
		.join("");
	const dialog = new frappe.ui.Dialog({
		title: __("Technician Suggestions"),
		size: "large",
		primary_action_label: __("Explain Schedule"),
		primary_action: async () => {
			const response = await frappe.call({
				method: "ai_erp_service.scheduling.request_scheduling_explanation",
				args: { name: frm.doc.name },
				freeze: true,
				freeze_message: __("Drafting cited schedule explanation..."),
			});
			dialog.hide();
			frappe.show_alert({
				message: __("Scheduling explanation draft created for human review."),
				indicator: "green",
			});
			frappe.set_route("Form", "AI Proposal", response.message.name);
		},
	});
	dialog.$body.html(`
		<table class="table table-bordered">
			<thead>
				<tr>
					<th>${__("Technician")}</th>
					<th>${__("Score")}</th>
					<th>${__("Reasons")}</th>
					<th></th>
				</tr>
			</thead>
			<tbody>${rows || `<tr><td colspan="4">${__("No available technician")}</td></tr>`}</tbody>
		</table>
		${excluded ? `<p>${__("Excluded")}:</p><ul>${excluded}</ul>` : ""}
		<p>${escape(suggestions.assignment_note)}</p>
		<p class="text-muted">
			${__("Explain Schedule creates a draft-only cited proposal; it cannot assign a technician.")}
		</p>`);
	dialog.$body.find(".suggestion-assign").on("click", (event) => {
		const technician = event.currentTarget.dataset.technician;
		dialog.hide();
		frm.set_value("assigned_technician", technician);
		frappe.show_alert({
			message: __("Suggestion applied. Review and save to assign."),
			indicator: "blue",
		});
	});
	dialog.$body.find(".suggestion-reject").on("click", (event) => {
		const technician = event.currentTarget.dataset.technician;
		capture_suggestion_rejection(frm, technician, dialog);
	});
	dialog.show();
}

function capture_suggestion_rejection(frm, technician, parent_dialog) {
	const feedback = new frappe.ui.Dialog({
		title: __("Reject Suggestion"),
		fields: [
			{
				fieldname: "reason_category",
				fieldtype: "Select",
				label: __("Reason"),
				reqd: 1,
				options: [
					"Wrong skill or territory",
					"Parts not ready",
					"Workload conflict",
					"Customer preference",
					"Other",
				].join("\n"),
			},
			{
				fieldname: "note",
				fieldtype: "Small Text",
				label: __("Note"),
			},
		],
		primary_action_label: __("Record Rejection"),
		primary_action: async (values) => {
			await frappe.call({
				method: "ai_erp_service.scheduling.record_suggestion_feedback",
				args: {
					name: frm.doc.name,
					technician: technician,
					reason_category: values.reason_category,
					note: values.note || "",
				},
				freeze: true,
				freeze_message: __("Recording dispatcher feedback..."),
			});
			feedback.hide();
			frappe.show_alert({
				message: __("Rejection reason recorded for ranking feedback."),
				indicator: "blue",
			});
			parent_dialog.$body
				.find(`.suggestion-reject[data-technician="${frappe.utils.escape_html(technician)}"]`)
				.prop("disabled", true)
				.text(__("Rejected"));
		},
	});
	feedback.show();
}

function show_evidence_replay_dialog(frm) {
	frappe.call({
		method: "ai_erp_service.evidence.get_evidence_chain",
		args: { name: frm.doc.name },
		freeze: true,
		freeze_message: __("Assembling evidence chain..."),
		callback(chain_response) {
			if (!chain_response.message) {
				return;
			}
			const chain = chain_response.message;
			frappe.call({
				method: "ai_erp_service.evidence.get_evidence_timeline",
				args: { name: frm.doc.name },
				callback(timeline_response) {
					render_evidence_replay(chain, timeline_response.message || []);
				},
			});
		},
	});
}

function render_evidence_replay(chain, timeline) {
	const escape = frappe.utils.escape_html;
	const sections = chain.sections || {};
	const completeness = chain.completeness || {};
	const status_class = completeness.complete ? "status-complete" : "status-incomplete";
	const status_text = completeness.complete ? __("Complete") : __("Incomplete");
	const parts = (sections.execution && sections.execution.parts) || [];
	const issued = parts.filter((row) => row.stock_entry).length;
	const proposals = sections.ai_proposals || [];
	const latest = proposals.length ? proposals[proposals.length - 1] : null;
	const finance = sections.finance || null;
	const margin_risks = (finance && finance.margin_risks) || [];

	const summary_rows = [
		[__("Evidence complete"), completeness.complete ? __("Yes") : __("No")],
		[
			__("Missing evidence"),
			completeness.missing && completeness.missing.length
				? escape(completeness.missing.join(", "))
				: __("None"),
		],
		[__("Open closure exceptions"), String(completeness.open_exceptions || 0)],
		[__("Parts issued"), `${issued} / ${parts.length}`],
		[
			__("AI proposal status"),
			latest
				? escape(`${latest.name}: ${latest.proposal_status}`)
				: __("None requested"),
		],
	];
	if (finance) {
		summary_rows.push([
			__("Invoice handoff"),
			finance.sales_invoice
				? escape(finance.sales_invoice)
				: finance.invoice_ready
					? __("Invoice Ready")
					: __("Not ready"),
		]);
		summary_rows.push([
			__("Projected margin percent"),
			String(finance.projected_margin_percent),
		]);
		summary_rows.push([
			__("Margin risks"),
			margin_risks.length ? escape(margin_risks.join(", ")) : __("None flagged"),
		]);
	}
	summary_rows.push([__("Chain hash"), escape(chain.chain_hash)]);

	const summary_html = summary_rows
		.map(([label, value]) => `<tr><th scope="row">${label}</th><td>${value}</td></tr>`)
		.join("");

	const timeline_html = timeline
		.map(
			(event) => `
		<div class="timeline-event stage-${frappe.scrub(event.stage)}" tabindex="0">
			<div class="timeline-title">${escape(event.label)}</div>
			<div class="timeline-meta">${escape(event.actor)} • ${escape(String(event.timestamp))}</div>
			<div class="timeline-details">${escape(event.details)}</div>
		</div>`,
		)
		.join("");

	const margin_html =
		finance && margin_risks.length
			? `<div class="alert alert-warning margin-risk-panel" role="status">
				<strong>${__("Margin leakage categories")}:</strong>
				${escape(margin_risks.join(", "))}
			</div>`
			: "";

	const html = `
		<div class="evidence-replay-container" role="region" aria-label="${__("Evidence Replay")}">
			<div class="evidence-header">
				<div>
					<strong>${__("Work Order")}:</strong> ${escape(chain.work_order)}<br>
					<small class="text-muted">${__("Chain Hash")}: ${escape(
						(chain.chain_hash || "").substring(0, 16),
					)}…</small>
				</div>
				<span class="evidence-status-badge ${status_class}">${status_text}</span>
			</div>
			${
				completeness.missing && completeness.missing.length
					? `<div class="alert alert-warning" role="status">
						<strong>${__("Missing Evidence")}:</strong>
						${escape(completeness.missing.join(", "))}
					</div>`
					: ""
			}
			${margin_html}
			<h5>${__("Ledger Summary")}</h5>
			<table class="table table-bordered"><tbody>${summary_html}</tbody></table>
			<h5>${__("Chronological Evidence Timeline")}</h5>
			<div class="evidence-timeline">
				${timeline_html || `<p class="text-muted">${__("No timeline events recorded.")}</p>`}
			</div>
			<p class="text-muted evidence-disclaimer">
				${__("Synthetic demo evidence. Not human acceptance or production audit proof.")}
			</p>
		</div>
	`;

	const dialog = new frappe.ui.Dialog({
		title: __("Evidence-to-Cash Ledger Replay"),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "replay_html" }],
	});
	dialog.fields_dict.replay_html.$wrapper.html(html);
	if (finance && finance.sales_invoice) {
		dialog.set_primary_action(__("Open Draft Invoice"), () => {
			dialog.hide();
			frappe.set_route("Form", "Sales Invoice", finance.sales_invoice);
		});
	}
	dialog.show();
}

function export_evidence_packet(frm) {
	frappe.call({
		method: "ai_erp_service.evidence.get_evidence_packet",
		args: { name: frm.doc.name },
		freeze: true,
		freeze_message: __("Exporting sanitized evidence packet..."),
		callback(response) {
			if (!response.message) {
				return;
			}
			const packet = response.message;
			const blob = new Blob([JSON.stringify(packet, null, 2)], {
				type: "application/json",
			});
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement("a");
			anchor.href = url;
			anchor.download = `evidence-packet-${frm.doc.name}.json`;
			anchor.click();
			URL.revokeObjectURL(url);
			frappe.show_alert({
				message: __("Evidence packet exported (synthetic ledger narrative)."),
				indicator: "green",
			});
		},
	});
}
