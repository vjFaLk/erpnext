from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, datetime, add_days, now_datetime, time_diff_in_hours, add_to_date

no_cache = 1

def get_context(context):
    a = frappe.local.request.environ.get("QUERY_STRING")
    requesting_token = ""
    count = 0
    for i in a:
        if i == "=":
            count += 1
            continue
        elif count == 1:
            requesting_token += cstr(i)
   
    token = cstr(requesting_token)
    doc = frappe.get_doc("Contract", {"hash" : requesting_token})
    
    if now_datetime() > add_to_date(doc.hash_generated_on, hours=24):
        raise frappe.DoesNotExistError
       
    else:
        context.contract = doc
        
 