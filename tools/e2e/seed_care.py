# local test data for care.js: a volunteer account with password, two assigned trees, one without GPS
import frappe
from frappe.utils.password import update_password
frappe.init("hr.localhost", sites_path="/home/frappe/frappe-bench/sites"); frappe.connect(); frappe.set_user("Administrator")
email, mob = "care.vol@example.com", "9555500001"
if not frappe.db.exists("User", email):
    frappe.get_doc({"doctype": "User", "email": email, "first_name": "Care Volunteer", "mobile_no": mob, "enabled": 1,
                    "user_type": "Website User", "send_welcome_email": 0, "roles": [{"role": "HR Volunteer"}]}).insert()
update_password(email, "Water2026x")
if not frappe.db.exists("HR Volunteer", "VOL-CARE1"):
    frappe.get_doc({"doctype": "HR Volunteer", "volunteer_id": "VOL-CARE1", "volunteer_name": "Care Volunteer", "phone": mob,
                    "email": email, "user": email, "active": 1, "group_id": "GRP-001"}).insert(ignore_permissions=True)
trees = frappe.get_all("HR Tree", {"site_id": "S-JAY-001"}, pluck="name")
for t in trees:
    frappe.db.set_value("HR Tree", t, {"owner_volunteer_id": "VOL-CARE1", "last_watered": None, "last_maintenance": None})
frappe.db.sql("delete from `tabHR Care Log` where tree in %s", (tuple(trees),))
frappe.db.set_value("HR Tree", trees[-1], {"gps_lat": 0, "gps_lng": 0, "gps_status": "Pending"})
frappe.db.commit(); print(trees)
# a plain citizen account for access.js (no volunteer role)
cit = "probe.citizen@example.com"
if not frappe.db.exists("User", cit):
    frappe.get_doc({"doctype": "User", "email": cit, "first_name": "Probe Citizen", "enabled": 1, "user_type": "Website User",
                    "send_welcome_email": 0}).insert(ignore_permissions=True)
update_password(cit, "Citizen2026x")
frappe.db.commit()
