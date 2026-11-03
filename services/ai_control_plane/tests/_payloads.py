"""Synthetic request builders shared by the control-plane tests."""

import hashlib
from datetime import date, timedelta
from uuid import uuid4


def sha(value):
	return hashlib.sha256(value.encode()).hexdigest()


def offset_date(days):
	"""Keep fixture dates relative so they never drift into the past."""
	return (date.today() + timedelta(days=days)).isoformat()


def source(name, field="history", value="history", doctype="Service Work Order"):
	return {"doctype": doctype, "name": name, "field": field, "content_hash": sha(value)}


def envelope(requested_by="technician@example.test", **body):
	"""Versioned request envelope; body supplies the route fields and may override tenant_site."""
	return {
		"schema_version": 1,
		"request_id": str(uuid4()),
		"tenant_site": "demo.localhost",
		"requested_by": requested_by,
		**body,
	}
