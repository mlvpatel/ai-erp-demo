"""Permission-scoped structured retrieval for AI proposal context."""

import frappe

RELATED_HISTORY_LIMIT = 5
RELATED_HISTORY_FIELDS = ("name", "subject", "status", "inspection_result", "closeout_notes")
COMPLETED_STATUSES = ("Closed", "Invoice Ready")


def related_work_history(work_order, limit=RELATED_HISTORY_LIMIT):
	"""Return completed work orders for the same asset or location visible to the session user.

	Matching is asset-first, then location. Customer alone is never a retrieval
	key, so an unrelated customer at a different site cannot leak into repair
	memory or closeout context.

	frappe.get_list applies the session user's permission query conditions, so a
	technician only retrieves history from work orders assigned to them. An empty
	result is the abstention path: the caller sends no historical context to the
	control plane instead of inventing any. Rows without actionable repair facts
	may still be returned; the control-plane template abstains or omits them.
	"""
	filters = {"name": ("!=", work_order.name), "status": ("in", COMPLETED_STATUSES)}
	if work_order.service_asset:
		filters["service_asset"] = work_order.service_asset
	elif work_order.service_location:
		filters["service_location"] = work_order.service_location
	else:
		return []
	return frappe.get_list(
		"Service Work Order",
		filters=filters,
		fields=list(RELATED_HISTORY_FIELDS),
		order_by="modified desc",
		limit_page_length=limit,
	)
