# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.core.doctype.role.role import get_emails_from_role
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate


class Contract(Document):
	def autoname(self):
		name = self.party_name

		if self.contract_template:
			name += " - {} Agreement".format(self.contract_template)

		if frappe.db.exists("Contract", name):
			count = len(frappe.get_all("Contract",
				filters={"name": ["like", "%{}%".format(name)]}))
			name = "{} - {}".format(name, count)

		self.name = _(name)

	def validate(self):
		self.validate_dates()
		self.update_contract_status()
		self.update_fulfilment_status()

	def after_insert(self):
		self.generate_token()

	def generate_token(self):
		self.token = frappe.generate_hash(self.name, 32)
		self.token_generated_on = now_datetime()
		self.contract_link = "http://{0}/sign_contract?token={1}".format(frappe.local.site, self.token)

	def before_update_after_submit(self):
		self.update_contract_status()
		self.update_fulfilment_status()

	def validate_dates(self):
		if self.end_date and self.end_date < self.start_date:
			frappe.throw(_("End Date cannot be before Start Date."))

	def on_submit(self):
		self.email_contract_link()

	def email_contract_link(self):
		"""
			Email the contract link to user for them to sign it
		"""
		message = frappe.render_template("templates/emails/contract_generated.html", {
			"contract": self,
			"link": self.contract_link
		})

		frappe.sendmail(recipients=[self.email], subject="A Contract has been generated for you", message=message)
		frappe.msgprint("Contract has been successfully sent to Email")

	def update_contract_status(self):
		if self.is_signed:
			self.status = get_status(self.start_date, self.end_date)
		else:
			self.status = "Unsigned"

	def update_fulfilment_status(self):
		fulfilment_status = "N/A"

		if self.requires_fulfilment:
			fulfilment_progress = self.get_fulfilment_progress()

			if not fulfilment_progress:
				fulfilment_status = "Unfulfilled"
			elif fulfilment_progress < len(self.fulfilment_terms):
				fulfilment_status = "Partially Fulfilled"
			elif fulfilment_progress == len(self.fulfilment_terms):
				fulfilment_status = "Fulfilled"

			if fulfilment_status != "Fulfilled" and self.fulfilment_deadline:
				now_date = getdate(nowdate())
				deadline_date = getdate(self.fulfilment_deadline)

				if now_date > deadline_date:
					fulfilment_status = "Lapsed"

		self.fulfilment_status = fulfilment_status

	def get_fulfilment_progress(self):
		return len([term for term in self.fulfilment_terms if term.fulfilled])


@frappe.whitelist(allow_guest=True)
def sign_contract(sign, signee, contract, token):
	"""
		Gets signee: whoever signed the contract, contract: contract name

		updates is_signed, signee and signed_on field in db

		returns relevant message
	"""
	doc = frappe.get_doc("Contract", contract)

	if not doc.token == token:
		frappe.throw("Invalid Token for Contract")

	if doc.is_signed:
		frappe.throw("Contract already signed")

	doc.is_signed = 1
	doc.signature = sign
	doc.signee = signee
	doc.signed_on = now_datetime()
	doc.save(ignore_permissions=1)

@frappe.whitelist(allow_guest=True)
def reset_token(contract_name, email):
	contract = frappe.get_doc("Contract", contract_name)
	if not contract.email == email:
		frappe.throw("Invalid Email")

	contract.flags.ignore_permissions = True
	contract.generate_token()
	contract.email_contract_link()
	contract.save()
	frappe.db.commit()


def get_status(start_date, end_date):
	"""
	Get a Contract's status based on the start, current and end dates

	Args:
		start_date (str): The start date of the contract
		end_date (str): The end date of the contract

	Returns:
		str: 'Active' if within range, otherwise 'Inactive'
	"""

	if not end_date:
		return "Active"

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	now_date = getdate(nowdate())

	return "Active" if start_date < now_date < end_date else "Inactive"


def update_status_for_contracts():
	"""
		Run the daily hook to update the statuses for all signed
		and submitted Contracts
	"""

	contracts = frappe.get_all("Contract",
		filters={"is_signed": True, "docstatus": 1},
		fields=["name", "start_date", "end_date"])

	for contract in contracts:
		status = get_status(contract.get("start_date"), contract.get("end_date"))
		frappe.db.set_value("Contract", contract.get("name"), "status", status)
