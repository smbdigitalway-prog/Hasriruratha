# create a volunteer the way an admin would (no sign-in account yet), with the given phone and email
import sys, frappe
frappe.init("hr.localhost", sites_path="/home/frappe/frappe-bench/sites"); frappe.connect()
phone, email = sys.argv[1], sys.argv[2]
vid = "VOL-T" + phone[-6:]
if not frappe.db.exists("HR Volunteer", vid):
    frappe.get_doc({"doctype": "HR Volunteer", "volunteer_id": vid, "volunteer_name": "Old Volunteer", "phone": phone,
                    "email": email, "active": 1, "group_id": "GRP-001"}).insert(ignore_permissions=True)
frappe.db.commit(); print(vid)
