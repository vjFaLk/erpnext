# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe import _
from erpnext import get_default_company
from frappe.model.document import Document
from frappe.core.doctype.role.role import get_emails_from_role
from frappe.model.mapper import get_mapped_doc
from erpnext.selling.doctype.quotation.quotation import make_sales_order
from frappe.utils import getdate, now_datetime, nowdate, get_link_to_form, cstr, datetime


class Contract(Document):
	def autoname(self):
		name = self.party_name

		if self.contract_template:
			name += " - {} Agreement".format(self.contract_template)

		# If identical, append contract name with the next number in the iteration
		if frappe.db.exists("Contract", name):
			count = len(frappe.get_all("Contract", filters={"name": ["like", "%{}%".format(name)]}))
			name = "{} - {}".format(name, count)

		self.name = _(name)
		

	def validate(self):
		self.validate_dates()
		self.update_contract_status()
		self.update_fulfilment_status()

	def after_insert(self):
		self.create_hash()

	def create_hash(self):
		self.hash = cstr(hash(self.name)).lstrip("-")
		self.hash_generated_on = now_datetime()
		self.save()

	def before_update_after_submit(self):
		self.update_contract_status()
		self.update_fulfilment_status()

	def validate_dates(self):
		if self.end_date and self.end_date < self.start_date:
			frappe.throw(_("End Date cannot be before Start Date."))

	def on_submit(self):
		# self.send_contract_email_notification()
		self.email_contract_link()
		
		self.create_sales_invoice()
		# self.send_sales_invoice_email_notification()

	# def before_submit(self):
		
		

	def send_contract_email_notification(self):
		"""
			Notify 'Contract Managers' about auto-creation
			of contracts
		"""
		recipients = ["dikshajadhav11.dj@gmail.com"]
		# recipients = get_emails_from_role("Contract Manager")
		
		if recipients:
			subject = "Contract Generated"
			message = frappe.render_template("templates/emails/contract_generated.html", {
				"contract": self
			})

		frappe.sendmail(recipients=recipients, subject=subject, message=message)
	
	def email_contract_link(self):
		"""
			Email the contract link to user for him to sign it
		"""

		recipients = ["diksha@digithinkit.com"]
		# recipients = get_emails_from_role("Contract Manager")

		link_to_contract = "http://localhost:8000/contract_generated" + "?token=" + self.hash

		if recipients:
			subject = "Contract to sign"
			# message = frappe.render_template("www/contract_generated.html", {
			# 	"contract": self
			# })
			message = link_to_contract

		# TODO : Create fields to store token and token generation time
		# TODO : Store Hash and current Datetime (checkout frappe/utils/data.py to get time related functions) in Contract

		frappe.sendmail(recipients=recipients, subject=subject, message=message)
		

	def create_sales_invoice(self):
		sales_invoice = frappe.new_doc("Sales Invoice")
		default_company = "Synergy Business Management INC."

		sales_invoice.update({
			"customer": self.party_name,
			# "company": get_default_company(),
			"company": default_company,
			"contract": self,
			"exempt_from_sales_tax": 1,
			"due_date": nowdate(),
		})

		contract_link = get_link_to_form("Contract", self.name)

		# for order, discount in order_discounts.items()
		# order_link = get_link_to_form("Sales Order", order.name)

		sales_invoice.append("items", {
			"item_name": "Contract lapse fee",
			"description": "This fee is charged for the non-compliance of Contract {0}".format(contract_link),
			"qty": 1,
			"uom": "Nos",
			"rate": 45,
			"conversion_factor": 1,
			# TODO: make income account configurable from the frontend
			"income_account": frappe.db.get_value("Company", default_company, "default_income_account"),
			"cost_center": frappe.db.get_value("Company", default_company, "cost_center")
		})

		sales_invoice.set_missing_values()
		sales_invoice.insert()

		return sales_invoice


	def send_sales_invoice_email_notification(self):
		"""
			Notify 'Contract Managers' about auto-creation
			of sales invoice
		"""
		recipients = ["dikshajadhav11.dj@gmail.com"]
		# recipients = get_emails_from_role("Contract Manager")

		if recipients:
			subject = "Sales invoice Generated"
			# message = frappe.render_template("templates/emails/contract_generated.html", {
			# 	"contract": self
			# })
			message = "Sales invoice generated"

		frappe.sendmail(recipients=recipients, subject=subject, message=message)

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
		

@frappe.whitelist()
def accept_contract_terms(signee, contract=None):
	"""
	Gets signee: whoever signed the contract, contract: contract name

	updates is_signed, signee and signed_on field in db

	returns relevant message
	"""
	try:
		doc = frappe.get_doc("Contract", contract)
		# frappe.db.set_value("Contract", contract , "is_signed", 1, "signee", signee, "signed", "signed_on", now_datetime())
		doc.is_signed = 1
		doc.signee = signee
		doc.signed_on = now_datetime()
		doc.save()
		return "Your contract is shared successfully!"
	except:
		return "couldn't submit signing"
	finally:
		doc = frappe.get_doc("Contract", contract)
		quotation = frappe.get_doc("Quotation", doc.document_name)
		make_sales_order(quotation.name)


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
								filters={"is_signed": True,
										"docstatus": 1},
								fields=["name", "start_date", "end_date"])

	for contract in contracts:
		status = get_status(contract.get("start_date"),
							contract.get("end_date"))

		frappe.db.set_value("Contract", contract.get("name"), "status", status)
