# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
HR Duplicate Report: one row for every site that was flagged as a possible duplicate.

Created automatically by HR Site.after_insert (no Server Script needed). Holds the new site, the existing
site it looks like, the distance, and both photos, so the admin can decide:
    Kept as New  |  Merged  |  Deleted (copy goes to HR Deleted Site)  |  Restored (re-planted from HR Deleted Site)
"""
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

PENDING = "Pending Review"


class HRDuplicateReport(Document):
	def validate(self):
		# Status is changed by the decision buttons (approve / merge / delete / re-plant), never by hand or by
		# dragging a Kanban card: those would skip moving the trees and closing the trail.
		if not self.is_new() and self.has_value_changed("status") and not self.flags.from_decision:
			frappe.throw(_("Use the Decide buttons (Different site / Merge / Delete duplicate) to close a duplicate report."))


def _geojson(lat, lng):
	return frappe.as_json({"type": "FeatureCollection", "features": [
		{"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [flt(lng), flt(lat)]}}]})


def create_for_site(site):
	"""Create (once) the Pending Review report for a flagged HR Site doc. Returns the report name or None."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _site_card, haversine

	if not (site.possible_duplicate_of and site.status == "Needs Review"):
		return None
	existing = frappe.db.exists("HR Duplicate Report", {"site": site.name, "status": PENDING})
	if existing:
		return existing
	other = _site_card(site.possible_duplicate_of)
	if not other:
		return None
	mine = _site_card(site.name) or frappe._dict(photo=None)
	distance = None
	if flt(site.gps_lat) and flt(other.gps_lat):
		distance = round(haversine(flt(site.gps_lat), flt(site.gps_lng), flt(other.gps_lat), flt(other.gps_lng)), 1)
	doc = frappe.get_doc({
		"doctype": "HR Duplicate Report",
		"site": site.name,
		"possible_duplicate_of_site": other.name,
		"possible_duplicate_of_tree_id": frappe.db.get_value("HR Tree", {"site_id": other.name}, "name", order_by="creation asc"),
		"distance_between_records": distance,
		"status": PENDING,
		"picture_of_tree": mine.photo,
		"original_photo": other.photo,
		"zone": site.zone_id, "area": site.area, "road": site.road,
		"geolocation_vris": _geojson(site.gps_lat, site.gps_lng) if flt(site.gps_lat) else None,
		"reported_by": site.owner, "report_date": now_datetime(),
		"admin_remarks": _("Automatically detected: {0} is {1} m from {2}.").format(site.name, distance, other.name),
	}).insert(ignore_permissions=True)
	return doc.name


def resolve(site_name, status, remarks=None, **extra):
	"""Close the open report(s) of `site_name`. Call BEFORE the site changes or is deleted."""
	for name in frappe.get_all("HR Duplicate Report", {"site": site_name, "status": PENDING}, pluck="name"):
		values = {"status": status, "resolved_by": frappe.session.user, "resolved_on": now_datetime(), **extra}
		if remarks:
			old = frappe.db.get_value("HR Duplicate Report", name, "admin_remarks") or ""
			values["admin_remarks"] = (old + "\n" + remarks).strip()
		frappe.db.set_value("HR Duplicate Report", name, values)


@frappe.whitelist()
def comparison(name):
	"""Both sides for the report form: the new site (from the report, it may be deleted) and the existing site (live)."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin, _site_card

	_require_admin()
	r = frappe.get_doc("HR Duplicate Report", name)
	this = frappe._dict(name=r.site, site_name=r.site, road=r.road, area=r.area, photo=r.picture_of_tree,
	                    status=frappe.db.get_value("HR Site", r.site, "status") or _("deleted"),
	                    tree_count=frappe.db.get_value("HR Site", r.site, "tree_count") or 0)
	other = _site_card(r.possible_duplicate_of_site) or frappe._dict(name=r.possible_duplicate_of_site)
	other["photo"] = other.get("photo") or r.original_photo
	return {"this": this, "other": other, "distance_m": r.distance_between_records}


@frappe.whitelist(methods=["POST"])
def bulk_delete_duplicates(names, reason):
	"""Admin: delete the duplicate site of every selected Pending Review report in one go (workspace list / Console).

	Each site's trees and records move to the site it duplicates; a copy goes to HR Deleted Site and the report is
	closed as Deleted. Reports that are not pending, or whose site has records but no original, are skipped and listed.
	"""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin, delete_duplicate

	_require_admin()
	names = frappe.parse_json(names) if isinstance(names, str) else names
	done, skipped = [], []
	for n in names or []:
		site, st = frappe.db.get_value("HR Duplicate Report", n, ["site", "status"]) or (None, None)
		if st != PENDING or not site or not frappe.db.exists("HR Site", site):
			skipped.append({"report": n, "why": _("Not pending, or the site is already gone")})
			continue
		try:
			delete_duplicate(site, reason)
			done.append(n)
		except Exception as e:
			frappe.db.rollback()
			skipped.append({"report": n, "why": str(e)})
	return {"deleted": done, "skipped": skipped}
