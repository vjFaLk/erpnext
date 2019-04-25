from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, datetime, add_days, now_datetime, time_diff_in_hours, add_to_date

no_cache = 1

def get_context(context):
    token = frappe.local.request.args.get("token")
    contract = frappe.db.get_value("Contract", {"token" : token, "docstatus" : 1}, "name")


    if not contract:
        context.contract = {}
        return

    doc = frappe.get_doc("Contract", contract)

    if now_datetime() > add_to_date(doc.token_generated_on, hours=72):
        context.contract_expired = True

    context.contract = doc