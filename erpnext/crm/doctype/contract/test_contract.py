# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest

import frappe
from erpnext.crm.doctype.contract.contract import sign_contract
from frappe.utils import add_days, nowdate


class TestContract(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("delete from `tabContract`")

		self.contract_doc = get_contract()
		self.sign_args = {
			"sign": "EXAMPLE SIGN",
			"signee": "SIGNEE NAME"
		}

	def test_contract_sign_invalid_token(self):
		self.contract_doc.insert()

		self.sign_args.update({
			"contract": self.contract_doc.name,
			"token": "INVALID TOKEN"
		})

		self.assertRaises(frappe.ValidationError, sign_contract, **self.sign_args)

	def test_contract_sign_success(self):
		self.contract_doc.insert()

		self.sign_args.update({
			"contract": self.contract_doc.name,
			"token": self.contract_doc.token
		})

		sign_contract(**self.sign_args)

		self.contract_doc.load_from_db()
		self.assertEqual(self.contract_doc.is_signed, 1)

	def test_contract_sign_with_existing_sign(self):
		self.contract_doc.insert()

		self.sign_args.update({
			"contract": self.contract_doc.name,
			"token": self.contract_doc.token
		})

		sign_contract(**self.sign_args)
		self.assertRaises(frappe.ValidationError, sign_contract, **self.sign_args)

	def test_token_generation(self):
		self.assertEqual(self.contract_doc.token, None)
		self.assertEqual(self.contract_doc.token_generated_on, None)

		self.contract_doc.insert()
		self.assertNotEqual(self.contract_doc.token, None)
		self.assertNotEqual(self.contract_doc.token_generated_on, None)

	def test_validate_start_date_before_end_date(self):
		self.contract_doc.start_date = nowdate()
		self.contract_doc.end_date = add_days(nowdate(), -1)

		self.assertRaises(frappe.ValidationError, self.contract_doc.insert)

	def test_unsigned_contract_status(self):
		self.contract_doc.insert()
		self.assertEqual(self.contract_doc.status, "Unsigned")

	def test_active_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -1)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Active")

	def test_past_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), -1)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_future_inactive_signed_contract_status(self):
		self.contract_doc.is_signed = True
		self.contract_doc.start_date = add_days(nowdate(), 1)
		self.contract_doc.end_date = add_days(nowdate(), 2)
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.status, "Inactive")

	def test_contract_status_with_no_fulfilment_terms(self):
		self.contract_doc.contract_term = "_Test Customer Contract"
		self.contract_doc.insert()

		self.assertEqual(self.contract_doc.fulfilment_status, "N/A")

	def test_unfulfilled_contract_status(self):
		self.contract_doc.contract_term = "_Test Customer Contract with Requirements"
		self.contract_doc.requires_fulfilment = 1
		self.contract_doc.save()
		self.assertEqual(self.contract_doc.fulfilment_status, "Unfulfilled")

	def test_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = "_Test Customer Contract with Requirements"

		# Mark all the terms as fulfilled
		self.contract_doc.requires_fulfilment = 1
		fulfilment_terms = []
		fulfilment_terms.append({
			"requirement": "This is a test requirement.",
			"fulfilled": 0
		})
		self.contract_doc.set("fulfilment_terms", fulfilment_terms)

		for term in self.contract_doc.fulfilment_terms:
			term.fulfilled = 1

		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Fulfilled")

	def test_partially_fulfilled_contract_status(self):
		self.contract_doc.contract_terms = "_Test Customer Contract with Requirements"
		self.contract_doc.requires_fulfilment = 1

		# Mark only the first term as fulfilled
		self.contract_doc.save()
		fulfilment_terms = []
		fulfilment_terms.append({
			"requirement": "This is a test requirement.",
			"fulfilled": 0
		})
		fulfilment_terms.append({
			"requirement": "This is another test requirement.",
			"fulfilled": 0
		})

		self.contract_doc.set("fulfilment_terms", fulfilment_terms)
		self.contract_doc.fulfilment_terms[0].fulfilled = 1
		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Partially Fulfilled")

	def test_lapsed_contract_status(self):
		self.contract_doc.contract_term = "_Test Customer Contract with Requirements"
		self.contract_doc.start_date = add_days(nowdate(), -2)
		self.contract_doc.end_date = add_days(nowdate(), 1)
		self.contract_doc.requires_fulfilment = 1
		self.contract_doc.fulfilment_deadline = add_days(nowdate(), -1)
		self.contract_doc.save()

		self.assertEqual(self.contract_doc.fulfilment_status, "Lapsed")


def get_contract():
	doc = frappe.new_doc("Contract")
	doc.party_type = "Customer"
	doc.party_name = "_Test Customer"
	doc.contract_terms = "This is a test customer contract."
	doc.email = "test@example.com"
	return doc
