import math

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hasiruratha import api, citizen_api
from hasiruratha.hasiruratha.doctype.hr_site import hr_site as hs


@frappe.whitelist()
def get_console_data():
	hs._require_admin()
	sites = frappe.get_all(
		"HR Site", filters={"status": ["!=", "Merged"]},
		fields=["name", "site_id", "site_name", "site_type", "status", "zone_id", "road", "area",
		        "gps_lat", "gps_lng", "tree_count", "possible_duplicate_of", "photo_url"],
		limit_page_length=0)
	by_id = {s.name: s for s in sites}
	queue = []
	for s in sites:
		if s.status == "Needs Review" and s.possible_duplicate_of:
			o = by_id.get(s.possible_duplicate_of) or frappe.db.get_value(
				"HR Site", s.possible_duplicate_of, ["name", "site_name", "gps_lat", "gps_lng"], as_dict=True)
			d = None
			if o and flt(o.gps_lat) and flt(s.gps_lat):
				d = round(hs.haversine(flt(s.gps_lat), flt(s.gps_lng), flt(o.gps_lat), flt(o.gps_lng)))
			queue.append({"site_id": s.name, "site_name": s.site_name, "other_id": s.possible_duplicate_of,
			              "other_name": o.site_name if o else "", "distance_m": d})
	return {
		"sites": sites,
		"queue": queue,
		"volunteers": frappe.get_all("HR Volunteer", filters={"active": 1},
		                             fields=["volunteer_id", "volunteer_name", "area"], limit_page_length=0),
		"report_pins": frappe.get_all(
			"HR Tree Report", {"status": ["!=", "Resolved"]},
			["name", "report_id", "tree_id", "site_id", "zone_id", "area", "road", "issue_type", "priority", "status",
			 "gps_lat", "gps_lng", "photo_url", "assigned_volunteer_name", "submitted_via"], limit_page_length=0),
		"citizen": citizen_api.admin_submissions(),
		"zones": frappe.get_all("HR Zone", {"active": 1}, ["zone_id", "zone_name"], order_by="zone_name"),
		"counts": {
			"review": len(queue),
			"applications": frappe.db.count("HR Application", {"status": "Pending"}),
			"reports": frappe.db.count("HR Tree Report", {"status": "Open"}),
		},
	}


def _check(res):
	if not res.get("success"):
		frappe.throw(res.get("error") or _("Something went wrong"))
	return res


# ───────────────────────────── finding places, trees and reports ─────────────────────────────
OPEN_REPORT = ["!=", "Resolved"]
SAME_SPOT_M = hs.DUPLICATE_RADIUS_M    # same rule the server uses (25 m): a new sapling closer than this is a duplicate
LOOK_AROUND_M = SAME_SPOT_M + 25       # how far the check looks, to show neighbours with photos


def _photo(*urls):
	for u in urls:
		if u and isinstance(u, str) and u.strip():
			return u.strip()
	return ""


def _tree_cards(site_rows, tree_filters=None, lat=None, lng=None, limit=60):
	"""Trees on the given sites as cards: id, photo, place, GPS, and whether an open report already exists."""
	by_site = {s.name: s for s in site_rows}
	if not by_site and not tree_filters:
		return []
	f = dict(tree_filters or {})
	if by_site:
		f["site_id"] = ["in", list(by_site)]
	trees = frappe.get_all("HR Tree", f, ["tree_id", "site_id", "species", "status", "condition", "photo_url", "gps_lat", "gps_lng",
	                                      "date_planted"], order_by="tree_id asc", limit_page_length=limit)
	missing = {t.site_id for t in trees if t.site_id and t.site_id not in by_site}
	if missing:
		for s in frappe.get_all("HR Site", {"name": ["in", list(missing)]},
		                        ["name", "site_name", "road", "area", "zone_id", "gps_lat", "gps_lng", "photo_url"]):
			by_site[s.name] = s
	reports = {}
	if trees:
		for r in frappe.get_all("HR Tree Report", {"tree_id": ["in", [t.tree_id for t in trees]], "status": OPEN_REPORT},
		                        ["name", "report_id", "tree_id", "issue_type", "status", "reported_on", "priority"],
		                        order_by="creation desc"):
			reports.setdefault(r.tree_id, []).append(r)
	out = []
	for t in trees:
		s = by_site.get(t.site_id) or frappe._dict()
		la, ln = flt(t.gps_lat) or flt(s.get("gps_lat")), flt(t.gps_lng) or flt(s.get("gps_lng"))
		rep = reports.get(t.tree_id, [])
		out.append({
			"tree_id": t.tree_id, "species": t.species or "", "status": t.status, "condition": t.condition,
			"site_id": t.site_id, "site_name": s.get("site_name") or t.site_id,
			"road": s.get("road") or "", "area": s.get("area") or "", "zone_id": s.get("zone_id"),
			"lat": la or None, "lng": ln or None, "photo": _photo(t.photo_url, s.get("photo_url")),
			"planted": str(t.date_planted or ""),
			"distance_m": round(hs.haversine(flt(lat), flt(lng), la, ln)) if (lat and lng and la and ln) else None,
			"open_reports": [{"name": r.name, "report_id": r.report_id, "issue_type": r.issue_type, "status": r.status,
			                  "on": str(r.reported_on or ""), "priority": r.priority} for r in rep],
		})
	if lat and lng:
		out.sort(key=lambda x: (x["distance_m"] is None, x["distance_m"] or 0))
	return out


def _site_cards(rows, lat=None, lng=None):
	out = []
	for s in rows:
		la, ln = flt(s.gps_lat), flt(s.gps_lng)
		visit = frappe.db.get_value("HR Visit", {"site_id": s.name, "status": ["in", ["Planned", "Scheduled"]]},
		                            ["visit_id", "planned_date"], as_dict=True, order_by="planned_date asc")
		out.append({
			"site_id": s.name, "site_name": s.site_name or s.name, "road": s.road or "", "area": s.area or "",
			"zone_id": s.zone_id, "status": s.status, "tree_count": s.tree_count or 0, "site_type": s.site_type,
			"lat": la or None, "lng": ln or None, "photo": _photo(s.photo_url),
			"distance_m": round(hs.haversine(flt(lat), flt(lng), la, ln)) if (lat and lng and la and ln) else None,
			"next_visit": {"visit_id": visit.visit_id, "on": str(visit.planned_date or "")} if visit else None,
		})
	if lat and lng:
		out.sort(key=lambda x: (x["distance_m"] is None, x["distance_m"] or 0))
	return out


SITE_FIELDS = ["name", "site_id", "site_name", "site_type", "status", "road", "area", "zone_id", "tree_count",
               "gps_lat", "gps_lng", "photo_url"]


def _find_sites(q=None, area=None, road=None, lat=None, lng=None, radius=300, limit=40):
	if lat and lng:
		rows = hs.get_nearby(lat, lng, min(flt(radius) or 300, 2000))
		return rows[:limit]
	or_f = []
	f = {"status": ["!=", "Merged"]}
	if area:
		f["area"] = area
	if road:
		f["road"] = road
	q = (q or "").strip()
	if q:
		like = "%" + q + "%"
		or_f = [["site_name", "like", like], ["road", "like", like], ["area", "like", like], ["name", "like", like],
		        ["address_full", "like", like]]
	if not (q or area or road):
		return []
	return frappe.get_all("HR Site", filters=f, or_filters=or_f or None, fields=SITE_FIELDS,
	                      order_by="modified desc", limit_page_length=limit)


@frappe.whitelist()
def find_places(q=None, area=None, road=None, lat=None, lng=None, radius=300, kind="trees"):
	"""The admin's "find a place" box. Type an area / road / tree ID, or give a pin (lat, lng).
	kind='trees' -> tree cards (photo, GPS, already-reported?); kind='sites' -> site cards (for visits)."""
	hs._require_admin()
	lat, lng = (flt(lat) or None), (flt(lng) or None)
	q = (q or "").strip()
	sites = _find_sites(q, area, road, lat, lng, radius)
	if kind == "sites":
		return {"sites": _site_cards(sites, lat, lng), "places": _area_road_suggestions(q)}
	trees = _tree_cards(sites, None, lat, lng, limit=80)
	if q and not trees:         # maybe they typed a tree ID
		trees = _tree_cards([], {"tree_id": ["like", "%" + q + "%"]}, lat, lng, limit=40)
	return {"trees": trees, "places": _area_road_suggestions(q)}


def _area_road_suggestions(q):
	"""Area and road names that contain what was typed, with how many sites each has - so the admin can browse."""
	q = (q or "").strip()
	if len(q) < 2:
		rows = frappe.db.sql("""select area, road, count(*) n from `tabHR Site`
			where status != 'Merged' and ifnull(area,'') != '' group by area, road order by n desc limit 12""", as_dict=True)
	else:
		like = "%" + q + "%"
		rows = frappe.db.sql("""select area, road, count(*) n from `tabHR Site`
			where status != 'Merged' and (area like %(l)s or road like %(l)s) group by area, road order by n desc limit 12""",
			{"l": like}, as_dict=True)
	return [{"area": r.area or "", "road": r.road or "", "sites": r.n} for r in rows]


@frappe.whitelist()
def find_reports(q=None, area=None, road=None, only_open=1):
	"""Tree reports as cards with photo, place and GPS (for Assign a volunteer)."""
	hs._require_admin()
	f = {}
	if cint(only_open):
		f["status"] = OPEN_REPORT
	if area:
		f["area"] = area
	if road:
		f["road"] = road
	q = (q or "").strip()
	or_f = None
	if q:
		like = "%" + q + "%"
		or_f = [["report_id", "like", like], ["tree_id", "like", like], ["area", "like", like], ["road", "like", like],
		        ["issue_type", "like", like]]
	rows = frappe.get_all("HR Tree Report", f, ["name", "report_id", "tree_id", "site_id", "area", "road", "issue_type",
	                      "priority", "status", "photo_url", "gps_lat", "gps_lng", "assigned_volunteer_name",
	                      "reported_on", "description"], or_filters=or_f, order_by="modified desc", limit_page_length=40)
	return [{"name": r.name, "report_id": r.report_id, "tree_id": r.tree_id, "site_id": r.site_id, "area": r.area or "",
	         "road": r.road or "", "issue_type": r.issue_type, "priority": r.priority, "status": r.status,
	         "photo": _photo(r.photo_url), "lat": flt(r.gps_lat) or None, "lng": flt(r.gps_lng) or None,
	         "volunteer": r.assigned_volunteer_name or "", "on": str(r.reported_on or ""),
	         "description": r.description or ""} for r in rows]


@frappe.whitelist()
def where_is(lat=None, lng=None):
	"""Pin -> road, area, zone, plus the sites around it. Google when a key is set, OpenStreetMap otherwise."""
	hs._require_admin()
	lat, lng = flt(lat), flt(lng)
	if not (lat and lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
		frappe.throw(_("Bad location"))
	g = api.reverse_geocode({"lat": lat, "lng": lng})
	out = {"road": g.get("road") or "", "area": g.get("area") or "", "pincode": g.get("pincode") or "",
	       "address": g.get("address") or "", "lookup_ok": bool(g.get("success"))}
	out.update(citizen_api.suggest_zone(lat, lng, out["road"], out["area"]))
	return out


@frappe.whitelist()
def search_map(q=None):
	"""Typed place name -> map points to jump to."""
	hs._require_admin()
	return _check(api.search_places({"q": q})).get("data", [])


# ───────────────────────────── duplicate check for a planting spot ─────────────────────────────
def _around(lat, lng, radius):
	"""Trees and sites near a pin, with photos, closest first."""
	sites = hs.get_nearby(lat, lng, radius)
	out = []
	for c in _tree_cards(sites, None, lat, lng, limit=50):
		if c["distance_m"] is not None and c["distance_m"] <= radius:
			out.append(c)
	seen = {c["site_id"] for c in out}
	for s in sites:          # sites that exist but have no tree yet still block the spot
		if s.name not in seen:
			out.extend({**c, "tree_id": "", "species": ""} for c in _site_cards([s], lat, lng))
	return sorted(out, key=lambda x: (x["distance_m"] is None, x["distance_m"] or 0))


def _offset(lat, lng, metres, bearing_deg):
	b = math.radians(bearing_deg)
	return (lat + (metres * math.cos(b)) / 111320.0,
	        lng + (metres * math.sin(b)) / (111320.0 * max(math.cos(math.radians(lat)), 0.01)))


def _free_spot(lat, lng):
	"""The closest point (ring around the pin) that is at least SAME_SPOT_M from every known tree/site."""
	near = hs.get_nearby(lat, lng, SAME_SPOT_M + 60)
	pts = [(flt(s.gps_lat), flt(s.gps_lng)) for s in near]
	pts += [(flt(t.gps_lat), flt(t.gps_lng)) for t in frappe.get_all(
		"HR Tree", {"gps_lat": ["between", [lat - 0.0009, lat + 0.0009]], "gps_lng": ["between", [lng - 0.0009, lng + 0.0009]]},
		["gps_lat", "gps_lng"], limit_page_length=200)]
	for metres in (SAME_SPOT_M + 2, SAME_SPOT_M + 6, SAME_SPOT_M + 12, SAME_SPOT_M + 20, SAME_SPOT_M + 35):
		for bearing in range(0, 360, 30):
			la, ln = _offset(lat, lng, metres, bearing)
			if all(hs.haversine(la, ln, a, b) >= SAME_SPOT_M for a, b in pts if a and b):
				return {"lat": round(la, 7), "lng": round(ln, 7), "metres": metres}
	return None


@frappe.whitelist()
def check_spot(lat=None, lng=None, road=None, area=None):
	"""Is there already a tree or site at this pin? Returns the neighbours (with photos) and a free spot nearby."""
	hs._require_admin()
	lat, lng = flt(lat), flt(lng)
	if not (lat and lng):
		return {"duplicate": False, "nearby": []}
	nearby = _around(lat, lng, LOOK_AROUND_M)
	same = [c for c in nearby if c["distance_m"] is not None and c["distance_m"] <= SAME_SPOT_M]
	out = {"duplicate": bool(same), "same_spot": same, "nearby": nearby[:12], "limit_m": SAME_SPOT_M}
	if same:
		out["free_spot"] = _free_spot(lat, lng)
	return out


# ───────────────────────────── the four actions (all need photo evidence) ─────────────────────────────
def _need_photo(url):
	if not (url or "").strip():
		frappe.throw(_("Photo evidence is required. Attach or take a photo."))
	return url.strip()


@frappe.whitelist(methods=["POST"])
def plant_sapling(**b):
	"""Admin plants a sapling: photo + GPS + road/area are mandatory, and a spot that already has a tree is refused
	unless the admin chooses 'plant anyway' (it is then sent to duplicate review)."""
	hs._require_admin()
	b.pop("cmd", None)
	photo = _need_photo(b.get("photo_url"))
	lat, lng = flt(b.get("gps_lat")), flt(b.get("gps_lng"))
	if not (lat and lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
		frappe.throw(_("Set the location: use my location, search a place, or tap the map."))
	road, area = (b.get("road") or "").strip(), (b.get("area") or "").strip()
	if not (road or area):
		frappe.throw(_("Add the road or the area name."))
	n = max(1, min(cint(b.get("count")) or 1, 10))
	if not cint(b.get("force")):
		chk = check_spot(lat, lng, road, area)
		if chk["duplicate"]:
			return {"success": False, "duplicate": True, **chk}
	label = area or road
	site = _check(api.add_site({
		"site_name": "%s - %s" % (label, today()), "name": "%s - %s" % (label, today()),
		"road": road, "area": area, "gps_lat": lat, "gps_lng": lng, "site_type": "spot", "tree_count": n,
		"photo_url": photo, "status": "Completed", "notes": b.get("notes") or "",
		"added_by": frappe.utils.get_fullname(frappe.session.user)}))
	frappe.db.set_value("HR Site", site["site_id"], {
		"submitted_via": "Admin", "address_full": b.get("address") or "", "admin_reviewed": 1})
	ids = []
	for i in range(n):
		t = api.add_tree({"site_id": site["site_id"], "road": road, "area": area, "gps_lat": lat, "gps_lng": lng,
		                  "species": b.get("species") or None, "photo_url": photo, "status": "Completed",
		                  "planted_by": frappe.utils.get_fullname(frappe.session.user), "position": i + 1,
		                  "notes": b.get("notes") or "", "planting_type": "New"})
		ids.append(t["tree_id"])
	return {"success": True, "site_id": site["site_id"], "tree_ids": ids, "needs_review": site.get("needs_review"),
	        "possible_duplicate_of": site.get("possible_duplicate_of")}


@frappe.whitelist(methods=["POST"])
def report_tree(**b):
	"""Report a tree: photo mandatory; if the tree already has an open report the admin is told, not duplicated."""
	hs._require_admin()
	b.pop("cmd", None)
	b["photo_url"] = _need_photo(b.get("photo_url"))
	tree = (b.get("tree_id") or "").strip()
	if not tree:
		frappe.throw(_("Choose the tree from the list."))
	existing = frappe.get_all("HR Tree Report", {"tree_id": tree, "status": OPEN_REPORT},
	                          ["name", "report_id", "issue_type", "status", "reported_on", "photo_url"], order_by="creation desc")
	if existing and not cint(b.get("force")):
		return {"success": False, "already_reported": True, "reports": existing}
	t = frappe.db.get_value("HR Tree", {"tree_id": tree}, ["gps_lat", "gps_lng", "site_id"], as_dict=True)
	if t and not (flt(b.get("gps_lat")) and flt(b.get("gps_lng"))) and flt(t.gps_lat) and flt(t.gps_lng):
		b["gps_lat"], b["gps_lng"] = t.gps_lat, t.gps_lng
	res = _check(api.create_tree_report(b))
	return res


@frappe.whitelist(methods=["POST"])
def plan_visit(**b):
	"""Plan a visit: the site (area, road, GPS, photo) must be chosen; the visit keeps the area and zone, and a photo."""
	hs._require_admin()
	b.pop("cmd", None)
	sid = (b.get("site_id") or "").strip()
	site = frappe.db.get_value("HR Site", sid, ["name", "area", "road", "zone_id", "photo_url", "gps_lat", "gps_lng"], as_dict=True) if sid else None
	if not site:
		frappe.throw(_("Choose the site from the list."))
	if not (flt(site.gps_lat) and flt(site.gps_lng)):
		frappe.throw(_("This site has no GPS location yet. Open it and set the location first."))
	photo = (b.get("photo_url") or "").strip() or (site.photo_url or "").strip()
	if not photo:
		frappe.throw(_("Photo evidence is required. This site has no photo, so attach one."))
	if not site.photo_url:       # keep the new photo on the site too, so the next admin sees it
		frappe.db.set_value("HR Site", sid, "photo_url", photo)
	if not cint(b.get("force")) and b.get("planned_date"):
		same = frappe.db.get_value("HR Visit", {"site_id": sid, "planned_date": getdate(b["planned_date"]),
		                                        "status": ["in", ["Planned", "Scheduled"]]}, "visit_id")
		if same:
			return {"success": False, "already_planned": True, "visit_id": same}
	b["photo_url"] = photo
	b["area"] = site.area or None
	b["zone"] = site.zone_id or None
	b["planned_by"] = frappe.utils.get_fullname(frappe.session.user)
	return _check(api.add_visit(b))


@frappe.whitelist(methods=["POST"])
def assign(tree_id=None, report_id=None, volunteer_id=None):
	hs._require_admin()
	if report_id:
		return _check(api.assign_tree_report({"report_id": report_id, "volunteer_id": volunteer_id}))
	return _check(api.assign_tree({"tree_id": tree_id, "volunteer_id": volunteer_id}))
