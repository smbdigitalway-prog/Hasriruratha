# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: volunteers move from the old phone app (/hasiruratha) to the Frappe Desk.

* role HR Volunteer gets Desk access; existing volunteer accounts become System Users that open the
  new "Hasiru Ratha" volunteer workspace
* the admin workspace is limited to admins and loses its "Field App (phone)" shortcut
"""
import json
import os

import frappe
from frappe.utils import random_string

from hasiruratha import api
from hasiruratha.permissions import ADMIN_WORKSPACE, VOLUNTEER_WORKSPACE

CARDS = ["Trees Planted", "Trees Waiting For GPS", "Active Volunteers", "Open Citizen Requests"]
SECTIONS = [
	("In the field (phone)", [
		{"label": "My Trees & Care Log", "type": "URL", "url": "/my-trees", "color": "Green"},
		{"label": "GPS Tagging", "type": "URL", "url": "/gps-tagging", "color": "Orange"},
		{"label": "Raise a Request", "type": "URL", "url": "/request", "color": "Blue"},
		{"label": "Trees Map", "type": "URL", "url": "/trees", "color": "Green"},
		{"label": "Add to Green Diary", "type": "URL", "url": "/green-diary-new", "color": "Purple"},
	]),
	("Organisation", [
		{"label": "Trees", "type": "DocType", "link_to": "HR Tree", "doc_view": "List", "color": "Green"},
		{"label": "Spots & Stretches", "type": "DocType", "link_to": "HR Site", "doc_view": "List", "color": "Green"},
		{"label": "Care Log", "type": "DocType", "link_to": "HR Care Log", "doc_view": "List", "color": "Blue"},
		{"label": "Citizen Requests", "type": "DocType", "link_to": "HR Request", "doc_view": "List", "color": "Blue",
		 "stats_filter": json.dumps({"status": ["not in", ["Completed", "Rejected", "Duplicate"]]})},
		{"label": "Volunteers", "type": "DocType", "link_to": "HR Volunteer", "doc_view": "List", "color": "Grey"},
		{"label": "Zones", "type": "DocType", "link_to": "HR Zone", "doc_view": "List", "color": "Grey"},
		{"label": "Visits", "type": "DocType", "link_to": "HR Visit", "doc_view": "List", "color": "Grey"},
		{"label": "Green Diary", "type": "DocType", "link_to": "HR Diary Entry", "doc_view": "List", "color": "Purple"},
	]),
	("Places", [
		{"label": "Areas", "type": "DocType", "link_to": "HR Area", "doc_view": "List", "color": "Grey"},
		{"label": "Roads", "type": "DocType", "link_to": "HR Road", "doc_view": "List", "color": "Grey"},
		{"label": "Landmarks", "type": "DocType", "link_to": "HR Landmark", "doc_view": "List", "color": "Grey"},
		{"label": "Watering Routes", "type": "DocType", "link_to": "HR Route", "doc_view": "List", "color": "Grey"},
		{"label": "Tree Species", "type": "DocType", "link_to": "HR Species", "doc_view": "List", "color": "Green"},
	]),
]


def execute():
	_role_desk_access()
	_sync_cards()
	_volunteer_workspace()
	_admin_workspace()
	_switch_volunteer_accounts()


def _role_desk_access():
	if frappe.db.exists("Role", api.VOLUNTEER_ROLE):
		frappe.db.set_value("Role", api.VOLUNTEER_ROLE, "desk_access", 1)
		frappe.clear_cache()


def _sync_cards():
	# Frappe syncs an app's number cards after patches run, so load ours now
	from frappe.modules.import_file import import_file_by_path

	base = frappe.get_app_path("hasiruratha", "hasiruratha", "number_card")
	for name in CARDS:
		slug = frappe.scrub(name)
		path = os.path.join(base, slug, slug + ".json")
		if os.path.exists(path):
			import_file_by_path(path, force=True)


def _volunteer_workspace():
	if frappe.db.exists("Workspace", VOLUNTEER_WORKSPACE):
		return
	ws = frappe.new_doc("Workspace")
	ws.update({"name": VOLUNTEER_WORKSPACE, "label": VOLUNTEER_WORKSPACE, "title": "Hasiru Ratha",
	           "module": "Hasiruratha", "public": 1, "icon": "getting-started", "sequence_id": 1})
	ws.append("roles", {"role": api.VOLUNTEER_ROLE})
	blocks = [{"id": random_string(10), "type": "header",
	           "data": {"text": '<span class="h4">Welcome to Hasiru Ratha</span>', "col": 12}}]
	for card in CARDS:
		if frappe.db.exists("Number Card", card):
			ws.append("number_cards", {"number_card_name": card, "label": card})
			blocks.append({"id": random_string(10), "type": "number_card", "data": {"number_card_name": card, "col": 3}})
	for title, shortcuts in SECTIONS:
		blocks.append({"id": random_string(10), "type": "header",
		               "data": {"text": '<span class="h4">%s</span>' % frappe.utils.escape_html(title), "col": 12}})
		for s in shortcuts:
			ws.append("shortcuts", s)
			blocks.append({"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": s["label"], "col": 3}})
	ws.content = json.dumps(blocks)
	ws.flags.ignore_permissions = True
	ws.flags.ignore_links = True
	ws.insert()


def _admin_workspace():
	if not frappe.db.exists("Workspace", ADMIN_WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", ADMIN_WORKSPACE)
	ws.shortcuts = [s for s in ws.shortcuts if not (s.type == "URL" and s.url == "/hasiruratha")]
	blocks = [b for b in json.loads(ws.content or "[]") if b.get("data", {}).get("shortcut_name") != "Field App (phone)"]
	ws.content = json.dumps(blocks)
	if not ws.roles:
		for role in ("HR Admin", "System Manager"):
			ws.append("roles", {"role": role})
	ws.flags.ignore_permissions = True
	ws.save()


def _switch_volunteer_accounts():
	users = frappe.get_all("Has Role", {"role": api.VOLUNTEER_ROLE, "parenttype": "User"}, pluck="parent", distinct=True)
	for name in users:
		user = frappe.get_doc("User", name)
		if not user.enabled or api.PRIVILEGED & {r.role for r in user.roles}:
			continue
		user.flags.ignore_permissions = True
		user.flags.no_welcome_mail = True
		try:
			user.save()    # recomputes user_type (System User) and sets the volunteer workspace
		except Exception:
			frappe.log_error(title="Volunteer account not switched to the Desk: " + name)
