# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: a workspace shortcut to /gps-tagging, where imported trees (GPS pending) get their location."""
import json

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"
LABEL = "GPS Tagging (phone)"


def execute():
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	if any(s.type == "URL" and s.url == "/gps-tagging" for s in ws.shortcuts):
		return
	ws.append("shortcuts", {"label": LABEL, "type": "URL", "url": "/gps-tagging"})
	blocks = json.loads(ws.content or "[]")
	after = max((i for i, b in enumerate(blocks) if b.get("type") == "shortcut"
	             and b.get("data", {}).get("shortcut_name") == "Field App (phone)"), default=len(blocks) - 1)
	blocks.insert(after + 1, {"id": random_string(10), "type": "shortcut", "data": {"shortcut_name": LABEL, "col": 3}})
	ws.content = json.dumps(blocks)
	ws.flags.ignore_permissions = True
	ws.save()
