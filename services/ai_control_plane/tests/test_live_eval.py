import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from ai_erp_control_plane.live_eval import CREDENTIAL_ORIGIN_MARKER, LIVE_EVAL_ACKNOWLEDGEMENT, main, run_live_eval
from ai_erp_control_plane.models import ModelMetadata, Policy, ProposalResponse
from ai_erp_control_plane.openai_provider import OpenAIProviderError


def _environment(**overrides):
	values = {
		"AI_ERP_ENABLE_PRIVATE_LIVE_EVAL": LIVE_EVAL_ACKNOWLEDGEMENT,
		"AI_ERP_PROVIDER": "openai",
	}
	values["OPENAI_API_KEY_SOURCE"] = CREDENTIAL_ORIGIN_MARKER
	values["OPENAI_API_KEY"] = "example"
	values.update(overrides)
	return values


def _renderer(request):
	return ProposalResponse(
		schema_version=1,
		request_id=request.request_id,
		proposal_type="service_closeout_summary",
		policy=Policy(decision="draft_only", allowed_action="none", reason="Synthetic evaluation."),
		model=ModelMetadata(provider="openai", name="pinned-test-model", prompt_version="test@v1"),
		draft_content="The synthetic pump mount was tightened and operation was verified.",
		sources=request.sources,
	)


class TestPrivateLiveEval(unittest.TestCase):
	def test_requires_acknowledgement_secret_store_marker_and_openai_provider(self):
		for override in (
			{"AI_ERP_ENABLE_PRIVATE_LIVE_EVAL": ""},
			{"OPENAI_API_KEY_SOURCE": "shell"},
			{"AI_ERP_PROVIDER": "template"},
		):
			with self.subTest(override=override):
				with patch.dict(os.environ, _environment(**override), clear=True):
					with self.assertRaises(OpenAIProviderError):
						run_live_eval(renderer=_renderer)

	def test_uses_only_built_in_synthetic_input_and_emits_no_payload_or_secret(self):
		captured = {}

		def renderer(request):
			captured["request"] = request
			return _renderer(request)

		with patch.dict(os.environ, _environment(), clear=True):
			run_live_eval(renderer=renderer)

		request = captured["request"]
		self.assertTrue(request.tenant_site.endswith(".localhost"))
		self.assertTrue(request.requested_by.startswith("synthetic-"))
		self.assertTrue(request.work_order.name.startswith("SYNTHETIC-"))

	def test_main_reports_only_safe_aggregate_failure(self):
		output = io.StringIO()
		with patch.dict(os.environ, _environment(), clear=True):
			with patch("ai_erp_control_plane.live_eval.run_live_eval", side_effect=RuntimeError("example-private-detail")):
				with redirect_stdout(output):
					self.assertEqual(main(), 1)
		self.assertEqual(output.getvalue().strip(), "openai_live_eval=FAIL reason=provider_or_policy")
		self.assertNotIn("example-private-detail", output.getvalue())
