# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: Events, QR labels, impact number cards and the new Kanban boards in the admin workspace."""
import json
import os

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"
CARDS = ("Trees Planted (all)", "Volunteer Hours", "Tree Guards Installed", "Tree Guards Removed", "Requests Completed", "Upcoming Events")


def execute():
	from frappe.modules.import_file import import_file_by_path

	from hasiruratha.boards import BOARDS, ensure_boards

	ensure_boards()
	base = frappe.get_app_path("hasiruratha", "hasiruratha", "number_card")
	for slug in ("trees_planted_total", "volunteer_hours", "guards_installed", "guards_removed", "requests_completed", "upcoming_events"):
		path = os.path.join(base, slug, slug + ".json")
		if os.path.exists(path):
			import_file_by_path(path, force=True)
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	have = {s.label for s in ws.shortcuts}
	have_cards = {c.number_card_name for c in ws.number_cards}
	new_blocks = []
	for c in CARDS:
		if frappe.db.exists("Number Card", c) and c not in have_cards:
			ws.append("number_cards", {"number_card_name": c, "label": c})
			new_blocks.append({"id": random_string(10), "type": "number_card", "data": {"number_card_name": c, "col": 4}})
	items = [("Events", dict(type="DocType", link_to="HR Event", doc_view="List", color="Green")),
	         ("Event Subscriptions", dict(type="DocType", link_to="HR Event Subscription", doc_view="List", color="Blue")),
	         ("QR labels (pick spots)", dict(type="DocType", link_to="HR Site", doc_view="List", color="Grey")),
	         ("Impact dashboard", dict(type="URL", url="/impact")),
	         ("Public events page", dict(type="URL", url="/events"))]
	for dt in ("HR Event", "HR Event Subscription"):
		c = BOARDS[dt]
		if frappe.db.exists("Kanban Board", c["board"]):
			items.append((c["label"] + " board", dict(type="DocType", link_to=dt, doc_view="Kanban", kanban_board=c["board"])))
	for label, kw in items:
		if label not in have:
			ws.append("shortcuts", {"label": label, **kw})
			new_blocks.append({"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": label, "col": 3}})
	if not new_blocks:
		return
	blocks = json.loads(ws.content or "[]")
	blocks.append({"id": random_string(10), "type": "header", "data": {"text": '<span class="h4">Impact, events &amp; QR</span>', "col": 12}})
	ws.content = json.dumps(blocks + new_blocks)
	ws.flags.ignore_permissions = True
	ws.save()
