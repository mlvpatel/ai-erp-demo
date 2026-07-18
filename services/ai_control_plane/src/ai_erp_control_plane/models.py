"""Strict request/response models for the v1 control-plane contract."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
	model_config = ConfigDict(extra="forbid")


class SourceReference(StrictModel):
	doctype: str = Field(min_length=1, max_length=128)
	name: str = Field(min_length=1, max_length=256)
	field: str = Field(min_length=1, max_length=128)
	content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class TimeEntry(StrictModel):
	technician: str = Field(min_length=1, max_length=256)
	work_date: date
	time_type: str = Field(min_length=1, max_length=128)
	hours: float = Field(gt=0, le=24, allow_inf_nan=False)


class PartUsage(StrictModel):
	item: str = Field(min_length=1, max_length=256)
	qty: float = Field(gt=0, le=100_000, allow_inf_nan=False)
	source_warehouse: str = Field(min_length=1, max_length=256)
	issued: bool


class RelatedWorkSummary(StrictModel):
	name: str = Field(min_length=1, max_length=256)
	subject: str = Field(min_length=1, max_length=256)
	status: str = Field(min_length=1, max_length=128)
	inspection_result: str = Field(default="", max_length=128)
	closeout_notes: str = Field(default="", max_length=4000)


class ServiceWorkOrder(StrictModel):
	doctype: Literal["Service Work Order"]
	name: str = Field(min_length=1, max_length=256)
	subject: str = Field(min_length=1, max_length=256)
	status: str = Field(min_length=1, max_length=128)
	description: str = Field(default="", max_length=4000)
	closeout_notes: str = Field(default="", max_length=4000)
	time_entries: list[TimeEntry] = Field(max_length=100)
	parts: list[PartUsage] = Field(max_length=200)
	related_history: list[RelatedWorkSummary] = Field(default_factory=list, max_length=5)


class ServiceCloseoutSummaryRequest(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	tenant_site: str = Field(min_length=1, max_length=253)
	requested_by: str = Field(min_length=1, max_length=256)
	work_order: ServiceWorkOrder
	sources: list[SourceReference] = Field(min_length=1, max_length=50)


class Policy(StrictModel):
	decision: Literal["draft_only"]
	allowed_action: Literal["none"]
	reason: str = Field(min_length=1)


class ModelMetadata(StrictModel):
	provider: str = Field(min_length=1)
	name: str = Field(min_length=1)
	prompt_version: str = Field(min_length=1)


class ProviderAudit(StrictModel):
	response_id_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
	input_tokens: int = Field(ge=0)
	output_tokens: int = Field(ge=0)
	duration_ms: int = Field(ge=0)
	redaction_count: int = Field(ge=0)


class ProposalResponse(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	proposal_type: Literal["service_closeout_summary"]
	policy: Policy
	model: ModelMetadata
	audit: ProviderAudit | None = None
	draft_content: str = Field(min_length=1, max_length=8000)
	sources: list[SourceReference] = Field(min_length=1)


class OpenAIOutput(StrictModel):
	"""The only model-authored field accepted from the provider."""

	draft_content: str = Field(min_length=1, max_length=8000)


class SchedulingCandidate(StrictModel):
	technician: str = Field(min_length=1, max_length=256)
	score: int
	workload: int = Field(ge=0)
	familiarity: int = Field(ge=0)
	reasons: list[str] = Field(max_length=10)


class SchedulingExclusion(StrictModel):
	technician: str = Field(min_length=1, max_length=256)
	reason: str = Field(min_length=1, max_length=128)


class SchedulingWorkOrderSummary(StrictModel):
	doctype: Literal["Service Work Order"]
	name: str = Field(min_length=1, max_length=256)
	subject: str = Field(min_length=1, max_length=256)
	status: str = Field(min_length=1, max_length=128)
	service_priority: str = Field(default="", max_length=128)
	sla_due_at: str = Field(default="", max_length=64)


class SchedulingExplanationRequest(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	tenant_site: str = Field(min_length=1, max_length=253)
	requested_by: str = Field(min_length=1, max_length=256)
	work_order: SchedulingWorkOrderSummary
	candidates: list[SchedulingCandidate] = Field(max_length=5)
	excluded: list[SchedulingExclusion] = Field(default_factory=list, max_length=50)
	sources: list[SourceReference] = Field(min_length=1, max_length=50)


class SchedulingProposalResponse(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	proposal_type: Literal["scheduling_explanation"]
	policy: Policy
	model: ModelMetadata
	draft_content: str = Field(min_length=1, max_length=8000)
	sources: list[SourceReference] = Field(min_length=1)
