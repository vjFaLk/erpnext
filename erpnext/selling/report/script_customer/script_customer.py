# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	if not filters: filters ={}

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data

def get_data(filters):
	data = frappe.get_all("Customer", fields=["customer_name"])

	return data

def get_columns(filter):
	return [
		{
			"fieldname": "customer_name",
			"fieldtype": "Link",
			"label": "Customer Name",
			"options": "Customer"
		}
	]