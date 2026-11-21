# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: Kanban boards for everything in the admin workspace, the Console and the missing lists.

Adds to "Hasiru Ratha Admin" (only what is missing, by link; later edits stay):
  * Console shortcut (Page hr-console)
  * a "Boards" section: one Kanban shortcut per board
  * "Delete duplicates" (Duplicate Reports, Pending Review, tick rows -> Actions -> Delete duplicate site(s))
  * Green Diary, Internship Applications, Citizen Plantings / Reports / Volunteer Requests if not there yet
"""
import json

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"


def execute():
	from hasiruratha.boards import BOARDS, ensure_boards

	ensure_boards()
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	have = {(s.link_to or s.url, s.doc_view or "", s.kanban_board or "") for s in ws.shortcuts}
	have_label = {s.label for s in ws.shortcuts}
	added_blocks = []

	def add(section, label, **kw):
		key = (kw.get("link_to") or kw.get("url"), kw.get("doc_view", ""), kw.get("kanban_board", ""))
		if key in have or label in have_label:
			return
		ws.append("shortcuts", {"label": label, **kw})
		have.add(key)
		have_label.add(label)
		added_blocks.append((section, label))

	add("Console", "Console", type="Page", link_to="hr-console", color="Green")
	add("Console", "Delete duplicates", type="DocType", link_to="HR Duplicate Report", doc_view="List", color="Red",
	    stats_filter=json.dumps({"status": "Pending Review"}))
	for dt, label, color in (("HR Diary Entry", "Green Diary", "Green"), ("HR Internship Application", "Internship Applications", "Blue"),
	                         ("HR Citizen Planting", "Citizen Plantings", "Green"), ("HR Citizen Report", "Citizen Reports", "Orange"),
	                         ("HR Volunteer Request", "Volunteer Requests", "Blue")):
		if frappe.db.exists("DocType", dt) and not any(s.link_to == dt for s in ws.shortcuts):
			add("Lists", label, type="DocType", link_to=dt, doc_view="List", color=color)
	for dt, c in BOARDS.items():
		if frappe.db.exists("Kanban Board", c["board"]):
			add("Boards", c["label"] + " board", type="DocType", link_to=dt, doc_view="Kanban", kanban_board=c["board"])

	if not added_blocks:
		return
	blocks = json.loads(ws.content or "[]")
	for section, title in (("Console", "Console &amp; duplicates"), ("Lists", "More lists"), ("Boards", "Boards")):
		items = [lbl for sec, lbl in added_blocks if sec == section]
		if not items:
			continue
		blocks.append({"id": random_string(10), "type": "header", "data": {"text": f'<span class="h4">{title}</span>', "col": 12}})
		blocks += [{"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": lbl, "col": 3}} for lbl in items]
	ws.content = json.dumps(blocks)
	ws.flags.ignore_permissions = True
	ws.save()
