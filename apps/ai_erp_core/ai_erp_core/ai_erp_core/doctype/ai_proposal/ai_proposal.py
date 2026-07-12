# Copyright (c) 2026, AI ERP Demo and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

IMMUTABLE_FIELDS = {
	"proposal_type",
	"policy_outcome",
	"policy_reason",
	"reference_doctype",
	"reference_name",
	"draft_content",
	"input_context_hash",
	"output_hash",
	"control_plane_request_id",
	"requested_by",
	"generated_at",
	"model_provider",
	"model_name",
	"prompt_version",
}
FINAL_STATUSES = {"Approved", "Rejected"}
HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class AIProposal(Document):
	"""A durable, draft-only AI output with a human review record."""

	def validate(self):
		if self.is_new():
			self._validate_new_proposal()
			return
		self._validate_existing_proposal()

	def _validate_new_proposal(self):
		if not self.flags.from_control_plane:
			frappe.throw(_("AI Proposals can only be created from the validated control-plane boundary."))
		if self.proposal_status != "Draft" or self.policy_outcome != "Draft Only":
			frappe.throw(_("New AI Proposals must be draft-only."))
		if self.proposal_type != "Service Closeout Summary":
			frappe.throw(_("The current policy allowlist permits only Service Closeout Summary."))
		if not self.sources:
			frappe.throw(_("An AI Proposal requires at least one cited source."))
		if not HASH_PATTERN.fullmatch(self.input_context_hash or "") or not HASH_PATTERN.fullmatch(self.output_hash or ""):
			frappe.throw(_("AI Proposal hashes must be SHA-256 values."))
		self._validate_source_rows(self.sources)

	def _validate_existing_proposal(self):
		previous = self.get_doc_before_save()
		if not previous:
			frappe.throw(_("AI Proposal audit state could not be loaded for validation."))

		for fieldname in IMMUTABLE_FIELDS:
			if self.get(fieldname) != previous.get(fieldname):
				frappe.throw(_("{0} is immutable after proposal generation.").format(fieldname))
		if self._source_signature(self.sources) != self._source_signature(previous.sources):
			frappe.throw(_("Cited sources are immutable after proposal generation."))

		previous_status = previous.proposal_status
		if self.proposal_status == previous_status:
			if any(
				self.get(fieldname) != previous.get(fieldname)
				for fieldname in ("reviewed_by", "reviewed_at", "reviewer_note")
			):
				frappe.throw(_("Review fields can change only through a review action."))
			return

		if not self.flags.review_action or previous_status != "Draft" or self.proposal_status not in FINAL_STATUSES:
			frappe.throw(_("AI Proposal status can change only through an authorized review action."))
		self._require_approver()
		if self.reviewed_by != frappe.session.user or not self.reviewed_at:
			frappe.throw(_("A review must record the current reviewer and timestamp."))
		if self.proposal_status == "Rejected" and not self.reviewer_note:
			frappe.throw(_("A rejection reason is required."))

	def _validate_source_rows(self, rows):
		for row in rows:
			if not row.source_doctype or not row.source_name or not row.source_field or not row.content_hash:
				frappe.throw(_("Every AI Proposal source needs a record, field, and content hash."))
			if not HASH_PATTERN.fullmatch(row.content_hash):
				frappe.throw(_("Every AI Proposal source must use a SHA-256 content hash."))

	def _source_signature(self, rows):
		return [
			(row.source_doctype, row.source_name, row.source_field, row.content_hash)
			for row in rows or []
		]

	def _require_approver(self):
		roles = set(frappe.get_roles(frappe.session.user))
		if frappe.session.user == "Administrator" or {"System Manager", "AI Proposal Approver"} & roles:
			return
		frappe.throw(_("Only an AI Proposal Approver can review AI output."), frappe.PermissionError)

	def review(self, outcome, reviewer_note=None):
		self.check_permission("write")
		self._require_approver()
		if self.proposal_status != "Draft":
			frappe.throw(_("Only a draft AI Proposal can be reviewed."))
		if outcome not in FINAL_STATUSES:
			frappe.throw(_("AI Proposal review outcome must be Approved or Rejected."))
		if outcome == "Rejected" and not reviewer_note:
			frappe.throw(_("A rejection reason is required."))

		self.proposal_status = outcome
		self.reviewed_by = frappe.session.user
		self.reviewed_at = now_datetime()
		self.reviewer_note = reviewer_note or ""
		self.flags.review_action = True
		self.save()
		return self


@frappe.whitelist()
def approve(name, reviewer_note=None):
	return frappe.get_doc("AI Proposal", name).review("Approved", reviewer_note).name


@frappe.whitelist()
def reject(name, reviewer_note):
	return frappe.get_doc("AI Proposal", name).review("Rejected", reviewer_note).name
