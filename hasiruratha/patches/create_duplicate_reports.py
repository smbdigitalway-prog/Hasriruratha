# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: a Duplicate Report for every site already waiting for review, and the Duplicate section of the admin workspace."""
import json
import os

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"
CARDS = ("Open Duplicate Reports", "Deleted Sites")


def execute():
	from hasiruratha.hasiruratha.doctype.hr_duplicate_report.hr_duplicate_report import create_for_site

	for name in frappe.get_all("HR Site", {"status": "Needs Review", "possible_duplicate_of": ["is", "set"]}, pluck="name"):
		create_for_site(frappe.get_doc("HR Site", name))
	_workspace()


def _workspace():
	from frappe.modules.import_file import import_file_by_path

	base = frappe.get_app_path("hasiruratha", "hasiruratha", "number_card")
	for slug in ("open_duplicate_reports", "deleted_sites"):
		path = os.path.join(base, slug, slug + ".json")
		if os.path.exists(path):
			import_file_by_path(path, force=True)
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	if any(s.link_to == "HR Duplicate Report" for s in ws.shortcuts):
		return                                  # already added; later edits stay
	for c in CARDS:
		if frappe.db.exists("Number Card", c):
			ws.append("number_cards", {"number_card_name": c, "label": c})
	shortcuts = [
		{"label": "Duplicate Reports", "type": "DocType", "link_to": "HR Duplicate Report", "doc_view": "List", "color": "Orange",
		 "stats_filter": json.dumps({"status": "Pending Review"})},
		{"label": "Deleted Sites", "type": "DocType", "link_to": "HR Deleted Site", "doc_view": "List", "color": "Red"},
	]
	for s in shortcuts:
		ws.append("shortcuts", s)
	blocks = json.loads(ws.content or "[]")
	new = [{"id": random_string(10), "type": "number_card", "data": {"number_card_name": c, "col": 4}} for c in CARDS
	       if frappe.db.exists("Number Card", c)]
	new += [{"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": s["label"], "col": 3}} for s in shortcuts]
	at = next((i + 1 for i, b in enumerate(blocks) if b.get("type") == "header" and "duplicate" in b["data"].get("text", "").lower()), None)
	if at is None:                              # no such heading: add one at the end
		new.insert(0, {"id": random_string(10), "type": "header", "data": {"text": '<span class="h4">Duplicate detection &amp; review</span>', "col": 12}})
		at = len(blocks)
	ws.content = json.dumps(blocks[:at] + new + blocks[at:])
	ws.flags.ignore_permissions = True
	ws.save()
