# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Import the volunteers' plantation / watering workbook (.xlsx or .csv). Every sheet with a header row
is read (e.g. "Not adopted" and "Adopted").

Columns (matched loosely, any order):
  Ownership (optional) | # Plants | Area | Watering Route | Location | Plant | <one column per date>

Each row becomes:
  * a Spot (1 plant) or a Stretch (several plants) named after the Location text, with Area, Watering Route
    ("Not needed" = none) and Landmark. New names go into the lists as Unverified.
  * one Tree per plant (1 sapling = 1 spot), species from "Plant", GPS pending, planting date left empty
  * the full Location text (other plants mentioned, "replacement", ...) kept in the notes; planting type from
    the text: "replac..." -> Replacement, "rescued"/"recovered" -> Rescued, "previous year"/"lone plant" -> Existing
  * Ownership -> who looks after it: a registered volunteer when the name matches exactly one active volunteer,
    otherwise a caretaker type (Resident, Shop owner, Security guard, Other) with the name kept as written
  * every filled date cell -> a Watering entry in the care log for each tree of the row

Rows already imported (same sheet, row and location) are skipped, so the same file can be imported again.
preview=1 changes nothing and reports what would happen.
"""
import csv
import io
import re
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import cint

from hasiruratha import api, masters

MARK = "Imported from the watering sheet"
NO_ROUTE = {"", "not needed", "na", "n/a", "-", "none", "nil"}

SPECIES = {   # spelling as written -> (name in the list, botanical name)
	"honge": ("Honge", "Pongamia pinnata"), "mahogony": ("Mahogany", "Swietenia mahagoni"),
	"mahagony": ("Mahogany", "Swietenia mahagoni"), "mahogany": ("Mahogany", "Swietenia mahagoni"),
	"kadamba": ("Kadamba", "Neolamarckia cadamba"), "pipal": ("Pipal", "Ficus religiosa"),
	"peepal": ("Pipal", "Ficus religiosa"), "banyan": ("Banyan", "Ficus benghalensis"),
	"halasu": ("Halasu", "Artocarpus heterophyllus"), "sampige": ("Sampige", "Magnolia champaca"),
	"bakula": ("Bakula", "Mimusops elengi"), "nerale": ("Jamun", "Syzygium cumini"), "jamun": ("Jamun", "Syzygium cumini"),
	"jamun protected": ("Jamun", "Syzygium cumini"), "badami": ("Indian almond", "Terminalia catappa"),
	"temple tree": ("Frangipani", "Plumeria"), "guava": ("Guava", "Psidium guajava"),
	"mango": ("Mango", "Mangifera indica"), "neem": ("Neem", "Azadirachta indica"), "ficus": ("Ficus", None),
}
AREAS = {     # spelling as written -> name in the list (the written spelling is kept as an "other spelling")
	"jayanagar 2nd blk": "Jayanagar 2nd Block", "jayanagar 3rd blk": "Jayanagar 3rd Block",
	"jayanagar 8th block": "Jayanagar 8th Block", "jayanagar 9th": "Jayanagar 9th Block",
	"jayanagar t block": "Jayanagar T Block", "bsk ii": "Banashankari 2nd Stage",
	"banashankari 2nd stage": "Banashankari 2nd Stage", "lalbhag": "Lalbagh", "southend circle": "South End Circle",
}
ROUTES = {"ashoka piller": "Ashoka Pillar"}
CARETAKER_TYPES = {   # Ownership values that are a kind of person, not a name
	"localite": "Resident", "resident": "Resident", "general": "Other", "security guard": "Security guard",
	"shop owner": "Shop owner", "coconut vendor": "Shop owner",
}


# ───────────────────────────── reading the file ─────────────────────────────
def _sheets(file_url):
	f = frappe.get_doc("File", {"file_url": file_url})
	content = f.get_content()
	if (f.file_name or file_url).lower().endswith(".csv"):
		text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
		return [("Sheet1", list(csv.reader(io.StringIO(text))))]
	from openpyxl import load_workbook

	wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
	return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]


def _as_date(v):
	if isinstance(v, datetime):
		return v.date()
	if isinstance(v, date):
		return v
	s = str(v or "").strip()
	for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%y"):
		try:
			return datetime.strptime(s, fmt).date()
		except ValueError:
			pass
	return None


def _columns(header):
	"""Which column holds what. Date headers are the watering days."""
	cols, dates = {}, {}
	for i, h in enumerate(header):
		d = _as_date(h)
		if d:
			dates[i] = d
			continue
		raw = str(h or "").lower()
		k = re.sub(r"[^a-z]", "", raw)
		if "#" in raw or k in ("plants", "noofplants", "count", "numberofplants", "qty"):
			cols.setdefault("count", i)
		elif k in ("plant", "species", "tree", "treetype"):
			cols.setdefault("plant", i)
		elif "route" in k:
			cols.setdefault("route", i)
		elif k in ("area", "locality"):
			cols.setdefault("area", i)
		elif "location" in k or "landmark" in k:
			cols.setdefault("location", i)
		elif k in ("ownership", "owner", "adoptedby", "caretaker", "adopted"):
			cols.setdefault("owner", i)
	return cols, dates


def _header_row(rows):
	for i, r in enumerate(rows[:10]):
		cols, _d = _columns(r)
		if {"area", "plant"} <= set(cols) and ("location" in cols or "route" in cols):
			return i
	return None


# ───────────────────────────── interpreting a row ─────────────────────────────
def _planting_type(text):
	t = text.lower()
	if "replac" in t:
		return "Replacement"
	if "rescued" in t or "recovered" in t:
		return "Rescued"
	if "previous year" in t or "existing" in t or "lone plant" in t:
		return "Existing"
	return "New"


def _canonical(table, value):
	v = masters.clean(value)
	return table.get(v.lower(), v)


def _list_entry(doctype, written, table, **extra):
	"""Find or add the list entry; a corrected spelling keeps the written one as an other spelling."""
	written = masters.clean(written)
	if not written or written.lower() in masters.PLACEHOLDER:
		return None
	name = _canonical(table, written)
	hit = masters.find(doctype, name) or masters.find(doctype, written)
	if hit:
		return hit
	vals = {"doctype": doctype, masters.FIELD[doctype]: name, "verified": 0}
	if name.lower() != written.lower() and frappe.get_meta(doctype).has_field("aliases"):
		vals["aliases"] = written
	vals.update({k: v for k, v in extra.items() if v and frappe.get_meta(doctype).has_field(k)})
	return frappe.get_doc(vals).insert(ignore_permissions=True).name


def _species(written):
	key = masters.clean(written).lower()
	if key not in SPECIES:
		return masters.ensure("HR Species", written)
	common, botanical = SPECIES[key]
	hit = masters.find("HR Species", common)
	if hit:
		return hit
	return frappe.get_doc({"doctype": "HR Species", "common_name": common, "botanical_name": botanical, "verified": 0,
	                       "aliases": written if key != common.lower() else ""}).insert(ignore_permissions=True).name


_VOLS = None


def _volunteer_for(name):
	"""HR Volunteer when the name matches exactly one active volunteer (titles like Dr / sir ignored)."""
	global _VOLS
	if _VOLS is None:
		_VOLS = frappe.get_all("HR Volunteer", {"active": 1}, ["name", "volunteer_name"])
	words = [w for w in re.split(r"[^a-z]+", name.lower()) if w and w not in ("dr", "sir", "mr", "mrs", "ms", "resident")]
	if not words:
		return None
	key = max(words, key=len)
	hits = [v for v in _VOLS if key in re.split(r"[^a-z]+", (v.volunteer_name or "").lower())]
	return hits[0] if len(hits) == 1 else None


def _caretaker(owner):
	"""(caretaker_type, caretaker_name, volunteer)."""
	owner = masters.clean(owner)
	if not owner:
		return None, None, None
	low = owner.lower()
	if low in CARETAKER_TYPES:
		return CARETAKER_TYPES[low], owner, None
	vol = _volunteer_for(owner)
	if vol:
		return "Volunteer", owner, vol
	return ("Resident" if "resident" in low else "Other"), owner, None


# ───────────────────────────── import ─────────────────────────────
@frappe.whitelist(methods=["POST"])
def import_sheet(file_url=None, preview=1):
	global _VOLS
	if not api._is_admin():
		frappe.throw(_("Only admins can import"), frappe.PermissionError)
	_VOLS = None
	preview = cint(preview)
	out = {"rows": 0, "skipped": 0, "sites": 0, "trees": 0, "waterings": 0, "adopted_trees": 0, "sheets": {},
	       "volunteers": {}, "caretakers": {}, "warnings": [], "new": {}}
	new = {"HR Area": set(), "HR Route": set(), "HR Landmark": set(), "HR Species": set()}
	found_header = False

	for sheet, rows in _sheets(file_url):
		h = _header_row(rows)
		if h is None:
			continue
		found_header = True
		cols, dates = _columns(rows[h])
		if "location" not in cols:       # a filter can rename the Location header
			guess = [i for i in range(len(rows[h])) if i not in cols.values() and i not in dates]
			if guess:
				cols["location"] = guess[0]
		get = lambda r, k: masters.clean(r[cols[k]]) if k in cols and cols[k] < len(r) and r[cols[k]] is not None else ""
		per_sheet = {"rows": 0, "trees": 0}

		for n, r in enumerate(rows[h + 1:], start=h + 2):
			location, area, route, plant = get(r, "location"), get(r, "area"), get(r, "route"), get(r, "plant")
			if not (location or area or plant):
				continue                     # blank or a totals row
			out["rows"] += 1
			per_sheet["rows"] += 1
			count = max(cint(get(r, "count") or 1), 1)
			if count > 50:
				out["warnings"].append(_("{0} row {1}: {2} plants looks wrong, skipped").format(sheet, n, count))
				continue
			key = "%s (%s row %s)" % (MARK, sheet, n)
			if frappe.db.exists("HR Site", {"notes": ["like", key + "%"]}):
				out["skipped"] += 1
				continue
			route = "" if route.lower() in NO_ROUTE else route
			landmark = re.split(r"\s+-\s*|\s*-\s+|,\s*(?=replac|rescued|along with|recovered)", location, maxsplit=1, flags=re.I)[0][:140]
			m = re.search(r"along with ([^()\n]+)", location, flags=re.I)
			companions = m.group(1).strip() if m else ""
			ctype, cname, vol = _caretaker(get(r, "owner"))
			watered = sorted({d for i, d in dates.items() if i < len(r) and r[i] not in (None, "")})

			for dt, val, table in (("HR Area", area, AREAS), ("HR Route", route, ROUTES), ("HR Landmark", landmark, {})):
				canon = _canonical(table, val) if val else ""
				if canon and not masters.find(dt, canon) and not masters.find(dt, val):
					new[dt].add(canon)
			if plant:
				canon = SPECIES.get(plant.lower(), (plant,))[0]
				if not masters.find("HR Species", canon) and not masters.find("HR Species", plant):
					new["HR Species"].add(canon)
			if cname:
				label = ("%s → volunteer %s" % (cname, vol.volunteer_name)) if vol else "%s (%s)" % (cname, ctype)
				out["caretakers"][label] = out["caretakers"].get(label, 0) + count
				if vol:
					out["volunteers"][cname] = vol.volunteer_name
			out["sites"] += 1
			out["trees"] += count
			per_sheet["trees"] += count
			out["adopted_trees"] += count if ctype else 0
			out["waterings"] += count * len(watered)
			if preview:
				continue

			ptype = _planting_type(location)
			area_name = _list_entry("HR Area", area, AREAS)
			route_name = _list_entry("HR Route", route, ROUTES, zone=frappe.db.get_value("HR Area", area_name, "zone") if area_name else None)
			landmark_name = _list_entry("HR Landmark", landmark, {}, area=area_name)
			site = api.add_site({"name": (location or landmark or "Imported spot")[:140], "site_type": "stretch" if count > 1 else "spot",
			                     "tree_count": count, "status": "Completed", "added_by": MARK})
			doc = frappe.get_doc("HR Site", site["site_id"])
			doc.update({"area": area_name, "route": route_name, "landmark": landmark_name, "companion_plants": companions,
			            "notes": "%s: %s%s" % (key, location, (" | %s plants in this row" % count) if count > 1 else "")})
			doc.flags.ignore_duplicate_check = True
			doc.save(ignore_permissions=True)
			species = _species(plant) if plant else None
			for pos in range(1, count + 1):
				t = api.add_tree({"site_id": doc.name, "area": area_name or "", "position": pos, "status": "Completed",
				                  "notes": "%s: %s" % (key, location)})
				frappe.db.set_value("HR Tree", t["tree_id"], {
					"species": species, "planting_type": ptype, "date_planted": None, "gps_status": "Pending",
					"caretaker_type": ctype, "caretaker_name": cname, "owner_volunteer_id": vol.name if vol else None,
				}, update_modified=False)
				for d in watered:
					frappe.get_doc({"doctype": "HR Care Log", "tree": t["tree_id"], "activity": "Watering", "log_date": d,
					                "source": "Import", "notes": MARK, "volunteer": vol.name if vol else None}).insert(ignore_permissions=True)
		out["sheets"][sheet] = per_sheet

	if not found_header:
		frappe.throw(_("Could not find the header row. It needs at least: Area, Plant, and Location or Watering Route."))
	out["new"] = {k: sorted(v) for k, v in new.items() if v}
	if not preview:
		frappe.db.commit()
	return out
