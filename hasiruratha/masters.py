# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Pick-lists that people can also type into: Area, Road, Landmark, Route, Species.

* On a form they are dropdowns (Link fields). If someone types a name that is not in the list yet
  (a citizen, a volunteer, the spreadsheet import), it is added as "Unverified" instead of failing.
* A typed name that matches an existing name, or one of its "Other spellings", is filed under that
  name, so "Jayanagar 2nd blk" goes to "Jayanagar 2nd Block" once the admin has added that spelling.
* Admins join two spellings with Frappe's own Rename -> "Merge with existing", which also updates
  every site, tree and request that used the old spelling.

Records that use these lists inherit AutoLinks: it fills the lists in *before* Frappe checks the
links (Frappe checks links before a document's own validate runs).
"""
import re

import frappe

FIELD = {"HR Area": "area_name", "HR Road": "road_name", "HR Landmark": "landmark_name",
         "HR Route": "route_name", "HR Species": "common_name"}
PLACEHOLDER = {"", "-", "na", "n/a", "not sure", "unknown", "none", "nil"}

# fieldname on the record -> list it points to
LINKS = {
	"HR Site": {"area": "HR Area", "road": "HR Road", "landmark": "HR Landmark", "route": "HR Route"},
	"HR Tree": {"species": "HR Species"},
	"HR Request": {"area": "HR Area", "road": "HR Road", "landmark": "HR Landmark"},
	"HR Volunteer": {"area": "HR Area", "road": "HR Road"},
	"HR Diary Entry": {"area": "HR Area"},
}


def clean(name):
	return re.sub(r"\s+", " ", str(name or "")).strip()[:140]


def find(doctype, name):
	"""Existing list entry for `name` (same name ignoring case/spaces, or listed as another spelling)."""
	name = clean(name)
	if not name:
		return None
	hit = frappe.db.get_value(doctype, {FIELD[doctype]: name}, "name")      # the database ignores case
	if hit:
		return hit
	if frappe.get_meta(doctype).has_field("aliases"):
		low = name.lower()
		for row in frappe.get_all(doctype, {"aliases": ["like", "%" + name + "%"]}, ["name", "aliases"]):
			if low in {clean(a).lower() for a in (row.aliases or "").splitlines()}:
				return row.name
	return None


def ensure(doctype, name, **extra):
	"""Name of the list entry for `name`, adding it as Unverified when it is new. None for blanks."""
	name = clean(name)
	if name.lower() in PLACEHOLDER:
		return None
	hit = find(doctype, name)
	if hit:
		return hit
	meta = frappe.get_meta(doctype)
	vals = {"doctype": doctype, FIELD[doctype]: name}
	if meta.has_field("verified"):
		vals["verified"] = 0
	vals.update({k: v for k, v in extra.items() if v and meta.has_field(k)})
	try:
		return frappe.get_doc(vals).insert(ignore_permissions=True).name
	except frappe.DuplicateEntryError:
		return find(doctype, name) or name


def ensure_links(doc):
	zone = doc.get("zone_id") or doc.get("zone") or doc.get("primary_zone_id")
	for field, doctype in LINKS.get(doc.doctype, {}).items():
		value = doc.get(field)
		if not value:
			continue
		extra = {}
		if doctype in ("HR Area", "HR Road", "HR Route"):
			extra["zone"] = zone
		elif doctype == "HR Landmark":
			extra["area"] = doc.get("area")
		doc.set(field, ensure(doctype, value, **extra))


class AutoLinks:
	"""Mixin for documents that use the pick-lists (put it before Document in the class bases)."""

	def _validate_links(self):
		ensure_links(self)
		return super()._validate_links()


def tidy(doc):
	"""validate() of the list DocTypes: tidy the name and the other spellings."""
	field = FIELD.get(doc.doctype)
	if field:
		doc.set(field, clean(doc.get(field)))
	if doc.meta.has_field("aliases"):
		seen, out = {clean(doc.get(field)).lower()}, []
		for a in (doc.aliases or "").splitlines():
			a = clean(a)
			if a and a.lower() not in seen:
				seen.add(a.lower())
				out.append(a)
		doc.aliases = "\n".join(out)


@frappe.whitelist(allow_guest=True)
def options(kind=None, area=None):
	"""Names for the dropdown-or-type fields on the web forms (non-sensitive, verified first)."""
	doctype = {"area": "HR Area", "road": "HR Road", "landmark": "HR Landmark", "species": "HR Species"}.get(kind)
	if not doctype:
		return []
	filters = {"area": area} if doctype == "HR Landmark" and area else {}
	order = "verified desc, {0} asc".format(FIELD[doctype]) if frappe.get_meta(doctype).has_field("verified") else FIELD[doctype]
	return frappe.get_all(doctype, filters, pluck="name", order_by=order, limit_page_length=1000)
