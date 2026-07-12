# Copyright (c) 2026, AI ERP Demo and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


IGNORE_TEST_RECORD_DEPENDENCIES = ["Address", "Customer", "Warehouse"]


class IntegrationTestServiceLocation(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "Service Location Test {0}".format(frappe.generate_hash(length=8)),
				"customer_type": "Company",
			}
		).insert()

	def test_creation_requires_a_customer(self):
		location = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Synthetic service site",
				"customer": self.customer.name,
			}
		).insert()

		self.assertTrue(location.name.startswith("SVC-LOC-"))
		self.assertEqual(location.customer, self.customer.name)
		self.assertEqual(location.active, 1)

		without_customer = frappe.get_doc(
			{
				"doctype": "Service Location",
				"location_name": "Invalid service site",
			}
		)
		with self.assertRaises(frappe.MandatoryError):
			without_customer.insert()
