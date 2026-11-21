# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Impact numbers for volunteers and admins (requirement 19): trees planted, requests attended, volunteer hours,
tree guards installed / removed. Every number carries the Desk list it opens (admins) or the public map (volunteers)."""
import frappe
from frappe import _
from frappe.utils import flt

from hasiruratha import api


def numbers():
	cl = "HR Care Log"
	hours = frappe.db.sql("select coalesce(sum(hours),0) from `tabHR Care Log`")[0][0] or 0
	attended = (frappe.db.count("HR Request", {"status": "Completed"}) + frappe.db.count("HR Tree Report", {"status": "Resolved"})
	            + frappe.db.count("HR Citizen Report", {"status": "Resolved"}))
	return {
		"trees": frappe.db.count("HR Tree", {"status": ["!=", "Merged"]}),
		"spots": frappe.db.count("HR Site", {"status": ["not in", ["Merged", "Needs Review"]]}),
		"requests_done": attended,
		"requests_open": frappe.db.count("HR Request", {"status": ["in", ["Received", "Under review", "Accepted", "Scheduled"]]}),
		"hours": round(flt(hours), 1),
		"guards_installed": frappe.db.count(cl, {"activity": "Guard installed"}),
		"guards_removed": frappe.db.count(cl, {"activity": "Guard removed"}),
		"volunteers": frappe.db.count("HR Volunteer", {"active": 1}),
	}


@frappe.whitelist()
def impact():
	user = frappe.session.user
	if user == "Guest" or not api._is_member(user):
		frappe.throw(_("Please sign in as a volunteer"), frappe.PermissionError)
	admin = api._is_admin(user)
	n = numbers()
	links = {
		"trees": "/app/hr-tree" if admin else "/trees",
		"requests_done": "/app/hr-request?status=Completed" if admin else "/my-requests",
		"hours": "/app/hr-care-log" if admin else "/my-trees",
		"guards_installed": "/app/hr-care-log?activity=Guard%20installed" if admin else "/my-trees",
		"guards_removed": "/app/hr-care-log?activity=Guard%20removed" if admin else "/my-trees",
		"volunteers": "/app/hr-volunteer?active=1" if admin else "",
	}
	return {"numbers": n, "links": links, "admin": admin}
