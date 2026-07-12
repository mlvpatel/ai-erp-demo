"""Strict request/response models for the v1 control-plane contract."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
	model_config = ConfigDict(extra="forbid")


class SourceReference(StrictModel):
	doctype: str = Field(min_length=1)
	name: str = Field(min_length=1)
	field: str = Field(min_length=1)
	content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class TimeEntry(StrictModel):
	technician: str
	work_date: str
	time_type: str
	hours: float = Field(gt=0)


class PartUsage(StrictModel):
	item: str
	qty: float = Field(gt=0)
	source_warehouse: str
	issued: bool


class ServiceWorkOrder(StrictModel):
	doctype: Literal["Service Work Order"]
	name: str = Field(min_length=1)
	subject: str = Field(min_length=1)
	status: str = Field(min_length=1)
	description: str = ""
	closeout_notes: str = ""
	time_entries: list[TimeEntry]
	parts: list[PartUsage]


class ServiceCloseoutSummaryRequest(StrictModel):
	schema_version: Literal[1]
	request_id: UUID
	tenant_site: str = Field(min_length=1)
	requested_by: str = Field(min_length=1)
	work_order: ServiceWorkOrder
	sources: list[SourceReference] = Field(min_length=1)


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
	draft_content: str = Field(min_length=1)
	sources: list[SourceReference] = Field(min_length=1)
