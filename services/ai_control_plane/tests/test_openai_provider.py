import hashlib
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx

from ai_erp_control_plane.models import RelatedWorkSummary, RepairMemoryRequest, ServiceCloseoutSummaryRequest
from ai_erp_control_plane.openai_provider import (
	DEFAULT_MODEL,
	MAX_AUTOMATIC_RETRIES,
	MAX_INPUT_BYTES,
	MAX_OUTPUT_TOKENS,
	MAX_PROVIDER_CALLS,
	MAX_TIMEOUT_SECONDS,
	OpenAIProviderError,
	render_openai,
	render_openai_repair_memory,
)


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


def _provider_payload(draft="Pump mount tightened.", **overrides):
	payload = {
		"id": "resp_synthetic_001",
		"model": DEFAULT_MODEL,
		"status": "completed",
		"usage": {"input_tokens": 120, "output_tokens": 20},
		"output_text": json.dumps({"draft_content": draft}),
	}
	payload.update(overrides)
	return payload


class TestOpenAIProvider(unittest.TestCase):
	def test_minimizes_input_and_constructs_policy_and_sources_locally(self):
		request = _request()
		captured = {}

		def handler(http_request):
			captured["request"] = http_request
			return httpx.Response(200, json=_provider_payload())

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai(request, client=client)
		client.close()

		outbound = json.loads(captured["request"].content)
		model_input = json.loads(outbound["input"])
		self.assertEqual(captured["request"].url, "https://eu.api.openai.com/v1/responses")
		self.assertEqual(captured["request"].headers["authorization"], "Bearer example")
		self.assertEqual(
			set(outbound),
			{"model", "store", "max_output_tokens", "reasoning", "instructions", "input", "text"},
		)
		self.assertEqual(outbound["model"], DEFAULT_MODEL)
		self.assertFalse(outbound["store"])
		self.assertNotIn("tools", outbound)
		self.assertTrue(outbound["text"]["format"]["strict"])
		self.assertEqual(outbound["max_output_tokens"], MAX_OUTPUT_TOKENS)
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
		self.assertEqual(response.audit.input_tokens, 120)
		self.assertEqual(response.audit.output_tokens, 20)
		self.assertEqual(response.audit.redaction_count, 0)
		self.assertEqual(len(response.audit.response_id_hash), 64)
		serialized_body = captured["request"].content.decode()
		for private_value in (
			"private-tenant.example",
			"private-user@example.test",
			"PRIVATE-WO-0001",
			"private-tech@example.test",
			"PRIVATE-WH",
			request.sources[0].content_hash,
		):
			self.assertNotIn(private_value, serialized_body)

	def test_missing_key_and_unapproved_origin_fail_closed_before_network(self):
		with patch.dict(os.environ, _environment(OPENAI_API_KEY=""), clear=True):
			with self.assertRaises(OpenAIProviderError):
				render_openai(_request())
		with patch.dict(os.environ, _environment(OPENAI_BASE_URL="https://example.invalid/v1"), clear=True):
			with self.assertRaises(OpenAIProviderError):
				render_openai(_request())
		with patch.dict(os.environ, _environment(OPENAI_BASE_URL="https://api.openai.com/v1"), clear=True):
			with self.assertRaises(OpenAIProviderError):
				render_openai(_request())

	def test_refusal_malformed_strict_schema_and_rate_limit_fail_closed_without_retry(self):
		responses = [
			httpx.Response(200, json=_provider_payload(output_text="", output=[{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}])),
			httpx.Response(200, json=_provider_payload(output_text="not-json")),
			httpx.Response(
				200,
				json=_provider_payload(
					output_text=json.dumps({"draft_content": "Draft", "requested_action": "submit invoice"})
				),
			),
			httpx.Response(429, json={"error": {"message": "rate limit"}}),
		]
		for provider_response in responses:
			with self.subTest(status=provider_response.status_code, body=provider_response.text):
				calls = []

				def handler(request):
					calls.append(request)
					return provider_response

				client = httpx.Client(transport=httpx.MockTransport(handler))
				with patch.dict(os.environ, _environment(), clear=True):
					with self.assertRaises(OpenAIProviderError):
						render_openai(_request(), client=client)
				client.close()
				self.assertEqual(len(calls), MAX_PROVIDER_CALLS)

	def test_timeout_fails_closed_without_retry_or_provider_detail(self):
		calls = []

		def handler(request):
			calls.append(request)
			raise httpx.ReadTimeout("private provider detail", request=request)

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			with self.assertRaisesRegex(OpenAIProviderError, "provider request failed") as raised:
				render_openai(_request(), client=client)
		client.close()
		self.assertNotIn("private provider detail", str(raised.exception))
		self.assertEqual(len(calls), MAX_PROVIDER_CALLS)

	def test_enforces_token_retry_latency_and_spend_envelope(self):
		self.assertEqual(MAX_AUTOMATIC_RETRIES, 0)
		self.assertEqual(MAX_PROVIDER_CALLS, 1)
		self.assertLessEqual(MAX_OUTPUT_TOKENS, 2_000)
		self.assertLessEqual(MAX_INPUT_BYTES, 32_000)
		with patch.dict(os.environ, _environment(OPENAI_TIMEOUT_SECONDS=str(MAX_TIMEOUT_SECONDS + 1)), clear=True):
			with self.assertRaisesRegex(OpenAIProviderError, "outside the approved range"):
				render_openai(_request())

	def test_rejects_input_above_spend_envelope_before_network(self):
		request = _request()
		request.work_order.description = "x" * 4000
		request.work_order.closeout_notes = "y" * 4000
		request.work_order.parts[0].item = "z" * 256
		request.work_order.parts = request.work_order.parts * 200
		calls = []
		client = httpx.Client(transport=httpx.MockTransport(lambda request: calls.append(request)))
		with patch.dict(os.environ, _environment(), clear=True):
			with self.assertRaisesRegex(OpenAIProviderError, "spend envelope"):
				render_openai(request, client=client)
		client.close()
		self.assertEqual(calls, [])

	def test_redacts_high_confidence_pii_and_credentials_and_records_only_count(self):
		request = _request()
		request.work_order.description = "Email alice@example.test or call +1 (415) 555-0100."
		request.work_order.closeout_notes = "credential=synthetic-value-1234"
		captured = {}

		def handler(http_request):
			captured["body"] = http_request.content.decode()
			return httpx.Response(200, json=_provider_payload())

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai(request, client=client)
		client.close()

		for sensitive in ("alice@example.test", "+1 (415) 555-0100", "synthetic-value-1234"):
			self.assertNotIn(sensitive, captured["body"])
		self.assertGreaterEqual(response.audit.redaction_count, 3)

	def test_related_history_is_minimized_and_redacted_before_provider_call(self):
		request = _request()
		request.work_order.related_history = [
			RelatedWorkSummary(
				name="PRIVATE-WO-HIST-1",
				subject="Prior pump repair",
				status="Closed",
				inspection_result="Passed",
				closeout_notes="Replaced the seal; owner is alice@example.test.",
			)
		]
		captured = {}

		def handler(http_request):
			captured["body"] = http_request.content.decode()
			return httpx.Response(200, json=_provider_payload())

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai(request, client=client)
		client.close()

		model_input = json.loads(json.loads(captured["body"])["input"])
		self.assertEqual(
			set(model_input["related_history"][0]),
			{"subject", "status", "inspection_result", "closeout_notes"},
		)
		self.assertNotIn("PRIVATE-WO-HIST-1", captured["body"])
		self.assertNotIn("alice@example.test", captured["body"])
		self.assertIn("Replaced the seal", captured["body"])
		self.assertGreaterEqual(response.audit.redaction_count, 1)

	def test_preserves_date_and_amount_facts_while_redacting_phone_shapes(self):
		request = _request()
		request.work_order.description = "Visited on 2026-07-10 and quoted 12 500.00 for the repair."
		request.work_order.closeout_notes = "Call 415-555-0100 or +1 (415) 555-0100 with ref 12345678901."
		captured = {}

		def handler(http_request):
			captured["body"] = http_request.content.decode()
			return httpx.Response(200, json=_provider_payload())

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai(request, client=client)
		client.close()

		for preserved_fact in ("2026-07-10", "12 500.00"):
			self.assertIn(preserved_fact, captured["body"])
		for phone_shape in ("415-555-0100", "+1 (415) 555-0100", "12345678901"):
			self.assertNotIn(phone_shape, captured["body"])
		self.assertEqual(response.audit.redaction_count, 3)

	def test_rejects_model_mismatch_and_missing_audit_metadata(self):
		for payload in (
			_provider_payload(model="unexpected-model"),
			_provider_payload(id=""),
			_provider_payload(usage=None),
		):
			client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=payload)))
			with patch.dict(os.environ, _environment(), clear=True):
				with self.assertRaises(OpenAIProviderError):
					render_openai(_request(), client=client)
			client.close()

	def test_repair_memory_redacts_pii_and_records_audit_parity(self):
		request = _repair_memory_request()
		request.work_order.description = "Email alice@example.test or call +1 (415) 555-0100."
		request.related_history[0].closeout_notes = "credential=synthetic-value-1234 and owner alice@example.test"
		captured = {}

		def handler(http_request):
			captured["body"] = http_request.content.decode()
			return httpx.Response(200, json=_provider_payload(draft="Prior seal replacement."))

		client = httpx.Client(transport=httpx.MockTransport(handler))
		with patch.dict(os.environ, _environment(), clear=True):
			response = render_openai_repair_memory(request, client=client)
		client.close()

		for sensitive in ("alice@example.test", "+1 (415) 555-0100", "synthetic-value-1234"):
			self.assertNotIn(sensitive, captured["body"])
		model_input = json.loads(json.loads(captured["body"])["input"])
		self.assertEqual(
			set(model_input["related_history"][0]),
			{"subject", "status", "inspection_result", "closeout_notes", "parts"},
		)
		self.assertNotIn("PRIVATE-WO-HIST-1", captured["body"])
		self.assertNotIn("PRIVATE-WO-0002", captured["body"])
		self.assertEqual(response.proposal_type, "repair_memory")
		self.assertEqual(response.policy.decision, "draft_only")
		self.assertIsNotNone(response.audit)
		self.assertGreaterEqual(response.audit.redaction_count, 3)
		self.assertEqual(response.audit.input_tokens, 120)
		self.assertEqual(response.audit.output_tokens, 20)
		self.assertEqual(len(response.audit.response_id_hash), 64)


def _repair_memory_request():
	return RepairMemoryRequest.model_validate(
		{
			"schema_version": 1,
			"request_id": str(uuid4()),
			"tenant_site": "private-tenant.example",
			"requested_by": "private-user@example.test",
			"work_order": {
				"doctype": "Service Work Order",
				"name": "PRIVATE-WO-0002",
				"subject": "Inspect pump again",
				"status": "In Progress",
				"description": "Investigate noise recurrence.",
			},
			"related_history": [
				{
					"name": "PRIVATE-WO-HIST-1",
					"subject": "Prior pump repair",
					"status": "Closed",
					"inspection_result": "Passed",
					"closeout_notes": "Replaced the seal.",
					"parts": [{"item": "SEAL-1", "qty": 1, "issued": True}],
				}
			],
			"sources": [
				{
					"doctype": "Service Work Order",
					"name": "PRIVATE-WO-0002",
					"field": "repair_context",
					"content_hash": "0" * 64,
				}
			],
		}
	)
