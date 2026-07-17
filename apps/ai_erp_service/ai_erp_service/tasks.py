"""Scheduled, human-owned field-service escalations."""

import json
from datetime import UTC, datetime

import frappe
from frappe import _
from frappe.utils import now_datetime, today


def escalate_overdue_closure_exceptions():
	"""Notify managers once when an open Cannot Close exception becomes overdue."""
	exceptions = frappe.get_all(
		"Service Closure Exception",
		filters={"status": "Open", "due_date": ["<", today()], "escalated_on": ["is", "not set"]},
		fields=["name", "work_order", "exception_owner", "due_date"],
	)
	for exception in exceptions:
		recipients = _manager_users() | {exception.exception_owner}
		for user in recipients - {None, "", "Guest"}:
			frappe.get_doc(
				{
					"doctype": "Notification Log",
					"subject": _("Overdue Cannot Close exception {0}").format(exception.name),
					"for_user": user,
					"type": "Alert",
					"document_type": "Service Closure Exception",
					"document_name": exception.name,
					"from_user": "Administrator",
				}
			).insert(ignore_permissions=True)
		frappe.db.set_value(
			"Service Closure Exception",
			exception.name,
			"escalated_on",
			now_datetime(),
			update_modified=False,
		)


def _manager_users():
	return {
		row.parent
		for row in frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Service Manager", "System Manager"]], "parenttype": "User"},
			fields=["parent"],
		)
	}


def publish_queue_age_metric():
	"""Emit one payload-free queue-age signal for CloudWatch log metric extraction."""
	from frappe.utils.background_jobs import get_queue, get_queue_list

	now = datetime.now(UTC)
	oldest_seconds = 0
	for queue_name in get_queue_list():
		for job in get_queue(queue_name).jobs:
			if job.kwargs.get("site") != frappe.local.site or not job.enqueued_at:
				continue
			enqueued_at = job.enqueued_at.replace(tzinfo=job.enqueued_at.tzinfo or UTC)
			oldest_seconds = max(oldest_seconds, int((now - enqueued_at).total_seconds()))
	print(
		json.dumps(
			{"event": "queue_oldest_age", "age_seconds": max(0, oldest_seconds)},
			separators=(",", ":"),
		),
		flush=True,
	)
