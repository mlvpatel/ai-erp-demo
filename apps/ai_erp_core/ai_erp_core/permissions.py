"""Role and record boundaries for the cross-industry AI proposal ledger."""

import frappe


def _roles(user):
	return set(frappe.get_roles(user))


def _is_reviewer(user):
	return user == "Administrator" or bool({"System Manager", "AI Proposal Approver"} & _roles(user))


def ai_proposal_query(user=None):
	user = user or frappe.session.user
	if _is_reviewer(user):
		return None
	if "AI Proposal Requester" in _roles(user):
		return "`tabAI Proposal`.`requested_by` = {0}".format(frappe.db.escape(user))
	return "1=0"


def ai_proposal_has_permission(doc, user=None, ptype=None):
	user = user or frappe.session.user
	if _is_reviewer(user):
		return True
	return ptype == "read" and "AI Proposal Requester" in _roles(user) and doc.requested_by == user
