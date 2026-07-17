import os
from unittest import TestCase
from unittest.mock import patch

import frappe

import ai_erp_service.performance as performance
from ai_erp_service.performance import (
	EXTERNAL_SCENARIOS,
	IMPLEMENTED_SCENARIOS,
	nearest_rank_p95,
	scaled_count,
	validate_profile,
)


class TestPerformanceSmokeHelpers(TestCase):
	def test_nearest_rank_p95_uses_the_nearest_rank_definition(self):
		self.assertEqual(nearest_rank_p95(range(1, 21)), 19)
		self.assertEqual(nearest_rank_p95([0.125]), 0.125)

	def test_scaled_count_keeps_small_record_classes_represented(self):
		self.assertEqual(scaled_count(100, 0.01), 2)
		self.assertEqual(scaled_count(5000, 0.01), 50)

	def test_profile_must_be_explicitly_synthetic(self):
		profile = {
			"schema_version": 1,
			"profile_id": "service-operations-mvp-v1",
			"synthetic_only": False,
			"data_profile": {},
			"targets": {},
			"scenarios": [],
		}
		with self.assertRaisesRegex(ValueError, "synthetic-only"):
			validate_profile(profile)

	def test_profile_rejects_duplicate_scenarios_and_invalid_values(self):
		scenarios = [
			{"id": scenario_id, "target": "interactive_p95_seconds"}
			for scenario_id in sorted(IMPLEMENTED_SCENARIOS | set(EXTERNAL_SCENARIOS))
		]
		base = {
			"schema_version": 1,
			"profile_id": "service-operations-mvp-v1",
			"synthetic_only": True,
			"privacy_rules": [
				"Do not use customer exports, production logs, production database snapshots, or prompt bodies."
			],
			"data_profile": {"service_work_orders": 10},
			"targets": {"interactive_p95_seconds": 1},
			"scenarios": scenarios,
		}

		duplicate = {**base, "scenarios": [*scenarios, scenarios[0]]}
		with self.assertRaisesRegex(ValueError, "unique"):
			validate_profile(duplicate)

		invalid_count = {**base, "data_profile": {"service_work_orders": 0}}
		with self.assertRaisesRegex(ValueError, "positive integers"):
			validate_profile(invalid_count)

		invalid_target = {**base, "targets": {"interactive_p95_seconds": -1}}
		with self.assertRaisesRegex(ValueError, "positive numbers"):
			validate_profile(invalid_target)

		missing_mapping = {**base, "scenarios": [{**scenarios[0], "target": "missing"}, *scenarios[1:]]}
		with self.assertRaisesRegex(ValueError, "configured target"):
			validate_profile(missing_mapping)

		missing_privacy = {**base, "privacy_rules": ["Synthetic only."]}
		with self.assertRaisesRegex(ValueError, "privacy boundaries"):
			validate_profile(missing_privacy)

	def test_injected_failure_rolls_back_synthetic_records_and_restores_user(self):
		original_user = frappe.session.user
		before = frappe.db.count("Service Work Order", {"subject": ["like", "PERF-%"]})
		environment = {
			"AI_ERP_PERFORMANCE_ALLOW": "1",
			"AI_ERP_PROVIDER": "template",
			"AI_CONTROL_PLANE_URL": "http://ai-control-plane:8090",
			"AI_CONTROL_PLANE_SHARED_SECRET": "change-this-local-control-plane-secret",
		}
		with (
			patch.dict(os.environ, environment, clear=False),
			patch.object(
				performance,
				"_run_list_scenario",
				side_effect=performance.PerformanceSmokeError("injected failure"),
			),
			self.assertRaises(frappe.ValidationError),
		):
			performance.run(scale=0.0001, samples=20, strict=True, allow_local=True)

		self.assertEqual(frappe.session.user, original_user)
		self.assertEqual(
			frappe.db.count("Service Work Order", {"subject": ["like", "PERF-%"]}),
			before,
		)
