import os
from unittest.mock import patch

import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, now_datetime, today

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

	def test_distribution_standard_workflow_reaches_draft_shortage_handoff_without_posting(self):
		self.addCleanup(frappe.db.rollback)
		before = self._posting_counts()
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			result = seed("distribution")
		order = frappe.get_doc("Sales Order", result["sales_order"])
		order.submit()
		pick_list = frappe.get_doc(
			{
				"doctype": "Pick List",
				"company": result["company"],
				"purpose": "Delivery",
				"customer": result["customer"],
				"parent_warehouse": result["warehouses"][0],
				"pick_manually": 1,
				"locations": [
					{
						"item_code": row.item_code,
						"qty": row.qty,
						"picked_qty": 0,
						"warehouse": row.warehouse,
						"stock_uom": row.stock_uom,
						"uom": row.uom,
						"conversion_factor": row.conversion_factor,
						"sales_order": order.name,
						"sales_order_item": row.name,
					}
					for row in order.items
				],
			}
		).insert()
		delivery_note = make_delivery_note(order.name)
		delivery_note.insert()

		self.assertEqual(pick_list.docstatus, 0)
		self.assertTrue(all(row.picked_qty == 0 and row.qty > 0 for row in pick_list.locations))
		self.assertEqual(delivery_note.docstatus, 0)
		self.assertTrue(all(row.against_sales_order == order.name for row in delivery_note.items))
		self.assertEqual(self._posting_counts(), before)

	def test_manufacturing_standard_workflow_reaches_draft_material_handoff_without_posting(self):
		self.addCleanup(frappe.db.rollback)
		before = self._posting_counts()
		with patch.dict(os.environ, {"AI_ERP_CONFIGURED_DEMO_ALLOW": "1"}, clear=False):
			result = seed("light_manufacturing")
		bom = frappe.get_doc("BOM", result["bom"])
		bom.submit()
		order = frappe.get_doc("Sales Order", result["sales_order"])
		order.submit()
		order_item = order.items[0]
		production_plan = frappe.get_doc(
			{
				"doctype": "Production Plan",
				"company": result["company"],
				"get_items_from": "Sales Order",
				"po_items": [
					{
						"item_code": result["finished_item"],
						"bom_no": bom.name,
						"planned_qty": order_item.qty,
						"planned_start_date": now_datetime(),
						"stock_uom": order_item.stock_uom,
						"warehouse": result["warehouses"][2],
						"sales_order": order.name,
						"sales_order_item": order_item.name,
					}
				],
			}
		).insert()
		work_order = frappe.get_doc(
			{
				"doctype": "Work Order",
				"production_item": result["finished_item"],
				"bom_no": bom.name,
				"qty": order_item.qty,
				"company": result["company"],
				"sales_order": order.name,
				"sales_order_item": order_item.name,
				"source_warehouse": result["warehouses"][0],
				"wip_warehouse": result["warehouses"][1],
				"fg_warehouse": result["warehouses"][2],
				"planned_start_date": now_datetime(),
			}
		).insert()
		material_request = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Purchase",
				"company": result["company"],
				"schedule_date": add_days(today(), 2),
				"items": [
					{
						"item_code": row.item_code,
						"qty": row.required_qty,
						"uom": row.stock_uom,
						"stock_uom": row.stock_uom,
						"conversion_factor": 1,
						"warehouse": result["warehouses"][0],
						"schedule_date": add_days(today(), 2),
						"sales_order": order.name,
						"sales_order_item": order_item.name,
						"bom_no": bom.name,
					}
					for row in work_order.required_items
				],
			}
		).insert()

		self.assertEqual(production_plan.docstatus, 0)
		self.assertEqual(work_order.docstatus, 0)
		self.assertTrue(
			all(
				self._available_quantity(row.item_code, result["warehouses"]) == 0
				for row in work_order.required_items
			)
		)
		self.assertEqual(material_request.docstatus, 0)
		self.assertEqual(self._posting_counts(), before)

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

	def _posting_counts(self):
		return {
			"stock_ledger": frappe.db.count("Stock Ledger Entry"),
			"gl_entry": frappe.db.count("GL Entry"),
			"stock_entry": frappe.db.count("Stock Entry"),
		}
