"""Remove the empty Dashboard from the Hasiru workspaces and surface every Kanban board.

(The old home-page rebuild was dropped: the page is now built by build_page_blocks.)

Safe to run more than once. Run with:  bench --site <site> migrate
or directly:  bench --site <site> execute hasiruratha.patches.v1_0.rebuild_citizen_website.execute
"""
import json
import os
import random
import string

import frappe

APP = "hasiruratha"          # python package name of the app (folder that holds hooks.py)

ADMIN_WORKSPACES = ["Hasiru Ratha Admin", "Hasiru Ratha Console"]


# ---------- pure helpers (no frappe calls, unit-testable) ----------

def is_dashboard_row(row: dict) -> bool:
	"""True for a Workspace shortcut/link that points at the Frappe 'Dashboard' feature."""
	label = (row.get("label") or "").strip().lower()
	return (
		row.get("type") == "Dashboard"
		or row.get("link_type") == "Dashboard"
		or row.get("link_to") == "Dashboard"
		or row.get("doc_view") == "Dashboard"
		or label == "dashboard"
	)


def strip_blocks(content: str, labels: set) -> str:
	"""Remove shortcut/link blocks for the given labels from a Workspace `content` JSON string."""
	try:
		blocks = json.loads(content or "[]")
	except ValueError:
		return content
	wanted = {x.lower() for x in labels}
	kept = [
		b for b in blocks
		if not (
			b.get("type") == "shortcut"
			and (b.get("data", {}).get("shortcut_name") or "").lower() in wanted
		)
	]
	return json.dumps(kept)


def add_shortcut_blocks(content: str, labels: list) -> str:
	try:
		blocks = json.loads(content or "[]")
	except ValueError:
		return content
	have = {
		(b.get("data", {}).get("shortcut_name") or "").lower()
		for b in blocks if b.get("type") == "shortcut"
	}
	new = [l for l in labels if l.lower() not in have]
	if not new:
		return content
	rid = lambda: "".join(random.choices(string.ascii_letters + string.digits, k=10))
	blocks.append({"id": rid(), "type": "header", "data": {"text": "<span class=\"h4\">Kanban Boards</span>", "col": 12}})
	blocks += [{"id": rid(), "type": "shortcut", "data": {"shortcut_name": l, "col": 3}} for l in new]
	return json.dumps(blocks)


# ---------- frappe steps ----------

def execute():
	clean_workspaces()


def clean_workspaces():
	names = frappe.get_all(
		"Workspace",
		or_filters=[["name", "like", "%Hasiru%"], ["module", "like", "Hasiru%"]],
		pluck="name",
	)
	for ws_name in names:
		ws = frappe.get_doc("Workspace", ws_name)
		removed = set()
		for table in ("shortcuts", "links"):
			rows = ws.get(table) or []
			keep = []
			for r in rows:
				if is_dashboard_row(r.as_dict()):
					removed.add((r.label or "").strip())
				else:
					keep.append(r)
			ws.set(table, keep)
		ws.content = strip_blocks(ws.content, removed | {"Dashboard"})
		ws.save(ignore_permissions=True)
		print(f"[hasiruratha] {ws_name}: removed Dashboard entries {sorted(removed) or 'none found'}")

	# Remove any real Dashboard records created by the app (the list was empty on the site, so usually none).
	for d in frappe.get_all("Dashboard", filters={"module": ["like", "Hasiru%"]}, pluck="name"):
		frappe.delete_doc("Dashboard", d, ignore_permissions=True)
		print(f"[hasiruratha] deleted Dashboard {d}")

	add_kanban_shortcuts([n for n in ADMIN_WORKSPACES if n in names] or names[:1])


def add_kanban_shortcuts(target):
	if not target:
		print("[hasiruratha] no Hasiru workspace found, Kanban shortcuts skipped")
		return
	ws = frappe.get_doc("Workspace", target[0])
	has_board_field = frappe.get_meta("Workspace Shortcut").has_field("kanban_board")
	boards = frappe.get_all("Kanban Board", fields=["name", "reference_doctype"], order_by="reference_doctype")
	boards = [b for b in boards if (b.reference_doctype or "").startswith("HR ")]
	existing = {(r.label or "").lower() for r in ws.shortcuts}
	labels = []
	for b in boards:
		label = f"{b.reference_doctype} Kanban"
		labels.append(label)
		if label.lower() in existing:
			continue
		row = {"label": label, "color": "Grey"}
		if has_board_field:
			row.update({"type": "DocType", "link_to": b.reference_doctype, "doc_view": "Kanban", "kanban_board": b.name})
		else:
			slug = frappe.scrub(b.reference_doctype).replace("_", "-")
			row.update({"type": "URL", "url": f"/app/{slug}/view/kanban/{b.name}"})
		ws.append("shortcuts", row)
	ws.content = add_shortcut_blocks(ws.content, labels)
	ws.save(ignore_permissions=True)
	print(f"[hasiruratha] {ws.name}: {len(labels)} Kanban shortcuts ensured")
