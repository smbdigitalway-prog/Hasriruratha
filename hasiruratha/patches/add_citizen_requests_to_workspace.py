# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: add a "Citizen requests" section to the admin workspace (number cards + shortcuts).
The workspace is kept on the site; this only adds, and never runs again, so later edits stay."""
import json

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"
CARDS = ("Open Citizen Requests", "Requests Needing Review")


def execute():
	from hasiruratha.install import ensure_request_kanban

	ensure_request_kanban()
	_sync_cards()
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	if any(s.link_to == "HR Request" for s in ws.shortcuts):
		return
	for c in CARDS:
		if frappe.db.exists("Number Card", c):
			ws.append("number_cards", {"number_card_name": c, "label": c})
	shortcuts = [
		{"label": "Citizen Requests", "type": "DocType", "link_to": "HR Request", "doc_view": "List", "color": "Green",
		 "stats_filter": json.dumps({"status": ["in", ["Received", "Under review", "Accepted", "Scheduled"]]})},
		{"label": "Requests Board", "type": "DocType", "link_to": "HR Request", "doc_view": "Kanban", "kanban_board": "HR Requests"},
		{"label": "Requests Map", "type": "URL", "url": "/app/hr-request/view/map"},
	]
	for s in shortcuts:
		ws.append("shortcuts", s)
	blocks = json.loads(ws.content or "[]")
	new = [{"id": random_string(10), "type": "header", "data": {"text": '<span class="h4">Citizen requests</span>', "col": 12}}]
	new += [{"id": random_string(10), "type": "number_card", "data": {"number_card_name": c, "col": 4}} for c in CARDS
	        if frappe.db.exists("Number Card", c)]
	new += [{"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": s["label"], "col": 3}} for s in shortcuts]
	at = 1 if blocks and blocks[0].get("type") == "header" else 0       # just under the welcome title
	ws.content = json.dumps(blocks[:at] + new + blocks[at:])
	ws.flags.ignore_permissions = True
	ws.save()


def _sync_cards():
	# Frappe syncs an app's number cards after patches run, so load ours now
	import os

	from frappe.modules.import_file import import_file_by_path

	base = frappe.get_app_path("hasiruratha", "hasiruratha", "number_card")
	for slug in ("open_citizen_requests", "requests_needing_review"):
		path = os.path.join(base, slug, slug + ".json")
		if os.path.exists(path):
			import_file_by_path(path, force=True)
