# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Volunteers log care for the trees they look after (/my-trees).

* my_trees()            the signed-in volunteer's trees (owner_volunteer_id), with last watered etc.
* log(trees, activity)  one HR Care Log per tree (hours of the round are split over its trees)
* set_gps(tree, ...)    capture GPS for a tree that was imported without it ("GPS pending")

A volunteer may only log for trees assigned to them; admins may log for any tree.
"""
import json

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, flt, getdate, today

from hasiruratha import api, citizen_api, public_api
from hasiruratha.hasiruratha.doctype.hr_site import hr_site as hs

ACTIVITIES = ("Watering", "Guard installed", "Guard removed", "Support pole", "Pruning", "Weeding",
              "Manure / soil", "Pest treatment", "Replanting", "Other")


def _me():
	user = frappe.session.user
	if user == "Guest" or not api._is_member(user):
		frappe.throw(_("Please sign in as a volunteer"), frappe.PermissionError)
	vol = frappe.db.get_value("HR Volunteer", {"user": user}, ["name", "volunteer_name"], as_dict=True)
	return vol, api._is_admin(user)


def _check_tree(tree, vol, admin):
	owner = frappe.db.get_value("HR Tree", tree, "owner_volunteer_id")
	if owner is None and not frappe.db.exists("HR Tree", tree):
		frappe.throw(_("Tree {0} not found").format(tree))
	if not admin and (not vol or owner != vol.name):
		frappe.throw(_("Tree {0} is not assigned to you").format(tree), frappe.PermissionError)


@frappe.whitelist()
def my_trees():
	vol, admin = _me()
	if not vol:
		return {"volunteer": None, "trees": []}
	trees = frappe.get_all("HR Tree", {"owner_volunteer_id": vol.name, "status": ["!=", "Merged"]},
	                       ["name", "species", "site_id", "date_planted", "planting_type", "last_watered",
	                        "last_maintenance", "gps_status", "photo_url", "tree_guard"], order_by="site_id, position",
	                       limit_page_length=500)
	sites = {s.name: s for s in frappe.get_all("HR Site", {"name": ["in", list({t.site_id for t in trees}) or [""]]},
	                                            ["name", "site_name", "landmark", "road", "area", "route"])}
	for t in trees:
		s = sites.get(t.site_id) or frappe._dict()
		t.update({"place": s.site_name or s.landmark or s.road or t.site_id, "landmark": s.landmark or "",
		          "road": s.road or "", "area": s.area or "", "route": s.route or "",
		          "age": public_api.age_text(t.date_planted), "last_watered": str(t.last_watered or ""),
		          "last_maintenance": str(t.last_maintenance or ""), "date_planted": str(t.date_planted or "")})
	return {"volunteer": vol.volunteer_name, "trees": trees, "activities": ACTIVITIES}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=60, seconds=3600)
def log(trees=None, activity=None, log_date=None, hours=None, notes=None, photo_url=None):
	vol, admin = _me()
	trees = json.loads(trees) if isinstance(trees, str) else (trees or [])
	trees = [t for t in dict.fromkeys(trees) if t]
	if not trees:
		frappe.throw(_("Please choose at least one tree"))
	if activity not in ACTIVITIES:
		frappe.throw(_("Please choose what you did"))
	day = getdate(log_date or today())
	if day > getdate(today()):
		frappe.throw(_("The date cannot be in the future"))
	for t in trees:
		_check_tree(t, vol, admin)
	photo = citizen_api._check_photo(photo_url) if photo_url else None
	each = round(flt(hours) / len(trees), 2) if flt(hours) > 0 else 0
	names = []
	for t in trees:
		names.append(frappe.get_doc({
			"doctype": "HR Care Log", "tree": t, "activity": activity, "log_date": day,
			"volunteer": vol.name if vol else None, "hours": each, "notes": (notes or "").strip()[:500],
			"photo": photo, "source": "App",
		}).insert(ignore_permissions=True).name)
	return {"success": True, "logged": len(names)}


@frappe.whitelist()
def pending_trees(route=None, area=None):
	"""Trees waiting for GPS: all of them for admins, a volunteer's own trees otherwise."""
	vol, admin = _me()
	filters = {"gps_status": "Pending", "status": ["!=", "Merged"]}
	if not admin:
		if not vol:
			return {"trees": [], "admin": False}
		filters["owner_volunteer_id"] = vol.name
	trees = frappe.get_all("HR Tree", filters, ["name", "species", "site_id", "position", "caretaker_type", "caretaker_name",
	                                            "owner_volunteer_id", "notes"], order_by="site_id, position", limit_page_length=1000)
	sites = {s.name: s for s in frappe.get_all("HR Site", {"name": ["in", list({t.site_id for t in trees}) or [""]]},
	                                            ["name", "site_name", "landmark", "area", "route", "tree_count", "site_type"])}
	out = []
	for t in trees:
		s = sites.get(t.site_id) or frappe._dict()
		if route and (s.route or "") != route or area and (s.area or "") != area:
			continue
		out.append({"name": t.name, "species": t.species or "", "site": t.site_id, "place": s.site_name or s.landmark or "",
		            "landmark": s.landmark or "", "area": s.area or "", "route": s.route or "", "position": t.position,
		            "of": s.tree_count or 1, "caretaker": t.caretaker_name or "", "adopted": bool(t.caretaker_type or t.owner_volunteer_id)})
	totals = {"pending": frappe.db.count("HR Tree", {"gps_status": "Pending", "status": ["!=", "Merged"]}),
	          "tagged": frappe.db.count("HR Tree", {"gps_status": "Captured", "status": ["!=", "Merged"]})} if admin else {}
	return {"trees": out, "admin": admin, "totals": totals}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=300, seconds=3600)
def set_gps(tree=None, lat=None, lng=None, accuracy=None, photo_url=None):
	vol, admin = _me()
	_check_tree(tree, vol, admin)
	lat, lng = flt(lat), flt(lng)
	if not (lat and lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
		frappe.throw(_("Bad location"))
	if cint(accuracy) > 50:
		frappe.throw(_("The location is too rough (±{0} m). Step into the open and try again.").format(cint(accuracy)))
	near = [n for n in hs.get_nearby(lat, lng, 8) if n.name != frappe.db.get_value("HR Tree", tree, "site_id")]
	doc = frappe.get_doc("HR Tree", tree)
	doc.gps_lat, doc.gps_lng = lat, lng
	if photo_url:
		doc.photo_url = citizen_api._check_photo(photo_url)
	doc.save(ignore_permissions=True)
	site = frappe.db.get_value("HR Site", doc.site_id, ["name", "gps_lat", "gps_lng"], as_dict=True)
	if site and not (flt(site.gps_lat) and flt(site.gps_lng)):
		s = frappe.get_doc("HR Site", site.name)        # a stretch without GPS: use its first located tree
		s.gps_lat, s.gps_lng = lat, lng
		if doc.photo_url and not s.photo_url:
			s.photo_url = doc.photo_url
		s.flags.ignore_duplicate_check = True
		s.save(ignore_permissions=True)
	return {"success": True, "gps_status": "Captured",
	        "near": [{"site": n.name, "name": n.site_name or n.name, "distance_m": n.distance_m} for n in near[:3]]}
