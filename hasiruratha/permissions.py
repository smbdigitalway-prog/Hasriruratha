# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
What a volunteer may do in the Desk.

Volunteers (role HR Volunteer) see the organisation's records read-only. Phone numbers, emails and
addresses of volunteers and citizens are at permission level 1, which only admins can read. A volunteer
may change only the trees assigned to them (HR Tree.owner_volunteer_id), and only the care fields of
those trees, and may add care log entries for those trees.
"""
import frappe
from frappe import _
from frappe.utils import flt

from hasiruratha import api

VOLUNTEER_WORKSPACE = "hasiru_ratha"
ADMIN_WORKSPACE = "hasiru_ratha_admin"
VOLUNTEER_HOME = "/desk/hasiruratha/" + VOLUNTEER_WORKSPACE
ADMIN_HOME = "/desk/hasiruratha/" + ADMIN_WORKSPACE
# fields of their own trees a volunteer may change (GPS only while it is still pending)
TREE_FIELDS_FOR_VOLUNTEERS = {"species", "condition", "tree_guard", "support_pole", "notes", "photo_url",
                              "caretaker_name"}
GPS_FIELDS = {"gps_lat", "gps_lng"}


def volunteer_only(user=None):
	"""True for a volunteer who is not also an admin."""
	user = user or frappe.session.user
	return user != "Guest" and not api._is_admin(user) and api.VOLUNTEER_ROLE in frappe.get_roles(user)


def my_volunteer(user=None):
	return frappe.db.get_value("HR Volunteer", {"user": user or frappe.session.user}, "name")


def tree_has_permission(doc, ptype=None, user=None, debug=False):
	"""has_permission hook: volunteers read every tree but change only their own.
	(Frappe v16 treats any falsy return, None included, as "denied", so allow explicitly with True.)"""
	if ptype in (None, "read", "print", "report", "select", "email", "share", "export") or not volunteer_only(user):
		return True
	mine = my_volunteer(user)
	return bool(mine and doc.owner_volunteer_id == mine)


def check_tree_changes(doc):
	"""Called from HR Tree.validate: a volunteer may change only the care fields of their own tree."""
	if frappe.flags.in_import or frappe.flags.in_patch or not volunteer_only() or doc.is_new():
		return
	before = doc.get_doc_before_save()
	if not before:
		return
	gps_pending = not (flt(before.gps_lat) and flt(before.gps_lng))
	allowed = TREE_FIELDS_FOR_VOLUNTEERS | (GPS_FIELDS if gps_pending else set())
	for df in doc.meta.fields:
		if df.fieldtype in frappe.model.no_value_fields or df.read_only or df.fieldname in allowed:
			continue
		if (doc.get(df.fieldname) or None) != (before.get(df.fieldname) or None):
			frappe.throw(_("Only an admin can change “{0}”. Please ask an admin.").format(_(df.label)),
			             frappe.PermissionError)


def check_care_log(doc):
	"""Called from HR Care Log.validate: a volunteer logs only for their own trees, as themselves."""
	if frappe.flags.in_import or frappe.flags.in_patch or not volunteer_only():
		return
	mine = my_volunteer()
	if not mine or frappe.db.get_value("HR Tree", doc.tree, "owner_volunteer_id") != mine:
		frappe.throw(_("Tree {0} is not assigned to you. You can log care only for your own trees.").format(doc.tree),
		             frappe.PermissionError)
	doc.volunteer = mine


def boot_session(bootinfo):
	"""Tell the Desk who the volunteer is (used by the HR Tree list's "My trees" filter)."""
	if frappe.session.user != "Guest":
		bootinfo.hr_volunteer = my_volunteer()
		bootinfo.hr_is_admin = api._is_admin()
		# where the bare /desk ("Desktop") should go: the person's own Hasiru Ratha workspace
		bootinfo.hr_home = ADMIN_HOME if bootinfo.hr_is_admin else (VOLUNTEER_HOME if volunteer_only() else None)


def set_volunteer_home(doc, method=None):
	"""User.validate: volunteers open the Desk on their own workspace."""
	roles = {r.role for r in doc.get("roles") or []}
	if api.VOLUNTEER_ROLE in roles and not (api.PRIVILEGED & roles) and not doc.default_workspace \
	        and frappe.db.exists("Workspace", VOLUNTEER_WORKSPACE):
		doc.default_workspace = VOLUNTEER_WORKSPACE
