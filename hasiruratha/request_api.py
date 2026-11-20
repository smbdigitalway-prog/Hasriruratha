# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Citizen requests (/request, /my-requests). Sign-in required (see citizen_auth).

* prepare(lat, lng)  -> address (road, area, pin code), suggested zone, and registered spots/trees
                        within NEAR_M metres with photos, so the citizen can see if it is already there
* submit(...)        -> creates an HR Request; flags a possible duplicate when a registered spot or
                        another open request is within DUP_M metres
* my_requests()      -> the citizen's own requests and their status
"""
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, cint, flt, get_fullname, today

from hasiruratha import api, citizen_api, public_api
from hasiruratha.hasiruratha.doctype.hr_site import hr_site as hs

NEAR_M = 60          # spots shown to the citizen
DUP_M = 25           # closer than this = possible duplicate, unless the citizen says it is a different spot
SAME_M = 10          # closer than this = always checked by an admin
TYPES = ("New location", "Maintenance")
ISSUES = ("Dead tree", "Damage", "Pest / Disease", "Watering", "Leaning", "Tree guard", "Support pole",
          "Debris / garbage", "Other")
OPEN = ("Received", "Under review", "Accepted", "Scheduled")


def _user():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in"), frappe.AuthenticationError)
	return frappe.session.user


def _latlng(lat, lng):
	lat, lng = flt(lat), flt(lng)
	if not (lat and lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
		frappe.throw(_("We need the location. Use your GPS or place the pin on the map."))
	return lat, lng


def _address(lat, lng):
	key = "hr_rq_addr_%.4f_%.4f" % (lat, lng)
	hit = api._cache().get_value(key)
	if hit:
		return hit
	g = api.reverse_geocode({"lat": lat, "lng": lng})
	if not g.get("success") or not g.get("pincode"):
		n = citizen_api._nominatim(lat, lng)
		if n.get("success"):
			g = {**n, **{k: v for k, v in g.items() if v and k != "success"}} if g.get("success") else n
	out = {"road": g.get("road") or "", "area": g.get("area") or "", "pincode": g.get("pincode") or "",
	       "address": g.get("address") or ""}
	out.update(citizen_api.suggest_zone(lat, lng, out["road"], out["area"]))
	api._cache().set_value(key, out, expires_in_sec=6 * 3600)
	return out


@frappe.whitelist()
@rate_limit(limit=120, seconds=600)
def prepare(lat=None, lng=None):
	_user()
	lat, lng = _latlng(lat, lng)
	out = dict(_address(lat, lng))
	spots = []
	for s in hs.get_nearby(lat, lng, NEAR_M):
		trees = frappe.get_all("HR Tree", {"site_id": s.name, "status": ["!=", "Merged"]},
		                       ["name", "species", "date_planted", "photo_url", "condition"], order_by="position",
		                       limit_page_length=30)
		spots.append({
			"id": s.name, "name": s.site_name or s.road or s.name, "distance_m": s.distance_m,
			"road": s.road or "", "area": s.area or "", "lat": flt(s.gps_lat), "lng": flt(s.gps_lng),
			"photo": s.photo_url or next((t.photo_url for t in trees if t.photo_url), ""),
			"trees": [{"id": t.name, "species": t.species or "Not known yet", "age": public_api.age_text(t.date_planted),
			           "photo": t.photo_url or "", "condition": t.condition or ""} for t in trees],
		})
	out["spots"] = spots
	out["open_requests"] = len(_open_requests_near(lat, lng, DUP_M))
	return out


def _open_requests_near(lat, lng, radius, exclude=None):
	d = radius / 111320.0
	rows = frappe.get_all("HR Request", {"status": ["in", OPEN], "request_type": "New location",
	                                     "creation": [">=", add_days(today(), -180)],
	                                     "gps_lat": ["between", [lat - d, lat + d]], "gps_lng": ["between", [lng - 2 * d, lng + 2 * d]]},
	                      ["name", "gps_lat", "gps_lng"])
	return [r for r in rows if r.name != exclude and hs.haversine(lat, lng, flt(r.gps_lat), flt(r.gps_lng)) <= radius]


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=30, seconds=3600)
def submit(request_type=None, lat=None, lng=None, accuracy=None, source=None, photo_url=None, issue_type=None,
           description=None, address_line=None, road=None, area=None, pincode=None, zone=None,
           existing_site=None, tree=None, different_spot=0):
	user = _user()
	if request_type not in TYPES:
		frappe.throw(_("Please choose what you are asking for"))
	lat, lng = _latlng(lat, lng)
	road, area = (road or "").strip()[:140], (area or "").strip()[:140]
	pin = api._digits(pincode)
	if not road or not area:
		frappe.throw(_("Please fill in the road and the area"))
	if len(pin) != 6:
		frappe.throw(_("Please enter the 6-digit pin code"))
	if zone and not frappe.db.exists("HR Zone", zone):
		zone = None
	auto = _address(lat, lng)
	photo = citizen_api._check_photo(photo_url) if photo_url else ""
	is_maint = request_type == "Maintenance"
	if is_maint:
		if issue_type not in ISSUES:
			frappe.throw(_("Please choose what the tree needs"))
		if not photo:
			frappe.throw(_("Please add a photo of the tree"))
	tree = tree if tree and frappe.db.exists("HR Tree", tree) else None
	existing_site = existing_site if existing_site and frappe.db.exists("HR Site", existing_site) else None
	if tree and not existing_site:
		existing_site = frappe.db.get_value("HR Tree", tree, "site_id")

	near = hs.get_nearby(lat, lng, NEAR_M)
	nearest = next((n for n in near if n.name == existing_site), None) or (near[0] if near else None)
	dup = False
	if not is_maint:
		close_spot = any(n.distance_m <= DUP_M for n in near)
		too_close = any(n.distance_m <= SAME_M for n in near)       # too close to be a different spot
		dup = (bool(existing_site) or too_close or (close_spot and not cint(different_spot))
		       or bool(_open_requests_near(lat, lng, DUP_M)))

	doc = frappe.get_doc({
		"doctype": "HR Request", "request_type": request_type, "status": "Under review" if dup else "Received",
		"issue_type": issue_type if is_maint else None, "description": (description or "").strip()[:1000],
		"photo": photo, "gps_lat": lat, "gps_lng": lng,
		"gps_accuracy_m": cint(accuracy) if source == "GPS" and accuracy else None,
		"location_source": "GPS" if source == "GPS" else "Map pin",
		"address_line": (address_line or "").strip()[:200], "road": road, "area": area, "pincode": pin,
		"zone": zone or auto.get("zone_id"), "zone_note": "Chosen by the citizen" if zone else auto.get("zone_note"),
		"nearest_site": nearest.name if nearest else None,
		"nearest_distance_m": nearest.distance_m if nearest else None,
		"related_tree": tree, "citizen_says_new": 0 if is_maint else cint(different_spot), "possible_duplicate": cint(dup),
		"citizen_user": user, "citizen_name": get_fullname(user),
		"mobile": frappe.db.get_value("User", user, "mobile_no") or "", "email": frappe.db.get_value("User", user, "email") or user,
	}).insert(ignore_permissions=True)
	what = ("%s: %s" % (request_type, issue_type)) if is_maint else request_type
	citizen_api._todo_admins("HR Request", doc.name, _("{0} at {1}, {2}{3}").format(
		what, road, area, _(" - possible duplicate, please check") if dup else ""))
	return {"success": True, "name": doc.name, "status": doc.status, "possible_duplicate": dup}


@frappe.whitelist()
def my_requests():
	user = _user()
	rows = frappe.get_all("HR Request", {"citizen_user": user},
	                      ["name", "request_type", "issue_type", "status", "road", "area", "photo", "creation",
	                       "admin_notes", "completed_on", "assigned_volunteer"], order_by="creation desc", limit_page_length=100)
	for r in rows:
		r["has_volunteer"] = bool(r.pop("assigned_volunteer"))      # names stay private
		r["creation"] = str(r.creation)[:16]
		r["completed_on"] = str(r.completed_on or "")
	return rows
