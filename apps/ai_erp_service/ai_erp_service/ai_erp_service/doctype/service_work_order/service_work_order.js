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

		if (is_manager || is_finance) {
			frm.add_custom_button(__("Evidence Packet"), () => {
				export_evidence_packet(frm);
			});
		}

		if (is_manager || is_finance) {
			frm.add_custom_button(__("Margin Leakage Summary"), () => {
				show_margin_leakage_summary();
			});
		}
	},
});

const MARGIN_RISK_LABELS = {
	missing_billable_time: "Missing billable time",
	zero_rate_labor: "Discount / zero-rate labor",
	missing_part_bill_rate: "Missing part bill rate",
	part_cost_above_bill_rate: "Part cost above bill rate",
	unknown_cost_basis: "Unknown cost basis",
	warranty_risk: "Warranty risk",
	failed_inspection: "Failed inspection",
	unresolved_exception: "Unresolved exception",
	repeat_visit_risk: "Repeat visit risk",
};

const MARGIN_STATUS_OPTIONS = [
	"",
	"Draft",
	"Scheduled",
	"In Progress",
	"Closeout Submitted",
	"Cannot Close",
	"Closed",
	"Invoice Ready",
	"Cancelled",
];

let margin_leakage_request = null;
let margin_leakage_dialog = null;

function margin_risk_label(category) {
	return __(MARGIN_RISK_LABELS[category] || category);
}

function margin_risk_option_label(category) {
	// Keep Select options in source English so Frappe translates once at render.
	return MARGIN_RISK_LABELS[category] || category;
}

function resolve_margin_risk_category(label, categories) {
	if (!label) {
		return "";
	}
	return (
		categories.find((category) => {
			const raw = margin_risk_option_label(category);
			return raw === label || __(raw) === label;
		}) || ""
	);
}

function format_margin_risk_evidence(detail) {
	const evidence = (detail && detail.evidence) || {};
	const category = (detail && detail.category) || "";
	if (category === "repeat_visit_risk") {
		const neighbors = evidence.neighbor_work_orders || [];
		return neighbors.length
			? __("Neighbors: {0}", [neighbors.slice(0, 3).join(", ")])
			: __("Repeat visit window match");
	}
	if (category === "unknown_cost_basis") {
		const items = (evidence.items || []).map((row) => row.item).filter(Boolean);
		return items.length
			? __("Items without cost: {0}", [items.slice(0, 3).join(", ")])
			: __("Missing stock unit cost");
	}
	if (category === "missing_billable_time") {
		return __("Closeout status {0} with no billable hours", [evidence.status || ""]);
	}
	if (category === "zero_rate_labor") {
		return __("{0}h at hourly rate {1}", [
			String(evidence.billable_hours ?? 0),
			String(evidence.hourly_rate ?? 0),
		]);
	}
	if (category === "unresolved_exception") {
		const exceptions = evidence.exceptions || [];
		return exceptions.length
			? __("Open exceptions: {0}", [exceptions.slice(0, 3).join(", ")])
			: __("Open closure exception");
	}
	if (category === "part_cost_above_bill_rate") {
		const items = (evidence.items || []).map((row) => row.item).filter(Boolean);
		return items.length
			? __("Cost above bill: {0}", [items.slice(0, 3).join(", ")])
			: __("Part cost above bill rate");
	}
	if (category === "missing_part_bill_rate") {
		const items = evidence.items || [];
		return items.length
			? __("Missing bill rate: {0}", [items.slice(0, 3).join(", ")])
			: __("Missing part bill rate");
	}
	if (category === "warranty_risk") {
		return __("Warranty status: {0}", [evidence.warranty_status || ""]);
	}
	if (category === "failed_inspection") {
		return __("Inspection: {0}", [evidence.inspection_result || ""]);
	}
	return evidence.source || "";
}

function show_margin_leakage_summary(filters) {
	if (margin_leakage_request) {
		return;
	}
	const next = filters || {};
	margin_leakage_request = frappe.call({
		method: "ai_erp_service.margin_risk.margin_leakage_summary",
		args: {
			risk_category: next.risk_category || "",
			status: next.status || "",
			from_date: next.from_date || "",
			to_date: next.to_date || "",
		},
		freeze: true,
		freeze_message: __("Loading margin leakage summary..."),
		callback(response) {
			margin_leakage_request = null;
			if (!response.message) {
				frappe.show_alert({
					message: __("Margin leakage summary returned no data."),
					indicator: "orange",
				});
				return;
			}
			render_margin_leakage_summary(response.message, next);
		},
		error() {
			margin_leakage_request = null;
		},
	});
}

function render_margin_leakage_summary(summary, selected) {
	const escape = frappe.utils.escape_html;
	const selected_filters = selected || {};
	const selected_category = selected_filters.risk_category || summary.risk_category || "";
	const selected_status = selected_filters.status || summary.status || "";
	const selected_from = selected_filters.from_date || summary.from_date || "";
	const selected_to = selected_filters.to_date || summary.to_date || "";
	const counts = summary.category_counts || {};
	const categories = summary.available_categories || Object.keys(MARGIN_RISK_LABELS);
	const count_rows = categories
		.map((category) => {
			const count = counts[category] || 0;
			return `<tr>
				<th scope="row">${escape(margin_risk_label(category))}</th>
				<td>${escape(String(count))}</td>
			</tr>`;
		})
		.join("");
	const order_rows = (summary.high_risk_orders || [])
		.map((row) => {
			const detail_lines = (row.risk_details || [])
				.map(
					(detail) =>
						`<div><strong>${escape(margin_risk_label(detail.category))}</strong>: ${escape(
							format_margin_risk_evidence(detail),
						)}</div>`,
				)
				.join("");
			return `<tr>
				<td>
					<a href="/app/service-work-order/${encodeURIComponent(row.name || "")}">
						${escape(row.name || "")}
					</a>
				</td>
				<td>${escape(row.customer || "")}</td>
				<td>${escape(row.status || "")}</td>
				<td>${escape(String(row.margin_percent ?? ""))}</td>
				<td>${
					detail_lines ||
					escape((row.risks || []).map(margin_risk_label).join(", "))
				}</td>
			</tr>`;
		})
		.join("");
	const truncation = summary.truncated
		? `<div class="alert alert-warning" role="status">
			${escape(
				__(
					"Showing the first {0} work orders. Narrow the filter or date range; counts may understate the full queue.",
					[summary.page_limit || 500],
				),
			)}
		</div>`
		: "";
	const high_risk_truncation = summary.high_risk_truncated
		? `<div class="alert alert-warning" role="status">
			${escape(
				__(
					"Showing the {0} highest-risk work orders in this scan. Narrow the category filter to see more.",
					[summary.high_risk_limit || 50],
				),
			)}
		</div>`
		: "";
	const filter_bits = [];
	if (selected_category) {
		filter_bits.push(
			`<strong>${__("Category")}:</strong> ${escape(margin_risk_label(selected_category))}`,
		);
	}
	if (selected_status) {
		filter_bits.push(`<strong>${__("Status")}:</strong> ${escape(__(selected_status))}`);
	}
	if (selected_from || selected_to) {
		filter_bits.push(
			`<strong>${__("Dates")}:</strong> ${escape(selected_from || "…")} → ${escape(
				selected_to || "…",
			)}`,
		);
	}
	const region_label = escape(__("Margin Leakage Summary"));
	const html = `
		<div class="margin-leakage-summary" role="region" aria-label="${region_label}">
			<p>
				<strong>${__("Orders scanned")}:</strong> ${escape(String(summary.total_orders || 0))}
				${filter_bits.length ? ` · ${filter_bits.join(" · ")}` : ""}
			</p>
			${truncation}
			${high_risk_truncation}
			<h5>${__("Category counts")}</h5>
			<table class="table table-bordered table-condensed">
				<tbody>${count_rows}</tbody>
			</table>
			<h5>${__("High-risk work orders")}</h5>
			<table class="table table-bordered table-condensed">
				<thead>
					<tr>
						<th>${__("Work Order")}</th>
						<th>${__("Customer")}</th>
						<th>${__("Status")}</th>
						<th>${__("Margin %")}</th>
						<th>${__("Risks and evidence")}</th>
					</tr>
				</thead>
				<tbody>
					${
						order_rows ||
						`<tr><td colspan="5" class="text-muted">${__("No high-risk work orders in this filter.")}</td></tr>`
					}
				</tbody>
			</table>
			<p class="text-muted">
				${__("Deterministic categories only. This view does not change billing records.")}
			</p>
		</div>
	`;

	const category_options = categories.map(margin_risk_option_label).join("\n");
	if (margin_leakage_dialog) {
		margin_leakage_dialog.hide();
		margin_leakage_dialog = null;
	}
	const dialog = new frappe.ui.Dialog({
		title: __("Margin Leakage Summary"),
		size: "extra-large",
		fields: [
			{
				fieldtype: "Select",
				fieldname: "risk_category",
				label: __("Risk category filter"),
				options: `\n${category_options}`,
				default: selected_category ? margin_risk_option_label(selected_category) : "",
			},
			{
				fieldtype: "Select",
				fieldname: "status",
				label: __("Status filter"),
				options: MARGIN_STATUS_OPTIONS.join("\n"),
				default: selected_status,
			},
			{
				fieldtype: "Date",
				fieldname: "from_date",
				label: __("From date"),
				default: selected_from,
			},
			{
				fieldtype: "Date",
				fieldname: "to_date",
				label: __("To date"),
				default: selected_to,
			},
			{ fieldtype: "HTML", fieldname: "summary_html" },
		],
		primary_action_label: __("Apply Filter"),
		primary_action(values) {
			const label = (values && values.risk_category) || "";
			const next_category = resolve_margin_risk_category(label, categories);
			dialog.hide();
			margin_leakage_dialog = null;
			show_margin_leakage_summary({
				risk_category: next_category,
				status: (values && values.status) || "",
				from_date: (values && values.from_date) || "",
				to_date: (values && values.to_date) || "",
			});
		},
	});
	margin_leakage_dialog = dialog;
	dialog.fields_dict.summary_html.$wrapper.html(html);
	dialog.show();
}

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
	const feedback = suggestions.feedback_summary || {};
	const category_counts = feedback.category_counts || {};
	const feedback_rows = Object.keys(category_counts)
		.filter((category) => category_counts[category] > 0)
		.map(
			(category) =>
				`<li>${escape(category)}: ${category_counts[category]}</li>`,
		)
		.join("");
	const feedback_html = feedback.total
		? `<div class="scheduling-feedback-summary" role="region" aria-label="${__(
				"Rejection feedback",
			)}">
			<p><strong>${__("Recorded rejection feedback")}:</strong> ${feedback.total}</p>
			<ul>${feedback_rows}</ul>
			<p class="text-muted">
				${__("Feedback informs future ranking review; it does not auto-assign.")}
			</p>
		</div>`
		: `<p class="text-muted scheduling-feedback-summary">
			${__("No rejection feedback recorded on this work order yet.")}
		</p>`;
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
		${feedback_html}
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
	const margin_details = (finance && finance.margin_risk_details) || [];

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

	const margin_detail_html = margin_details
		.map(
			(detail) => `<li>
				<strong>${escape(margin_risk_label(detail.category))}</strong>
				<span>${escape(format_margin_risk_evidence(detail))}</span>
			</li>`,
		)
		.join("");
	const margin_html =
		finance && margin_risks.length
			? `<div class="alert alert-warning margin-risk-panel" role="status">
				<strong>${__("Margin leakage categories")}:</strong>
				${
					margin_detail_html
						? `<ul class="margin-risk-evidence-list">${margin_detail_html}</ul>`
						: escape(margin_risks.join(", "))
				}
			</div>`
			: "";

	const narrative = chain.ledger_narrative || {};
	const narrative_incomplete = Boolean(narrative.incomplete) || !completeness.complete;
	const narrative_stages = (narrative.stages || [])
		.map(
			(stage) => `
		<li class="ledger-narrative-stage${
			stage.stage === "completeness" && narrative_incomplete ? " is-incomplete" : ""
		}" tabindex="0">
			<strong>${escape(stage.stage)}</strong>
			<span>${escape(stage.summary)}</span>
		</li>`,
		)
		.join("");
	const default_headline = narrative_incomplete
		? __("Incomplete evidence chain")
		: __("Request → execution → cited proposals → finance handoff");
	const narrative_html = narrative_stages
		? `<div class="ledger-narrative${
				narrative_incomplete ? " ledger-narrative-incomplete" : ""
			}" role="region" aria-label="${__("Ledger narrative")}">
			<h5>${__("Ledger narrative")}</h5>
			<p class="ledger-narrative-headline">${escape(narrative.headline || default_headline)}</p>
			<ol class="ledger-narrative-stages">${narrative_stages}</ol>
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
			${narrative_html}
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
