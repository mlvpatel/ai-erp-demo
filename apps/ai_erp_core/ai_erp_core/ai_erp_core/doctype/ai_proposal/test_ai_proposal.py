# Copyright (c) 2026, AI ERP Demo and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime


IGNORE_TEST_RECORD_DEPENDENCIES = ["AI Proposal", "AI Proposal Source", "User"]


class IntegrationTestAIProposalPermissions(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.owner = self._make_requester("owner")
		self.other_requester = self._make_requester("other")

	def test_requester_cannot_read_another_requesters_proposal(self):
		owner_proposal = self._make_proposal(self.owner)
		other_proposal = self._make_proposal(self.other_requester)

		frappe.set_user(self.other_requester)
		roles = set(frappe.get_roles(self.other_requester))
		self.assertIn("AI Proposal Requester", roles)
		self.assertTrue({"System Manager", "AI Proposal Approver"}.isdisjoint(roles))
		visible = set(
			frappe.get_list(
				"AI Proposal",
				filters={"name": ["in", [owner_proposal.name, other_proposal.name]]},
				pluck="name",
			)
		)
		self.assertEqual(visible, {other_proposal.name})
		self.assertFalse(owner_proposal.has_permission("read"))
		with self.assertRaises(frappe.PermissionError):
			owner_proposal.check_permission("read")
		self.assertTrue(other_proposal.has_permission("read"))

	def _make_requester(self, label):
		email = "ai.proposal.{0}.{1}@example.test".format(label, frappe.generate_hash(length=8))
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "AI Proposal {0}".format(label.title()),
				"enabled": 1,
				"send_welcome_email": 0,
				"user_type": "System User",
				"roles": [{"role": "AI Proposal Requester"}],
			}
		).insert()
		frappe.clear_cache(user=user.name)
		return user.name

	def _make_proposal(self, requested_by):
		proposal = frappe.get_doc(
			{
				"doctype": "AI Proposal",
				"proposal_type": "Service Closeout Summary",
				"proposal_status": "Draft",
				"policy_outcome": "Draft Only",
				"policy_reason": "Draft only; human review has no ERP side effect.",
				"reference_doctype": "User",
				"reference_name": requested_by,
				"sources": [
					{
						"source_doctype": "User",
						"source_name": requested_by,
						"source_field": "first_name",
						"content_hash": "0" * 64,
					}
				],
				"draft_content": "Synthetic draft for permission testing.",
				"input_context_hash": "1" * 64,
				"output_hash": "2" * 64,
				"control_plane_request_id": frappe.generate_hash(length=32),
				"requested_by": requested_by,
				"generated_at": now_datetime(),
				"model_provider": "test-template",
				"model_name": "permission-test",
				"prompt_version": "permission-test@v1",
			}
		)
		proposal.flags.from_control_plane = True
		return proposal.insert(ignore_permissions=True)
