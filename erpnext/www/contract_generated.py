from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, datetime, add_days, now_datetime

no_cache = 1

def get_context(context):
    # TODO : Get Token Value from Request Object
    print("\n======++++++++++++====frappe.local.request", frappe.local.request)
    print("\n======++++++++++++====frappe.local.request", frappe.local.request.__dict__)
    print("\n======++++++++++++====type(frappe.local.request.__dict__)", type(frappe.local.request.__dict__))

    print("header", frappe.local.request.headers)
    print("frappe.local.request.environ", frappe.local.request.environ.get("QUERY_STRING"), "\ntype of query string", type(frappe.local.request.environ.get("QUERY_STRING")))

    a = frappe.local.request.environ.get("QUERY_STRING")
    requesting_token = ""
    count = 0
    for i in a:
        if i == "=":
            count += 1
            continue
        elif count == 1:
            requesting_token += cstr(i)
    print("cstr(requesting_token)", cstr(requesting_token), "type(re", type(requesting_token))     
    token = cstr(requesting_token)

    # TODO : Get Contract based on token in Contract
    doc = frappe.get_doc("Contract", {"hash" : requesting_token})
    # doc = frappe.get_all('Contract', filters={'hash': requesting_token})[0]
    print("***doc****", doc)
    if add_days(doc.hash_generated_on, 1) < now_datetime():
        context.error = "Invalid link"
    else:
        context.contract = doc
    # TODO : Display relevant Contract Info