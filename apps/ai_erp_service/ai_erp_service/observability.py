"""Payload-free security signals for production log metric filters."""

import frappe


def record_permission_failure():
	response = getattr(frappe.local, "response", {}) or {}
	if response.get("http_status_code") == 403:
		print("erp_permission_denied", flush=True)
