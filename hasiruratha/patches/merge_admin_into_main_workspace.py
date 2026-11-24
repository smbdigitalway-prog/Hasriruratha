# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: the important parts of the admin workspace move into the main "Hasiru Ratha" workspace (sir's), so there is one home.

Added only if missing: the admin's own charts, the cards that need attention (duplicates, reviews, hours, guards ...), the
Dashboard, the Console, duplicate / deleted-site / request shortcuts and a Kanban section with every board.
Frappe shows a shortcut or card only to people who may open its list, so volunteers never see admin-only items.
The admin workspace itself is left as it is."""
import json

import frappe
from frappe.utils import random_string

from hasiruratha.permissions import ADMIN_WORKSPACE, VOLUNTEER_WORKSPACE

CARDS = ["Open Duplicate Reports", "Requests Needing Review", "Sites Needing Review", "Citizen Reports To Review",
         "Citizen Plantings To Review", "Volunteer Applications Pending", "Open Tree Reports", "Volunteer Hours",
         "Tree Guards Installed", "Tree Guards Removed", "Requests Completed", "Upcoming Events"]
OUR_CHARTS = ["Trees by Status", "Requests by Status", "Citizen Reports by Issue", "Care Activity",
              "Duplicate Reports by Status", "Spots and Stretches by Zone", "Requests per Month"]
SHORTCUTS = [
	("Admin", [
		("Console", dict(type="Page", link_to="hr-console", color="Green")),
		("Dashboard", dict(type="Dashboard", link_to="Hasiru Ratha", color="Blue")),
		("Duplicate Reports", dict(type="DocType", link_to="HR Duplicate Report", doc_view="List", color="Red",
		                           stats_filter=json.dumps({"status": "Pending Review"}))),
		("Deleted Sites", dict(type="DocType", link_to="HR Deleted Site", doc_view="List", color="Red")),
		("Requests", dict(type="DocType", link_to="HR Request", doc_view="List", color="Blue")),
		("Citizen Plantings", dict(type="DocType", link_to="HR Citizen Planting", doc_view="List", color="Green")),
		("Citizen Reports", dict(type="DocType", link_to="HR Citizen Report", doc_view="List", color="Orange")),
		("Volunteer Requests", dict(type="DocType", link_to="HR Volunteer Request", doc_view="List", color="Blue")),
		("Tree Reports", dict(type="DocType", link_to="HR Tree Report", doc_view="List", color="Orange")),
		("Volunteer Applications", dict(type="DocType", link_to="HR Application", doc_view="List", color="Blue")),
		("Events", dict(type="DocType", link_to="HR Event", doc_view="List", color="Green")),
		("Impact", dict(type="URL", url="/impact", color="Green")),
	]),
]


def _header(text):
	return {"id": random_string(10), "type": "header", "data": {"text": '<span class="h4">%s</span>' % text, "col": 12}}


def _sync_standard_files():
	"""Frappe loads an app's number cards, charts and dashboards after patches have run, so load ours now."""
	import glob
	import os

	from frappe.modules.import_file import import_file_by_path

	base = frappe.get_app_path("hasiruratha", "hasiruratha")
	for folder in ("number_card", "dashboard_chart", "dashboard"):   # cards and charts first, the Dashboard uses them
		for path in sorted(glob.glob(os.path.join(base, folder, "*", "*.json"))):
			import_file_by_path(path, force=True)


def execute():
	from hasiruratha.boards import BOARDS

	_sync_standard_files()

	if not frappe.db.exists("Workspace", VOLUNTEER_WORKSPACE):
		return
	ws = frappe.get_doc("Workspace", VOLUNTEER_WORKSPACE)
	adm = frappe.get_doc("Workspace", ADMIN_WORKSPACE) if frappe.db.exists("Workspace", ADMIN_WORKSPACE) else None

	have_roles = {r.role for r in ws.roles}
	for role in ("HR Admin", "System Manager"):
		if role not in have_roles:
			ws.append("roles", {"role": role})

	have_cards = {c.number_card_name for c in ws.number_cards}
	have_charts = {c.chart_name for c in ws.charts}
	have_short = {s.label for s in ws.shortcuts}
	blocks = []

	# charts: everything built on the admin workspace, then ours
	chart_names = [c.chart_name for c in (adm.charts if adm else [])] + OUR_CHARTS
	new_charts = [c for c in dict.fromkeys(chart_names) if c not in have_charts and frappe.db.exists("Dashboard Chart", c)]
	if new_charts:
		blocks.append(_header("Charts"))
		for c in new_charts:
			ws.append("charts", {"chart_name": c, "label": c})
			blocks.append({"id": random_string(10), "type": "chart", "data": {"chart_name": c, "col": 6}})

	new_cards = [c for c in CARDS if c not in have_cards and frappe.db.exists("Number Card", c)]
	if new_cards:
		blocks.append(_header("Needs attention"))
		for c in new_cards:
			ws.append("number_cards", {"number_card_name": c, "label": c})
			blocks.append({"id": random_string(10), "type": "number_card", "data": {"number_card_name": c, "col": 3}})

	for title, items in SHORTCUTS:
		todo = [(label, kw) for label, kw in items if label not in have_short
		        and (kw.get("type") != "DocType" or frappe.db.exists("DocType", kw["link_to"]))
		        and (kw.get("type") != "Dashboard" or frappe.db.exists("Dashboard", kw["link_to"]))]
		if todo:
			blocks.append(_header(title))
		for label, kw in todo:
			ws.append("shortcuts", {"label": label, **kw})
			blocks.append({"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})

	boards = [(dt, c) for dt, c in BOARDS.items() if frappe.db.exists("Kanban Board", c["board"]) and (c["label"] + " board") not in have_short]
	if boards:
		blocks.append(_header("Kanban boards"))
		for dt, c in boards:
			label = c["label"] + " board"
			ws.append("shortcuts", {"label": label, "type": "DocType", "link_to": dt, "doc_view": "Kanban", "kanban_board": c["board"]})
			blocks.append({"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})

	if not blocks:
		return
	ws.content = json.dumps(json.loads(ws.content or "[]") + blocks)
	ws.flags.ignore_permissions = True
	ws.flags.ignore_links = True
	ws.save()
