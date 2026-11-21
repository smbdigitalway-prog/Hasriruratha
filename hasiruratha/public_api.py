# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Public (no sign-in) map data for /trees.

Only public details leave the server: spot, road, area, zone, tree type, date planted, age, photo
and whether the tree has a caretaker. Volunteer names, phone numbers and emails are never sent.
Maintenance history is added only for signed-in volunteers and admins.
"""
from datetime import date

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import flt, getdate

from hasiruratha import api

MAX_SPOTS = 400
HIDDEN_STATUS = ("Merged",)


def age_text(planted):
	if not planted:
		return ""
	d = getdate(planted)
	months = (date.today().year - d.year) * 12 + date.today().month - d.month
	if months < 1:
		return "under a month"
	if months < 12:
		return "%d month%s" % (months, "" if months == 1 else "s")
	y, m = divmod(months, 12)
	return "%d yr" % y + (" %d mo" % m if m else "")


def _zone_names():
	return {z.name: z.zone_name for z in frappe.get_all("HR Zone", fields=["name", "zone_name"])}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=600, seconds=300)
def spots(south=None, west=None, north=None, east=None):
	"""Spots inside the visible map box (closest-to-centre first, at most MAX_SPOTS)."""
	s, w, n, e = flt(south), flt(west), flt(north), flt(east)
	if not (s < n and w < e) or (n - s) > 1.5 or (e - w) > 1.5:
		return {"spots": [], "zoom_in": True}
	rows = frappe.get_all(
		"HR Site",
		filters={"gps_lat": ["between", [s, n]], "gps_lng": ["between", [w, e]], "status": ["not in", HIDDEN_STATUS]},
		fields=["name", "site_name", "site_type", "road", "area", "zone_id", "gps_lat", "gps_lng", "tree_count", "photo_url"],
		limit_page_length=0,
	)
	cy, cx = (s + n) / 2, (w + e) / 2
	rows.sort(key=lambda r: (flt(r.gps_lat) - cy) ** 2 + (flt(r.gps_lng) - cx) ** 2)
	more = len(rows) > MAX_SPOTS
	rows = rows[:MAX_SPOTS]
	trees = {}
	if rows:
		for t in frappe.get_all("HR Tree", {"site_id": ["in", [r.name for r in rows]], "status": ["!=", "Merged"]},
		                        ["site_id", "species", "date_planted", "photo_url", "owner_volunteer_id", "caretaker_type"], limit_page_length=0):
			trees.setdefault(t.site_id, []).append(t)
	zones = _zone_names()
	out = []
	for r in rows:
		ts = trees.get(r.name, [])
		planted = min((t.date_planted for t in ts if t.date_planted), default=None)
		species = sorted({(t.species or "").strip() for t in ts if (t.species or "").strip()})
		out.append({
			"id": r.name, "name": r.site_name or r.road or r.name, "type": r.site_type or "spot",
			"lat": flt(r.gps_lat), "lng": flt(r.gps_lng), "road": r.road or "", "area": r.area or "",
			"zone": zones.get(r.zone_id, ""), "trees": len(ts) or (r.tree_count or 0), "species": species[:5],
			"planted": str(planted or ""), "age": age_text(planted),
			"photo": r.photo_url or next((t.photo_url for t in ts if t.photo_url), ""),
			"cared": sum(1 for t in ts if t.owner_volunteer_id or t.caretaker_type),
		})
	return {"spots": out, "more": more}


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=300, seconds=300)
def spot(site_id=None):
	"""One spot with its trees. Volunteers/admins also get the maintenance history."""
	r = frappe.db.get_value("HR Site", site_id, ["name", "site_name", "site_type", "road", "area", "zone_id", "gps_lat",
	                                             "gps_lng", "photo_url", "status", "landmark", "companion_plants"], as_dict=True)
	if not r or r.status in HIDDEN_STATUS:
		return {"found": False}
	trees = []
	species = {}
	for t in frappe.get_all("HR Tree", {"site_id": r.name, "status": ["!=", "Merged"]},
	                        ["name", "species", "date_planted", "photo_url", "condition", "tree_guard", "owner_volunteer_id",
	                         "last_watered", "planting_type", "caretaker_type"],
	                        order_by="position", limit_page_length=200):
		if t.species and t.species not in species:
			species[t.species] = frappe.db.get_value("HR Species", t.species, ["kannada_name", "botanical_name", "description"],
			                                         as_dict=True) or {}
		sp = species.get(t.species) or {}
		trees.append({"id": t.name, "species": t.species or "Not known yet", "planted": str(t.date_planted or ""),
		              "age": age_text(t.date_planted), "photo": t.photo_url or "", "condition": t.condition or "",
		              "guard": t.tree_guard or "", "cared": bool(t.owner_volunteer_id or t.caretaker_type),
		              "last_watered": str(t.last_watered or ""), "planting_type": t.planting_type or "",
		              "kannada": sp.get("kannada_name") or "", "botanical": sp.get("botanical_name") or "",
		              "about": sp.get("description") or ""})
	out = {"found": True, "id": r.name, "name": r.site_name or r.road or r.name, "type": r.site_type or "spot",
	       "road": r.road or "", "area": r.area or "", "zone": _zone_names().get(r.zone_id, ""),
	       "lat": flt(r.gps_lat), "lng": flt(r.gps_lng), "photo": r.photo_url or "", "trees": trees,
	       "landmark": r.landmark or "", "companions": r.companion_plants or ""}
	if frappe.session.user != "Guest" and api._is_member():
		out["visits"] = frappe.get_all("HR Visit", {"site_id": r.name},
		                               ["planned_date", "actual_date", "service_type", "status", "notes"],
		                               order_by="planned_date desc", limit_page_length=20)
	return out


@frappe.whitelist(allow_guest=True)
def zones():
	return frappe.get_all("HR Zone", {"active": 1}, ["name as id", "zone_name as name"], order_by="zone_name")
