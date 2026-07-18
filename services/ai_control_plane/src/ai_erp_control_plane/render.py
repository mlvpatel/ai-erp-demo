"""Deterministic renderers for the governed proposal routes."""

from .models import (
	ExceptionRecoveryProposalResponse,
	ExceptionRecoveryRequest,
	ModelMetadata,
	Policy,
	ProposalResponse,
	SchedulingExplanationRequest,
	SchedulingProposalResponse,
	ServiceCloseoutSummaryRequest,
)


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


def render_scheduling_template(request: SchedulingExplanationRequest) -> SchedulingProposalResponse:
	"""Explain supplied deterministic ranking facts without inference or assignment authority."""
	work_order = request.work_order
	lines = [
		f"Draft scheduling explanation — {work_order.subject}",
		"",
		f"Work order: {work_order.name}",
		f"Status: {work_order.status}",
		f"Priority: {work_order.service_priority or 'Not set'}",
		f"SLA due: {work_order.sla_due_at or 'Not set'}",
		"",
		"Ranked candidates (score = 2 x completed work here - open workload)",
	]
	for position, candidate in enumerate(request.candidates, 1):
		lines.append(
			f"{position}. {candidate.technician}: score {candidate.score} "
			f"(open workload {candidate.workload}, completed here {candidate.familiarity})"
		)
	if not request.candidates:
		lines.append("No available candidate passed the availability filter.")
	elif all(candidate.familiarity == 0 for candidate in request.candidates):
		lines.extend(
			[
				"",
				"Evidence note",
				"No candidate has completed prior work at this asset or location; the ranking rests on open workload alone.",
			]
		)
	if request.excluded:
		lines.extend(["", "Excluded"])
		for exclusion in request.excluded:
			lines.append(f"- {exclusion.technician}: {exclusion.reason}")
	lines.extend(
		[
			"",
			"Review required",
			"This explanation is a draft only. It cannot assign a technician; the dispatcher assigns through the saved form.",
		]
	)
	return SchedulingProposalResponse(
		schema_version=1,
		request_id=request.request_id,
		proposal_type="scheduling_explanation",
		policy=Policy(decision="draft_only", allowed_action="none", reason=POLICY_REASON),
		model=ModelMetadata(
			provider="development-template",
			name="deterministic-scheduling-v1",
			prompt_version="scheduling-explanation@v1",
		),
		draft_content="\n".join(lines),
		sources=request.sources,
	)


RECOVERY_GUIDANCE = {
	"Customer unavailable": (
		"Confirm the next customer contact window with the service manager.",
		"Reschedule the visit inside the SLA window before releasing the technician slot.",
	),
	"Parts unavailable": (
		"Check declared part availability across permitted warehouses.",
		"Raise the purchase or transfer request through the deterministic stock workflow.",
	),
	"Further diagnosis needed": (
		"Schedule a diagnostic visit with the inspection findings attached.",
		"Record the suspected cause on the work order before the next visit.",
	),
	"Approval required": (
		"Route the pending approval to its owner with the closure due date.",
		"Hold execution until the approval decision is recorded.",
	),
	"Safety issue": (
		"Keep the work order open and escalate the safety condition to the manager immediately.",
		"Document the hazard and required mitigation before any further site visit.",
	),
}


def render_recovery_template(request: ExceptionRecoveryRequest) -> ExceptionRecoveryProposalResponse:
	"""Draft deterministic recovery steps or an explicit abstention. Never closes work."""
	work_order = request.work_order
	exception = request.exception
	lines = [
		f"Draft recovery steps — {work_order.subject}",
		"",
		f"Work order: {work_order.name} ({work_order.status})",
		f"Closure exception: {exception.name} ({exception.status})",
		f"Reason: {exception.reason}",
	]
	if exception.due_date:
		lines.append(f"Closure due: {exception.due_date}")
	if work_order.inspection_result:
		lines.append(f"Inspection result: {work_order.inspection_result}")

	guidance = RECOVERY_GUIDANCE.get(exception.reason)
	unissued = [part for part in request.parts if not part.issued]
	if guidance:
		lines.extend(["", "Recommended next steps"])
		lines.extend(f"- {step}" for step in guidance)
	elif not request.related_history:
		lines.extend(
			[
				"",
				"Abstention",
				"The exception reason is uncategorized and no prior related work is visible, "
				"so no recovery recommendation is made. The manager should record the next "
				"step manually.",
			]
		)
	if unissued:
		lines.extend(["", "Declared parts not yet issued"])
		lines.extend(f"- {part.item}: {part.qty:g}" for part in unissued)
	if request.related_history:
		lines.extend(["", "Prior related work (cited)"])
		for entry in request.related_history:
			lines.append(f"- {entry.name}: {entry.subject} ({entry.status})")
			if entry.closeout_notes:
				lines.append(f"  Closeout notes: {entry.closeout_notes}")
	lines.extend(
		[
			"",
			"Review required",
			"This is a draft only. It cannot close the work order or resolve the exception; "
			"the manager owns the recovery action and closure.",
		]
	)
	return ExceptionRecoveryProposalResponse(
		schema_version=1,
		request_id=request.request_id,
		proposal_type="exception_recovery",
		policy=Policy(decision="draft_only", allowed_action="none", reason=POLICY_REASON),
		model=ModelMetadata(
			provider="development-template",
			name="deterministic-recovery-v1",
			prompt_version="exception-recovery@v1",
		),
		draft_content="\n".join(lines),
		sources=request.sources,
	)
