import hashlib
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from ai_erp_control_plane.models import ServiceCloseoutSummaryRequest
from ai_erp_control_plane.openai_provider import DEFAULT_MODEL, OpenAIProviderError, render_openai


def _request():
	return ServiceCloseoutSummaryRequest.model_validate(
		{
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "private-tenant.example",
			"requested_by": "private-user@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "PRIVATE-WO-0001",
				"subject": "Inspect pump",
				"status": "Closeout Submitted",
				"description": "Investigate noise.",
				"closeout_notes": "Tightened the mount.",
				"time_entries": [
					{
						"technician": "private-tech@example.test",
						"work_date": "2026-07-10",
						"time_type": "Work",
						"hours": 1.5,
					}
				],
				"parts": [{"item": "MOUNT-1", "qty": 1, "source_warehouse": "PRIVATE-WH", "issued": True}],
			},
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "PRIVATE-WO-0001",
					"field": "closeout_notes",
					"content_hash": hashlib.sha256(b"Tightened the mount.").hexdigest(),
				}
			],
		}
	)


def _environment(**overrides):
	values = {
		"OPENAI_API_KEY": "example",
		"OPENAI_MODEL": DEFAULT_MODEL,
		"OPENAI_BASE_URL": "https://eu.api.openai.com/v1",
		"OPENAI_TIMEOUT_SECONDS": "5",
	}
	values.update(overrides)
	return values


class TestOpenAIProvider(unittest.TestCase):
	def test_minimizes_input_and_constructs_policy_and_sources_locally(self):
		request = _request()
		captured = {}

		def handler(http_request):
			captured["request"] = http_request
			return httpx.Response(
				200,
				json={
					"status": "completed",
					"output": [
						{
							"type": "message",
							"content": [
								{"type": "output_text", "text": json.dumps({"draft_content": "Pump mount tightened."})}
							],
						}
					],
				},
			)

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai(request, client=client)
		client.close()

		outbound = json.loads(captured["request"].content)
		model_input = json.loads(outbound["input"])
		self.assertEqual(captured["request"].url, "https://eu.api.openai.com/v1/responses")
		self.assertEqual(captured["request"].headers["authorization"], "Bearer example")
		self.assertFalse(outbound["store"])
		self.assertNotIn("tools", outbound)
		self.assertTrue(outbound["text"]["format"]["strict"])
		self.assertNotIn("tenant_site", model_input)
		self.assertNotIn("requested_by", model_input)
		self.assertNotIn("name", model_input)
		self.assertNotIn("technician", model_input["time_entries"][0])
		self.assertNotIn("source_warehouse", model_input["parts"][0])
		self.assertEqual(response.policy.decision, "draft_only")
		self.assertEqual(response.policy.allowed_action, "none")
		self.assertEqual(response.sources, request.sources)
		self.assertEqual(response.model.provider, "openai")
		self.assertEqual(response.model.name, DEFAULT_MODEL)

	def test_missing_key_and_unapproved_origin_fail_closed_before_network(self):
		with patch.dict(os.environ, _environment(OPENAI_API_KEY=""), clear=True):
			with self.assertRaises(OpenAIProviderError):
				render_openai(_request())
		with patch.dict(os.environ, _environment(OPENAI_BASE_URL="https://example.invalid/v1"), clear=True):
			with self.assertRaises(OpenAIProviderError):
				render_openai(_request())

	def test_refusal_malformed_and_provider_error_fail_closed(self):
		responses = [
			httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]}),
			httpx.Response(200, json={"status": "completed", "output_text": "not-json"}),
			httpx.Response(429, json={"error": {"message": "rate limit"}}),
		]
		for provider_response in responses:
			with self.subTest(status=provider_response.status_code, body=provider_response.text):
				client = httpx.Client(transport=httpx.MockTransport(lambda _request: provider_response))
				with patch.dict(os.environ, _environment(), clear=True):
					with self.assertRaises(OpenAIProviderError):
						render_openai(_request(), client=client)
				client.close()
