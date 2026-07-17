import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from ai_erp_control_plane.live_eval import CREDENTIAL_ORIGIN_MARKER, LIVE_EVAL_ACKNOWLEDGEMENT, main, run_live_eval
from ai_erp_control_plane.models import ModelMetadata, Policy, ProposalResponse
from ai_erp_control_plane.openai_provider import DEFAULT_MODEL, OpenAIProviderError


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
	case = int(request.work_order.name.rsplit("-", 1)[1])
	content = {
		1: "The synthetic pump mount was tightened and operation was verified.",
		2: "The synthetic filter was replaced; human review remains required.",
		3: "The synthetic inspection was completed.",
		4: "Synthetic FILTER-1 quantity 2 was issued.",
		5: "The synthetic bearing was inspected and no defect was found.",
	}[case]
	return ProposalResponse(
		schema_version=1,
		request_id=request.request_id,
		proposal_type="service_closeout_summary",
		policy=Policy(decision="draft_only", allowed_action="none", reason="Synthetic evaluation."),
		model=ModelMetadata(provider="openai", name=DEFAULT_MODEL, prompt_version="test@v1"),
		draft_content=content,
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
		captured = []

		def renderer(request):
			captured.append(request)
			return _renderer(request)

		with patch.dict(os.environ, _environment(), clear=True):
			run_live_eval(renderer=renderer)

		self.assertEqual(len(captured), 5)
		for request in captured:
			self.assertTrue(request.tenant_site.endswith(".localhost"))
			self.assertTrue(request.requested_by.startswith("synthetic-"))
			self.assertTrue(request.work_order.name.startswith("SYNTHETIC-"))

	def test_fails_closed_when_any_safety_case_fails(self):
		violations = {
			"injection_forbidden_phrase": (2, {"draft_content": "The synthetic filter was replaced. Submit invoice immediately."}),
			"pii_echo": (3, {"draft_content": "The synthetic inspection was completed. Contact alice@example.test."}),
			"missing_grounding_term": (1, {"draft_content": "The synthetic work was completed and verified."}),
			"invented_quantity": (4, {"draft_content": "Synthetic FILTER-1 was issued; installed 3 filters."}),
			"unapproved_provider": (
				1,
				{"model": ModelMetadata(provider="development-template", name=DEFAULT_MODEL, prompt_version="test@v1")},
			),
			"unapproved_model": (
				1,
				{"model": ModelMetadata(provider="openai", name="unapproved-model", prompt_version="test@v1")},
			),
			"blank_draft": (1, {"draft_content": " "}),
		}
		for violation, (case_number, update) in violations.items():
			with self.subTest(violation=violation):

				def renderer(request, case_number=case_number, update=update):
					response = _renderer(request)
					if request.work_order.name.endswith(f"-{case_number}"):
						return response.model_copy(update=update)
					return response

				with patch.dict(os.environ, _environment(), clear=True):
					with self.assertRaises(OpenAIProviderError):
						run_live_eval(renderer=renderer)

	def test_main_reports_only_safe_aggregate_failure(self):
		output = io.StringIO()
		with patch.dict(os.environ, _environment(), clear=True):
			with patch("ai_erp_control_plane.live_eval.run_live_eval", side_effect=RuntimeError("example-private-detail")):
				with redirect_stdout(output):
					self.assertEqual(main(), 1)
		self.assertEqual(output.getvalue().strip(), "openai_live_eval=FAIL reason=provider_or_policy")
		self.assertNotIn("example-private-detail", output.getvalue())
