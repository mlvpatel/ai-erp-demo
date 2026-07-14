import os
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from ai_erp_core.configured_demo import reset, seed


class TestConfiguredIndustryDemos(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_seed_requires_explicit_local_opt_in(self):
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "0"}, clear=False):
			with self.assertRaises(frappe.PermissionError):
				seed("distribution")

	def test_non_manager_cannot_seed(self):
		frappe.set_user("Guest")
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			with self.assertRaises(frappe.PermissionError):
				seed("distribution")

	def test_distribution_seed_is_idempotent_draft_only_and_non_posting(self):
		before = self._ledger_and_submission_counts()
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			first = seed("distribution")
			second = seed("distribution")

		self.assertEqual(first["sales_order"], second["sales_order"])
		self.assertEqual(len(first["warehouses"]), 2)
		self.assertEqual(frappe.db.get_value("Sales Order", first["sales_order"], "docstatus"), 0)
		for item in first["items"]:
			self.assertEqual(self._available_quantity(item, first["warehouses"]), 0)
		self.assertEqual(self._ledger_and_submission_counts(), before)

	def test_manufacturing_seed_is_idempotent_draft_only_and_non_posting(self):
		before = self._ledger_and_submission_counts()
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			first = seed("light_manufacturing")
			second = seed("light_manufacturing")

		self.assertEqual(first["sales_order"], second["sales_order"])
		self.assertEqual(first["bom"], second["bom"])
		self.assertEqual(frappe.db.get_value("Sales Order", first["sales_order"], "docstatus"), 0)
		self.assertEqual(frappe.db.get_value("BOM", first["bom"], "docstatus"), 0)
		for item in first["components"]:
			self.assertEqual(self._available_quantity(item, first["warehouses"]), 0)
		self.assertEqual(self._ledger_and_submission_counts(), before)

	def test_reset_removes_only_configured_draft_records_and_is_idempotent(self):
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			distribution = seed("distribution")
			manufacturing = seed("light_manufacturing")
			reset("distribution")
			reset("distribution")
			reset("light_manufacturing")
			reset("light_manufacturing")

		self.assertFalse(frappe.db.exists("Sales Order", distribution["sales_order"]))
		self.assertFalse(frappe.db.exists("Sales Order", manufacturing["sales_order"]))
		self.assertFalse(frappe.db.exists("BOM", manufacturing["bom"]))

	def _ledger_and_submission_counts(self):
		return {
			"stock_ledger": frappe.db.count("Stock Ledger Entry"),
			"gl_entry": frappe.db.count("GL Entry"),
			"stock_entry": frappe.db.count("Stock Entry"),
			"pick_list": frappe.db.count("Pick List"),
			"delivery_note": frappe.db.count("Delivery Note"),
			"production_plan": frappe.db.count("Production Plan"),
			"work_order": frappe.db.count("Work Order"),
			"material_request": frappe.db.count("Material Request"),
		}

	def _available_quantity(self, item, warehouses):
		return sum(
			flt(value)
			for value in frappe.get_all(
				"Bin",
				filters={"item_code": item, "warehouse": ["in", warehouses]},
				pluck="actual_qty",
			)
		)
