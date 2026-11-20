# Local test data for admin.js: an admin with no mobile number (signs in by email) and a disabled
# admin whose mobile number also sits on a volunteer record (the reset page must refuse it).
import frappe
from frappe.utils.password import update_password

frappe.init("hr.localhost", sites_path="/home/frappe/frappe-bench/sites"); frappe.connect(); frappe.set_user("Administrator")
if not frappe.db.exists("User", "boss@example.com"):
	frappe.get_doc({"doctype": "User", "email": "boss@example.com", "first_name": "Boss", "enabled": 1, "send_welcome_email": 0,
	                "roles": [{"role": "HR Admin"}, {"role": "System Manager"}]}).insert()
update_password("boss@example.com", "Admin2026pass")
if not frappe.db.exists("User", "oldadmin@example.com"):
	frappe.get_doc({"doctype": "User", "email": "oldadmin@example.com", "first_name": "Old", "mobile_no": "9123456789",
	                "enabled": 0, "send_welcome_email": 0, "roles": [{"role": "HR Admin"}]}).insert()
if not frappe.db.exists("HR Volunteer", "VOL-ADM1"):
	frappe.get_doc({"doctype": "HR Volunteer", "volunteer_id": "VOL-ADM1", "volunteer_name": "Admin Vol", "phone": "9123456789",
	                "email": "adminvol@example.com", "active": 1, "group_id": "GRP-001"}).insert(ignore_permissions=True)
frappe.db.commit()
