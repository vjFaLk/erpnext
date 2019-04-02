# import frappe

# def email_contract(doc, method):
#     print("\n==================\n","doc:",doc,"\nmethod:", method)
#     """
# 			Notify 'Contract Managers' about auto-creation
# 			of contracts
# 		"""
   
#     recipients = ["dikshajadhav11.dj@gmail.com"]
#     # recipients = get_emails_from_role("Contract Manager")

#     if recipients:
#         subject = "Contract to sign"
#         message = frappe.render_template("templates/emails/contract_generated.html", {
#             "contract": self
#         })

#     frappe.sendmail(recipients=recipients, subject=subject, message=message)