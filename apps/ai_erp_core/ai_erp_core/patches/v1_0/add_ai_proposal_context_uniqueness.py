"""Add the durable idempotency constraint for proposal context."""

import frappe
from frappe import _

CONSTRAINT_NAME = "unique_ai_proposal_reference_context"
FIELDS = ("reference_doctype", "reference_name", "input_context_hash")


def execute():
	duplicates = frappe.db.sql(
		"""
		SELECT `reference_doctype`, `reference_name`, `input_context_hash`, COUNT(*) AS `row_count`
		FROM `tabAI Proposal`
		GROUP BY `reference_doctype`, `reference_name`, `input_context_hash`
		HAVING COUNT(*) > 1
		LIMIT 1
		""",
		as_dict=True,
	)
	if duplicates:
		frappe.throw(
			_("AI Proposal context duplicates must be resolved before adding the idempotency constraint.")
		)
	frappe.db.add_unique("AI Proposal", FIELDS, constraint_name=CONSTRAINT_NAME)
