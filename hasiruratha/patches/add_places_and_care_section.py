# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: a "Places & care" section in the admin workspace (care log, trees waiting for GPS, and the
Area / Road / Landmark / Route / Species lists with their unverified entries)."""
import json

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"
SHORTCUTS = [
	{"label": "Care Log", "type": "DocType", "link_to": "HR Care Log", "doc_view": "List", "color": "Blue"},
	{"label": "Trees waiting for GPS", "type": "DocType", "link_to": "HR Tree", "doc_view": "List", "color": "Orange",
	 "stats_filter": json.dumps({"gps_status": "Pending"})},
	{"label": "Areas", "type": "DocType", "link_to": "HR Area", "doc_view": "List", "color": "Grey",
	 "stats_filter": json.dumps({"verified": 0})},
	{"label": "Roads", "type": "DocType", "link_to": "HR Road", "doc_view": "List", "color": "Grey",
	 "stats_filter": json.dumps({"verified": 0})},
	{"label": "Landmarks", "type": "DocType", "link_to": "HR Landmark", "doc_view": "List", "color": "Grey",
	 "stats_filter": json.dumps({"verified": 0})},
	{"label": "Watering Routes", "type": "DocType", "link_to": "HR Route", "doc_view": "List", "color": "Grey"},
	{"label": "Tree Species", "type": "DocType", "link_to": "HR Species", "doc_view": "List", "color": "Green",
	 "stats_filter": json.dumps({"verified": 0})},
]


def execute():
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	if any(s.link_to == "HR Care Log" for s in ws.shortcuts):
		return
	for s in SHORTCUTS:
		ws.append("shortcuts", s)
	blocks = json.loads(ws.content or "[]")
	blocks.append({"id": random_string(10), "type": "header",
	               "data": {"text": '<span class="h4">Places &amp; care</span>', "col": 12}})
	blocks += [{"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": s["label"], "col": 3}} for s in SHORTCUTS]
	ws.content = json.dumps(blocks)
	ws.flags.ignore_permissions = True
	ws.save()
