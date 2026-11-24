"""Rebuild the citizen website page, remove the empty Dashboard, surface every Kanban board.

Safe to run more than once. Run with:  bench --site <site> migrate
or directly:  bench --site <site> execute hasiruratha.patches.v1_0.rebuild_citizen_website.execute
"""
import json
import os
import random
import string

import frappe

APP = "hasiruratha"          # python package name of the app (folder that holds hooks.py)
PAGE_ROUTE = "hasiru-ratha"  # route of the existing Web Page
IMG_BASE = f"/assets/{APP}/images/site"

# Web Forms are looked up by the DocType they save into; fallbacks are used if none is found.
FORM_FOR = {
	"__PLANT_URL__": ("HR Citizen Planting", "/plant-a-tree"),
	"__REPORT_URL__": ("HR Citizen Report", "/report-a-tree"),
	"__VOLUNTEER_URL__": ("HR Volunteer Request", "/become-a-volunteer"),
	"__INTERNSHIP_URL__": ("HR Internship Application", "/internship"),
}
ADMIN_WORKSPACES = ["Hasiru Ratha Admin", "Hasiru Ratha Console"]


# ---------- pure helpers (no frappe calls, unit-testable) ----------

def render_page(template: str, urls: dict) -> str:
	out = template.replace("__IMG__", IMG_BASE)
	for token, value in urls.items():
		out = out.replace(token, value)
	return out


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
	rebuild_web_page()
	clean_workspaces()


def web_form_route(doctype, fallback):
	route = frappe.db.get_value("Web Form", {"doc_type": doctype, "published": 1}, "route")
	return "/" + route.strip("/") if route else fallback


def rebuild_web_page():
	name = frappe.db.get_value("Web Page", {"route": PAGE_ROUTE}, "name")
	if not name:
		print(f"[hasiruratha] Web Page with route '{PAGE_ROUTE}' not found: creating it")
		doc = frappe.new_doc("Web Page")
		doc.title = "Hasiru Ratha"
		doc.route = PAGE_ROUTE
		doc.published = 1
	else:
		doc = frappe.get_doc("Web Page", name)
		backup = frappe.get_site_path("private", "files", f"web_page_{name}_before_rebuild.json")
		with open(backup, "w") as f:
			json.dump(doc.as_dict(), f, default=str, indent=1)
		print(f"[hasiruratha] old page backed up to {backup}")

	template_path = frappe.get_app_path(APP, "website_content", "home.html")
	with open(template_path, encoding="utf-8") as f:
		template = f.read()

	urls = {t: web_form_route(dt, fb) for t, (dt, fb) in FORM_FOR.items()}
	urls.update({"__LOGIN_URL__": "/login", "__SIGNUP_URL__": "/login#signup"})

	doc.content_type = "HTML"
	doc.main_section_html = render_page(template, urls)
	doc.full_width = 1
	doc.show_title = 0
	doc.published = 1
	if doc.meta.has_field("add_breadcrumbs"):
		doc.add_breadcrumbs = 0
	doc.save(ignore_permissions=True)
	print("[hasiruratha] page rebuilt; links used:", urls)


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
