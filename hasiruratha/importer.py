# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Import the volunteers' watering spreadsheet (.xlsx or .csv).

Expected columns (names are matched loosely, order does not matter):
  # Plants | Area | Watering Route | Location | Plant | <one column per date>

Each row becomes:
  * a Spot (1 plant) or a Stretch (several plants), named after the Location text, with its Area,
    Watering Route and Landmark (all added to the lists as Unverified when new)
  * one Tree per plant, species from "Plant", GPS pending (volunteers add it with the phone app)
  * planting type from the text: "replac..." -> Replacement, "rescued" -> Rescued,
    "previous year" / "existing" / "lone plant" -> Existing, otherwise New
  * "along with ..." -> companion plants (noted, not counted)
  * every filled date cell -> a Watering entry in the care log for each tree of the row

Rows already imported (same location, area and route) are skipped, so the file can be imported again.
preview=1 changes nothing and reports what would happen.
"""
import csv
import io
import re
from datetime import date, datetime

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hasiruratha import api, masters

MARK = "Imported from the watering sheet"
SPECIES = {   # common spellings -> (name, botanical name)
	"honge": ("Honge", "Pongamia pinnata"), "mahogony": ("Mahogany", "Swietenia mahagoni"),
	"mahogany": ("Mahogany", "Swietenia mahagoni"), "kadamba": ("Kadamba", "Neolamarckia cadamba"),
	"pipal": ("Pipal", "Ficus religiosa"), "peepal": ("Pipal", "Ficus religiosa"),
	"banyan": ("Banyan", "Ficus benghalensis"), "halasu": ("Halasu", "Artocarpus heterophyllus"),
	"sampige": ("Sampige", "Magnolia champaca"), "bakula": ("Bakula", "Mimusops elengi"),
}


def _cells(file_url):
	f = frappe.get_doc("File", {"file_url": file_url})
	content = f.get_content()
	name = (f.file_name or file_url).lower()
	if name.endswith(".csv"):
		text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
		return [row for row in csv.reader(io.StringIO(text))]
	from openpyxl import load_workbook

	wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
	return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]


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
	return cols, dates


def _planting_type(text):
	t = text.lower()
	if "replac" in t:
		return "Replacement"
	if "rescued" in t:
		return "Rescued"
	if "previous year" in t or "existing" in t or "lone plant" in t:
		return "Existing"
	return "New"


def _species(name):
	key = masters.clean(name).lower()
	if key in SPECIES:
		common, botanical = SPECIES[key]
		hit = masters.find("HR Species", common)
		if not hit:
			hit = frappe.get_doc({"doctype": "HR Species", "common_name": common, "botanical_name": botanical,
			                      "verified": 0, "aliases": name if name.lower() != common.lower() else ""}).insert(
				ignore_permissions=True).name
		return hit
	return masters.ensure("HR Species", name)


def _header_row(rows):
	for i, r in enumerate(rows[:10]):
		cols, _d = _columns(r)
		if {"area", "plant"} <= set(cols) and ("location" in cols or "route" in cols):
			return i
	frappe.throw(_("Could not find the header row. It needs at least: Area, Plant, and Location or Watering Route."))


@frappe.whitelist(methods=["POST"])
def import_sheet(file_url=None, preview=1):
	if not api._is_admin():
		frappe.throw(_("Only admins can import"), frappe.PermissionError)
	rows = _cells(file_url)
	h = _header_row(rows)
	cols, dates = _columns(rows[h])
	if "location" not in cols:      # the second sample had the Location header renamed by a filter
		guess = [i for i in range(len(rows[h])) if i not in cols.values() and i not in dates]
		if guess:
			cols["location"] = guess[0]
	preview = cint(preview)
	get = lambda r, k: masters.clean(r[cols[k]]) if k in cols and cols[k] < len(r) and r[cols[k]] is not None else ""
	out = {"rows": 0, "skipped": 0, "sites": 0, "trees": 0, "waterings": 0, "warnings": [], "new": {}}
	new = {"HR Area": set(), "HR Route": set(), "HR Landmark": set(), "HR Species": set()}

	for n, r in enumerate(rows[h + 1:], start=h + 2):
		if not any(c not in (None, "") for c in r):
			continue
		location, area, route, plant = get(r, "location"), get(r, "area"), get(r, "route"), get(r, "plant")
		if not (location or area or plant):
			continue
		out["rows"] += 1
		count = max(cint(get(r, "count") or 1), 1)
		if count > 50:
			out["warnings"].append(_("Row {0}: {1} plants looks wrong, skipped").format(n, count))
			continue
		landmark = re.split(r"\s+-\s+|,\s*(?=replac|rescued|along with)", location, maxsplit=1, flags=re.I)[0][:140]
		companions = ""
		m = re.search(r"along with ([^()\n]+)", location, flags=re.I)
		if m:
			companions = m.group(1).strip()
		watered = sorted({d for i, d in dates.items() if i < len(r) and r[i] not in (None, "")})
		for dt, val in (("HR Area", area), ("HR Route", route), ("HR Landmark", landmark), ("HR Species", plant)):
			if val and not masters.find(dt, val) and not (dt == "HR Species" and masters.clean(val).lower() in SPECIES
			                                                 and masters.find(dt, SPECIES[masters.clean(val).lower()][0])):
				new[dt].add(SPECIES.get(masters.clean(val).lower(), (val,))[0] if dt == "HR Species" else val)
		if frappe.db.exists("HR Site", {"site_name": (location or landmark)[:140], "area": masters.find("HR Area", area) or area,
		                                "route": masters.find("HR Route", route) or route}):
			out["skipped"] += 1
			continue
		out["sites"] += 1
		out["trees"] += count
		out["waterings"] += count * len(watered)
		if preview:
			continue

		ptype = _planting_type(location)
		site = api.add_site({"name": (location or landmark or "Imported spot")[:140], "site_type": "stretch" if count > 1 else "spot",
		                     "tree_count": count, "status": "Completed", "added_by": MARK})
		doc = frappe.get_doc("HR Site", site["site_id"])
		doc.update({"area": area or None, "route": route or None, "landmark": landmark or None,
		            "companion_plants": companions, "notes": "%s (row %s): %s" % (MARK, n, location)})
		doc.flags.ignore_duplicate_check = True
		doc.save(ignore_permissions=True)
		species = _species(plant) if plant else None
		for pos in range(1, count + 1):
			t = api.add_tree({"site_id": doc.name, "area": area, "position": pos, "status": "Completed",
			                  "notes": "%s (row %s)" % (MARK, n)})
			frappe.db.set_value("HR Tree", t["tree_id"], {"species": species, "planting_type": ptype, "date_planted": None,
			                                             "gps_status": "Pending"}, update_modified=False)
			for d in watered:
				frappe.get_doc({"doctype": "HR Care Log", "tree": t["tree_id"], "activity": "Watering", "log_date": d,
				                "source": "Import", "notes": MARK}).insert(ignore_permissions=True)
	out["new"] = {k: sorted(v) for k, v in new.items() if v}
	if not preview:
		frappe.db.commit()
	return out
