# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: admins now land in the Desk workspace, so give them a shortcut back to the phone app
(/hasiruratha) and point the requests map shortcut at the Frappe v16 /desk address."""
import json

import frappe
from frappe.utils import random_string

WS = "hasiru_ratha_admin"


def execute():
	if not frappe.db.exists("Workspace", WS):
		return
	ws = frappe.get_doc("Workspace", WS)
	for s in ws.shortcuts:
		if s.type == "URL" and (s.url or "").startswith("/app/hr-request"):
			s.url = s.url.replace("/app/", "/desk/", 1)
	if not any(s.type == "URL" and s.url == "/hasiruratha" for s in ws.shortcuts):
		ws.append("shortcuts", {"label": "Field App (phone)", "type": "URL", "url": "/hasiruratha"})
		blocks = json.loads(ws.content or "[]")
		after = max((i for i, b in enumerate(blocks) if b.get("type") == "shortcut"
		             and b.get("data", {}).get("shortcut_name") == "Requests Map"), default=len(blocks) - 1)
		blocks.insert(after + 1, {"id": random_string(10), "type": "shortcut",
		                          "data": {"shortcut_name": "Field App (phone)", "col": 3}})
		ws.content = json.dumps(blocks)
	ws.flags.ignore_permissions = True
	ws.save()
