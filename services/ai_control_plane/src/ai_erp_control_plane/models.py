"""Strict request/response models for the v1 control-plane contract."""

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
	technician: str = Field(max_length=256)
	work_date: str = Field(max_length=10)
	time_type: str = Field(max_length=128)
	hours: float = Field(gt=0)


class PartUsage(StrictModel):
	item: str = Field(max_length=256)
	qty: float = Field(gt=0)
	source_warehouse: str = Field(max_length=256)
	issued: bool


class ServiceWorkOrder(StrictModel):
	doctype: Literal["Service Work Order"]
	name: str = Field(min_length=1, max_length=256)
	subject: str = Field(min_length=1, max_length=256)
	status: str = Field(min_length=1, max_length=128)
	description: str = Field(default="", max_length=4000)
	closeout_notes: str = Field(default="", max_length=4000)
	time_entries: list[TimeEntry] = Field(max_length=100)
	parts: list[PartUsage] = Field(max_length=200)


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


class ProposalResponse(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	proposal_type: Literal["service_closeout_summary"]
	policy: Policy
	model: ModelMetadata
	draft_content: str = Field(min_length=1, max_length=8000)
	sources: list[SourceReference] = Field(min_length=1)
