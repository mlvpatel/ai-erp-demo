"""Validated, site-scoped calls from Frappe to the stateless AI control plane."""

import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import UTC, datetime

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

CONTROL_PLANE_PATH = "/v1/proposals/service-closeout-summary"
PROPOSAL_TYPE = "service_closeout_summary"
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MAX_CONCURRENT_REQUESTS = 2
MAX_REQUESTS_PER_HOUR = 30
MAX_REQUESTS_PER_DAY = 100
RATE_LIMIT_PREFIX = "ai_erp:proposal_limit"


def canonical_json(value):
	return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def content_hash(value):
	if not isinstance(value, str):
		value = canonical_json(value)
	return hashlib.sha256(value.encode()).hexdigest()


def request_service_closeout_summary(reference_doctype, reference_name, request_payload):
	"""Request one allow-listed draft and persist its auditable proposal record."""
	request_id = request_payload["request_id"]
	if existing := frappe.db.exists("AI Proposal", {"control_plane_request_id": request_id}):
		return frappe.get_doc("AI Proposal", existing)
	input_hash = content_hash(
		{"work_order": request_payload["work_order"], "sources": request_payload["sources"]}
	)
	_lock_reference(reference_doctype, reference_name)
	if existing := frappe.db.get_value(
		"AI Proposal",
		{
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"input_context_hash": input_hash,
		},
		"name",
	):
		return frappe.get_doc("AI Proposal", existing)

	with _proposal_rate_limit():
		response = _post_to_control_plane(request_payload)
	_validate_response(response, request_payload)

	proposal = frappe.get_doc(
		{
			"doctype": "AI Proposal",
			"proposal_type": "Service Closeout Summary",
			"proposal_status": "Draft",
			"policy_outcome": "Draft Only",
			"policy_reason": response["policy"]["reason"],
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"sources": [
				{
					"source_doctype": source["doctype"],
					"source_name": source["name"],
					"source_field": source["field"],
					"content_hash": source["content_hash"],
				}
				for source in response["sources"]
			],
			"draft_content": response["draft_content"],
			"input_context_hash": input_hash,
			"output_hash": content_hash(response["draft_content"]),
			"control_plane_request_id": request_id,
			"requested_by": request_payload["requested_by"],
			"generated_at": now_datetime(),
			"model_provider": response["model"]["provider"],
			"model_name": response["model"]["name"],
			"prompt_version": response["model"]["prompt_version"],
			"provider_response_id_hash": (response.get("audit") or {}).get("response_id_hash"),
			"provider_input_tokens": (response.get("audit") or {}).get("input_tokens"),
			"provider_output_tokens": (response.get("audit") or {}).get("output_tokens"),
			"provider_duration_ms": (response.get("audit") or {}).get("duration_ms"),
			"provider_redaction_count": (response.get("audit") or {}).get("redaction_count"),
		}
	)
	proposal.flags.from_control_plane = True
	proposal.insert(ignore_permissions=True)
	return proposal


def _lock_reference(reference_doctype, reference_name):
	if reference_doctype != "Service Work Order":
		frappe.throw(_("The AI proposal reference is outside the policy allowlist."))
	frappe.db.sql(
		"SELECT `name` FROM `tabService Work Order` WHERE `name` = %s FOR UPDATE",
		reference_name,
	)


@contextmanager
def _proposal_rate_limit():
	"""Use site-scoped Redis counters and fail closed if cache enforcement is unavailable."""
	now = datetime.now(UTC)
	try:
		cache = frappe.cache
		concurrent_key = cache.make_key(f"{RATE_LIMIT_PREFIX}:concurrent")
		hour_key = cache.make_key(f"{RATE_LIMIT_PREFIX}:hour:{now:%Y%m%d%H}")
		day_key = cache.make_key(f"{RATE_LIMIT_PREFIX}:day:{now:%Y%m%d}")
		with cache.pipeline() as pipeline:
			pipeline.incr(concurrent_key)
			pipeline.expire(concurrent_key, 30)
			pipeline.incr(hour_key)
			pipeline.expire(hour_key, 3_700)
			pipeline.incr(day_key)
			pipeline.expire(day_key, 90_000)
			concurrent, _concurrent_expiry, hourly, _hour_expiry, daily, _day_expiry = pipeline.execute()
	except Exception:
		frappe.log_error(title="AI proposal rate-limit cache unavailable")
		frappe.throw(_("AI proposal limits are unavailable. No provider request was made."))

	if concurrent > MAX_CONCURRENT_REQUESTS or hourly > MAX_REQUESTS_PER_HOUR or daily > MAX_REQUESTS_PER_DAY:
		_release_concurrent_slot(concurrent_key)
		frappe.throw(_("AI proposal request limit reached. No provider request was made."))

	try:
		yield
	finally:
		_release_concurrent_slot(concurrent_key)


def _release_concurrent_slot(key):
	try:
		if frappe.cache.decr(key) <= 0:
			frappe.cache.delete(key)
	except Exception:
		frappe.log_error(title="AI proposal concurrency slot release failed")


def _post_to_control_plane(request_payload):
	base_url = os.environ.get("AI_CONTROL_PLANE_URL", "").rstrip("/")
	service_key = os.environ.get("AI_CONTROL_PLANE_SHARED_SECRET", "")
	if not base_url or not service_key:
		frappe.throw(_("AI control plane is not configured for this environment."))

	try:
		response = requests.post(
			f"{base_url}{CONTROL_PLANE_PATH}",
			json=request_payload,
			headers={"Authorization": f"Bearer {service_key}"},
			timeout=12,
		)
		response.raise_for_status()
		return response.json()
	except requests.RequestException:
		frappe.log_error(title="AI control plane request failed")
		frappe.throw(_("The AI control plane is unavailable. No proposal was created."))
	except ValueError:
		frappe.log_error(title="AI control plane returned invalid JSON")
		frappe.throw(_("The AI control plane returned an invalid response. No proposal was created."))


def _validate_response(response, request_payload):
	if not isinstance(response, dict):
		frappe.throw(_("The AI control plane response must be an object."))
	if response.get("schema_version") != 1 or response.get("request_id") != request_payload["request_id"]:
		frappe.throw(_("The AI control plane response does not match its request."))
	if response.get("proposal_type") != PROPOSAL_TYPE:
		frappe.throw(_("The AI control plane returned a proposal outside the policy allowlist."))

	policy = response.get("policy") or {}
	if policy.get("decision") != "draft_only" or policy.get("allowed_action") != "none" or not policy.get("reason"):
		frappe.throw(_("The AI control plane response attempted an unsupported action."))

	model = response.get("model") or {}
	if not all(model.get(field) for field in ("provider", "name", "prompt_version")):
		frappe.throw(_("The AI control plane response is missing model audit metadata."))
	if model.get("provider") == "openai":
		expected_model = os.environ.get("AI_CONTROL_PLANE_EXPECTED_MODEL", "gpt-5.4-mini-2026-03-17")
		if model.get("name") != expected_model:
			frappe.throw(_("The AI control plane returned an unapproved model."))
		audit = response.get("audit")
		if not isinstance(audit, dict) or not HASH_PATTERN.fullmatch(audit.get("response_id_hash") or ""):
			frappe.throw(_("The AI control plane response is missing safe provider audit metadata."))
		for fieldname in ("input_tokens", "output_tokens", "duration_ms", "redaction_count"):
			if not isinstance(audit.get(fieldname), int) or audit[fieldname] < 0:
				frappe.throw(_("The AI control plane response has invalid provider audit metadata."))
	if not isinstance(response.get("draft_content"), str) or not response["draft_content"].strip():
		frappe.throw(_("The AI control plane response is missing a draft."))
	sources = response.get("sources")
	if sources != request_payload["sources"]:
		frappe.throw(_("The AI control plane response returned unverifiable source references."))
	if not isinstance(sources, list) or not sources:
		frappe.throw(_("The AI control plane response must include cited sources."))
	for source in sources:
		if not all(source.get(field) for field in ("doctype", "name", "field", "content_hash")):
			frappe.throw(_("Every AI source reference must identify a record, field, and hash."))
		if not HASH_PATTERN.fullmatch(source["content_hash"]):
			frappe.throw(_("AI source references must use SHA-256 content hashes."))
