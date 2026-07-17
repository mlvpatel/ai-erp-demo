"""Development-only deterministic renderer for the governed demo path."""

from .models import ModelMetadata, Policy, ProposalResponse, ServiceCloseoutSummaryRequest


POLICY_REASON = "This response is a cited draft only; a human review records no ERP action."


def render_development_template(request: ServiceCloseoutSummaryRequest) -> ProposalResponse:
	"""Format supplied data without inference, tools, retrieval, or ERP access."""
	work_order = request.work_order
	lines = [
		f"Draft closeout summary — {work_order.subject}",
		"",
		f"Work order: {work_order.name}",
		f"Current status: {work_order.status}",
	]
	if work_order.description:
		lines.extend(["", "Reported scope", work_order.description])
	if work_order.closeout_notes:
		lines.extend(["", "Technician closeout notes", work_order.closeout_notes])

	total_hours = sum(entry.hours for entry in work_order.time_entries)
	lines.extend(["", "Recorded effort", f"- Total hours: {total_hours:g}"])
	for entry in work_order.time_entries:
		lines.append(f"- {entry.work_date}: {entry.hours:g} {entry.time_type} ({entry.technician})")

	if work_order.parts:
		lines.extend(["", "Parts declared"])
		for part in work_order.parts:
			issue_state = "issued" if part.issued else "not issued"
			lines.append(f"- {part.item}: {part.qty:g} from {part.source_warehouse} ({issue_state})")

	if work_order.related_history:
		lines.extend(["", "Prior related work (cited)"])
		for entry in work_order.related_history:
			lines.append(f"- {entry.name}: {entry.subject} ({entry.status})")
			if entry.inspection_result:
				lines.append(f"  Inspection result: {entry.inspection_result}")
			if entry.closeout_notes:
				lines.append(f"  Closeout notes: {entry.closeout_notes}")

	lines.extend(
		[
			"",
			"Review required",
			"This is a draft only. Approval does not update the work order or perform an ERP transaction.",
		]
	)
	return ProposalResponse(
		schema_version=1,
		request_id=request.request_id,
		proposal_type="service_closeout_summary",
		policy=Policy(decision="draft_only", allowed_action="none", reason=POLICY_REASON),
		model=ModelMetadata(
			provider="development-template",
			name="deterministic-closeout-v1",
			prompt_version="service-closeout-summary@v1",
		),
		draft_content="\n".join(lines),
		sources=request.sources,
	)
