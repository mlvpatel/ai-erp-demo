"""Validated, site-scoped calls from Frappe to the stateless AI control plane."""

import hashlib
import json
import os
import re

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime


CONTROL_PLANE_PATH = "/v1/proposals/service-closeout-summary"
PROPOSAL_TYPE = "service_closeout_summary"
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


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
		}
	)
	proposal.flags.from_control_plane = True
	proposal.insert(ignore_permissions=True)
	return proposal


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
			timeout=10,
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
