# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Kanban boards for everything in the admin workspace.

One board per DocType that has a status, one column per status. The same list is used twice:
  * ensure_boards()   -> Frappe's own Kanban Board records (Desk: <DocType> -> Kanban, workspace shortcuts)
  * console_board()   -> the board view inside the Hasiru Ratha Console page (drag a card to change status)

Columns that carry a decision (duplicates, merges) are LOCKED: cards cannot be dragged in or out, the admin
uses the card's buttons so the trees, visits and the duplicate trail are handled properly.
"""
import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

# doctype: board name, status field, card title field, card image field, subtitle fields, locked columns
BOARDS = {
	"HR Request": dict(board="HR Requests", field="status", title="title", image="photo",
	                   sub=["request_type", "area"], label="Citizen requests"),
	"HR Citizen Planting": dict(board="HR Citizen Plantings", field="status", title="road", image="photo",
	                            sub=["spot_or_stretch", "area"], label="Citizen plantings"),
	"HR Citizen Report": dict(board="HR Citizen Reports", field="status", title="issue_type", image="photo",
	                          sub=["area", "assigned_volunteer"], label="Citizen reports"),
	"HR Tree Report": dict(board="HR Tree Reports", field="status", title="report_id", image="photo_url",
	                       sub=["issue_type", "area", "assigned_volunteer_name"], label="Tree reports"),
	"HR Volunteer Request": dict(board="HR Volunteer Requests", field="status", title="full_name", image=None,
	                             sub=["area", "email"], label="Volunteer requests"),
	"HR Application": dict(board="HR Applications", field="status", title="volunteer", image=None,
	                       sub=["application_type", "tree"], label="Volunteer applications"),
	"HR Site": dict(board="HR Sites", field="status", title="site_name", image="photo_url",
	                sub=["road", "area"], locked=["Needs Review", "Merged"], label="Sites"),
	"HR Tree": dict(board="HR Trees", field="status", title="tree_id", image="photo_url",
	                sub=["species", "site_id"], locked=["Merged"], label="Trees"),
	"HR Duplicate Report": dict(board="HR Duplicate Reports", field="status", title="site", image="picture_of_tree",
	                            sub=["possible_duplicate_of_site", "area"],
	                            locked=["Pending Review", "Kept as New", "Merged", "Deleted", "Restored"],
	                            label="Duplicate reports"),
	"HR Diary Entry": dict(board="HR Diary Entries", field="status", title="title", image="photo",
	                       sub=["activity", "area"], label="Green Diary"),
	"HR Event": dict(board="HR Events", field="status", title="title", image="photo",
	                 sub=["event_date", "area"], label="Events"),
	"HR Event Subscription": dict(board="HR Event Subscriptions", field="status", title="full_name", image=None,
	                              sub=["event", "mobile"], label="Event subscriptions"),
	"HR Internship Application": dict(board="HR Internship Applications", field="status", title="full_name", image=None,
	                                  sub=["area", "duration"], label="Internships"),
}


def _exists(doctype):
	return bool(frappe.db.exists("DocType", doctype))


def ensure_boards():
	"""Create (once) a Frappe Kanban Board for every DocType above. Idempotent; never touches an existing board's columns."""
	from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board

	meta_kb = frappe.get_meta("Kanban Board")
	for dt, c in BOARDS.items():
		if not _exists(dt) or not frappe.get_meta(dt).has_field(c["field"]):
			continue
		if not frappe.db.exists("Kanban Board", c["board"]):
			quick_kanban_board(dt, c["board"], c["field"])
		# Frappe v16 boards have their own card title / image settings
		want = {"title_field": c["title"], "image_field": c["image"], "use_kanban_v2": 1}
		vals = {k: v for k, v in want.items() if v and meta_kb.has_field(k) and frappe.db.get_value("Kanban Board", c["board"], k) != v}
		if vals:
			frappe.db.set_value("Kanban Board", c["board"], vals)


def _fields(dt, wanted):
	meta = frappe.get_meta(dt)
	return [f for f in wanted if f and meta.has_field(f)]


@frappe.whitelist()
def console_boards():
	"""Which boards the Console can show, with how many open cards each has (for the tab badges)."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin

	_require_admin()
	out = []
	for dt, c in BOARDS.items():
		if not _exists(dt):
			continue
		out.append({"doctype": dt, "label": _(c["label"]), "total": frappe.db.count(dt)})
	return out


@frappe.whitelist()
def console_board(doctype, q=None, limit=60):
	"""Columns + cards for one board. Newest first, `limit` cards per column."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin

	_require_admin()
	c = BOARDS.get(doctype)
	if not c or not _exists(doctype):
		frappe.throw(_("No board for {0}").format(doctype))
	meta = frappe.get_meta(doctype)
	sf = c["field"]
	statuses = [s for s in (meta.get_field(sf).options or "").split("\n") if s]
	title, image = c["title"], c["image"] if meta.has_field(c["image"] or "") else None
	sub = _fields(doctype, c["sub"])
	fields = list({"name", "creation", sf, title, *sub, *([image] if image else [])})
	locked = set(c.get("locked") or [])
	cols = []
	text = (q or "").lower().strip()
	for st in statuses:
		rows = frappe.get_all(doctype, {sf: st}, fields, order_by="modified desc", limit_page_length=500)
		if text:
			rows = [r for r in rows if text in " ".join(str(r.get(k) or "") for k in (title, *sub, "name")).lower()]
		cards = [{
			"name": r.name, "title": r.get(title) or r.name,
			"sub": [str(r.get(k)) for k in sub if r.get(k)], "image": r.get(image) if image else None,
			"age": max(date_diff(nowdate(), getdate(r.creation)), 0),
		} for r in rows[: int(limit)]]
		cols.append({"status": st, "count": len(rows), "cards": cards, "locked": st in locked})
	return {"doctype": doctype, "columns": cols, "route": frappe.scrub(doctype).replace("_", "-")}


@frappe.whitelist(methods=["POST"])
def move_card(doctype, name, status):
	"""Drag-and-drop on the Console board: change the status of one record."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin

	_require_admin()
	c = BOARDS.get(doctype)
	if not c:
		frappe.throw(_("No board for {0}").format(doctype))
	locked = set(c.get("locked") or [])
	cur = frappe.db.get_value(doctype, name, c["field"])
	if status in locked or cur in locked:
		frappe.throw(_("Use the buttons on the card for this one, so trees and the duplicate trail are handled."))
	doc = frappe.get_doc(doctype, name)
	doc.set(c["field"], status)
	doc.save(ignore_permissions=True)
	return {"success": True}
