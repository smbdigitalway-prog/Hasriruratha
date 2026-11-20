# approve the pending volunteer application of a user, as an admin would in the Desk
import sys, frappe
frappe.init("hr.localhost", sites_path="/home/frappe/frappe-bench/sites"); frappe.connect(); frappe.set_user("Administrator")
email = sys.argv[1]
vol = frappe.db.get_value("HR Volunteer", {"user": email}, "name")
app = frappe.db.get_value("HR Application", {"volunteer": vol, "status": "Pending"}, "name")
from hasiruratha import citizen_api
print(citizen_api.review_application(name=app, approve=1)); frappe.db.commit()
