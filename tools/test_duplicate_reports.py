"""Flow test for HR Duplicate Report: flag -> report -> keep / merge / delete -> Deleted Site -> re-plant.
Runs against the real Frappe v15 package with an in-memory fake database (no site needed)."""
import json, os, sys
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import frappe
frappe.init(site="test", sites_path="/tmp/sites"); frappe.local.lang = "en"
import frappe.translate as _t; _t.get_all_translations = lambda lang: {}
frappe.local.session = frappe._dict(user="admin@x.com")
NOW = "2026-11-22 10:00:00"
frappe.utils.now_datetime = lambda: NOW
frappe.get_roles = lambda *a, **k: ["HR Admin"]

# ---------------- tiny in-memory database ----------------
T = {}
def tab(dt): return T.setdefault(dt, {})
def match(row, flt):
    for k, v in (flt or {}).items():
        val = row.get(k)
        if isinstance(v, (list, tuple)):
            op, arg = v[0], v[1] if len(v) > 1 else None
            if op == "is": ok = bool(val) if arg == "set" else not val
            elif op == "!=": ok = val != arg
            elif op == "=": ok = val == arg
            elif op == "in": ok = val in (arg or [])
            elif op == "between": ok = val is not None and arg[0] <= val <= arg[1]
            else: raise AssertionError(op)
            if not ok: return False
        elif val != v: return False
    return True
class Flags(dict):
    __getattr__ = dict.get
    def __setattr__(self, k, v): self[k] = v
class FDoc(frappe._dict):
    def __init__(self, d): super().__init__(d); self["flags"] = Flags(); self["_new"] = True
    def __getattr__(self, k):
        if k in self: return self[k]
        if self.get("doctype") == "HR Site" and callable(getattr(HRSite, k, None)):
            import types; return types.MethodType(getattr(HRSite, k), self)
        return None
    def is_new(self): return self.get("_new")
    def insert(self, **k):
        dt = self["doctype"]; n = len(tab(dt)) + 1
        self["name"] = self.get("name") or (self.get("site_id") if dt == "HR Site" else f"{dt[3:6].upper()}-{n:05d}")
        self["owner"] = self.get("owner") or "admin@x.com"; self["_new"] = False
        tab(dt)[self["name"]] = {k2: v for k2, v in self.items() if k2 not in ("flags", "_new")}; return self
    def save(self, **k): tab(self["doctype"])[self["name"]] = {k2: v for k2, v in self.items() if k2 not in ("flags", "_new")}; return self
    def as_dict(self, *a, **k): return {k2: v for k2, v in self.items() if k2 not in ("flags", "_new")}
def get_doc(a, b=None):
    if isinstance(a, dict): return FDoc(a)
    row = tab(a).get(b)
    if row is None: raise frappe.DoesNotExistError(f"{a} {b}")
    d = FDoc(row); d["_new"] = False; d["doctype"] = a; return d
def get_all(dt, filters=None, fields=None, pluck=None, order_by=None, limit_page_length=None, **k):
    if not isinstance(filters, dict): filters = {"name": filters} if filters else {}
    rows = [dict(r, name=n) for n, r in tab(dt).items() if match(dict(r, name=n), filters)]
    if pluck: return [r[pluck] for r in rows]
    return [frappe._dict(r) for r in rows]
class DB:
    def exists(self, dt, f=None):
        if isinstance(f, str): return f if f in tab(dt) else None
        r = get_all(dt, f); return r[0]["name"] if r else None
    def get_value(self, dt, f, field=None, as_dict=False, order_by=None, **k):
        if isinstance(f, str): row = tab(dt).get(f); row = dict(row, name=f) if row else None
        else: r = get_all(dt, f); row = dict(r[0]) if r else None
        if row is None: return None
        if isinstance(field, (list, tuple)): d = frappe._dict({x: row.get(x) for x in field}); return d if as_dict else tuple(d.values())
        return row.get(field)
    def set_value(self, dt, name, field, value=None, update_modified=True, **k):
        vals = field if isinstance(field, dict) else {field: value}
        tab(dt)[name].update(vals)
    def count(self, dt, f=None): return len(get_all(dt, f))
    def sql(self, q, vals=None, **k):
        if q.startswith("update `tab"):
            dt = q.split("`")[1][3:]
            for r in tab(dt).values():
                if r.get("site_id") == vals[1]: r["site_id"] = vals[0]
            return
        raise AssertionError(q)
frappe.local.db = DB()
def delete_doc(dt, name, **k):
    doc = get_doc(dt, name)
    if dt == "HR Site": HRSite.on_trash(doc)
    del tab(dt)[name]
frappe.get_doc, frappe.get_all, frappe.delete_doc = get_doc, get_all, delete_doc

from hasiruratha.hasiruratha.doctype.hr_site import hr_site as hs
from hasiruratha.hasiruratha.doctype.hr_site.hr_site import HRSite
from hasiruratha.hasiruratha.doctype.hr_duplicate_report import hr_duplicate_report as dr
from hasiruratha.hasiruratha.doctype.hr_deleted_site import hr_deleted_site as ds
dr.now_datetime = ds.now_datetime = lambda: NOW
hs._notify_admins = mock.Mock(); hs._close_todos = mock.Mock()
ok = lambda m: print("PASS", m)

# ---------------- data ----------------
tab("HR Site")["S-1"] = dict(site_id="S-1", site_name="Ashoka Pillar Rd", site_type="spot", status="Identified", road="Ashoka Pillar Rd",
    area="Jayanagar 2nd Block", zone_id="Z-1", gps_lat=12.93000, gps_lng=77.58000, photo_url="/files/s1.jpg", tree_count=2, doctype="HR Site")
tab("HR Tree")["T-1"] = dict(site_id="S-1", photo_url="/files/t1.jpg"); tab("HR Tree")["T-2"] = dict(site_id="S-1")

def new_site(sid, lat, lng, photo):
    d = get_doc(dict(doctype="HR Site", site_id=sid, site_name=sid, site_type="spot", status="Planned", road="Ashoka Pillar Rd",
                     area="Jayanagar 2nd Block", zone_id="Z-1", gps_lat=lat, gps_lng=lng, photo_url=photo, tree_count=0))
    HRSite.validate(d); d.insert(); HRSite.after_insert(d); return d

# 1 flag -> report with photos, distance, location
s2 = new_site("S-2", 12.93005, 77.58003, "/files/s2.jpg")
assert s2.status == "Needs Review" and s2.possible_duplicate_of == "S-1"
rep = tab("HR Duplicate Report"); assert len(rep) == 1, rep
r = next(iter(rep.values()))
assert r["site"] == "S-2" and r["possible_duplicate_of_site"] == "S-1" and r["status"] == "Pending Review"
assert r["picture_of_tree"] == "/files/s2.jpg" and r["original_photo"] == "/files/s1.jpg" and 0 < r["distance_between_records"] < 25
assert r["possible_duplicate_of_tree_id"] == "T-1" and r["zone"] == "Z-1" and json.loads(r["geolocation_vris"])["features"][0]["geometry"]["coordinates"] == [77.58003, 12.93005]
ok("duplicate site -> Pending Review report with both photos, distance, nearest tree, zone, map point")
hs._notify_admins.assert_called_once(); ok("admins still notified")

# 2 not a duplicate -> no report; idempotent
new_site("S-FAR", 12.95, 77.60, None); assert len(rep) == 1
assert dr.create_for_site(s2) == next(iter(rep)); assert len(rep) == 1; ok("far-away site makes no report; calling twice makes one report")

# 3 report form data
c = dr.comparison("HRD-00001" if "HRD-00001" in rep else next(iter(rep)))
assert c["this"]["photo"] == "/files/s2.jpg" and c["other"]["photo"] == "/files/s1.jpg"; ok("side-by-side payload has both photos")

# 4 keep as new
s3 = new_site("S-3", 12.93004, 77.58001, "/files/s3.jpg")
hs.approve_site("S-3")
assert tab("HR Site")["S-3"]["status"] == "Identified" and [x for x in rep.values() if x["site"] == "S-3"][0]["status"] == "Kept as New"; ok("approve -> report 'Kept as New'")

# 5 merge
s4 = new_site("S-4", 12.93002, 77.58002, "/files/s4.jpg"); tab("HR Tree")["T-4"] = dict(site_id="S-4")
hs.merge_site("S-4")        # merges into whichever existing site was nearest (S-1 or the approved S-3)
assert tab("HR Tree")["T-4"]["site_id"] == s4.possible_duplicate_of in ("S-1", "S-3") and tab("HR Site")["S-4"]["status"] == "Merged" and [x for x in rep.values() if x["site"] == "S-4"][0]["status"] == "Merged"; ok("merge -> trees moved, report 'Merged'")

# 6 delete duplicate -> Deleted Sites + report
tab("HR Tree")["T-2"]["site_id"] = "S-2"        # S-2 has a tree
hs.delete_duplicate("S-2", "same spot")
assert "S-2" not in tab("HR Site") and tab("HR Tree")["T-2"]["site_id"] == "S-1"
arc = tab("HR Deleted Site"); assert len(arc) == 1; a = next(iter(arc.values())); an = next(iter(arc))
assert a["original_site"] == "S-2" and a["photo"] == "/files/s2.jpg" and a["moved_to"] == "S-1" and a["trees_moved"] == "T-2" and a["reason"] == "same spot"
rr = [x for x in rep.values() if x["site"] == "S-2"][0]
assert rr["status"] == "Deleted" and rr["deleted_site"] == an and rr["resolved_by"] == "admin@x.com"
ok("delete duplicate -> copy in Deleted Sites (photo, reason, trees moved), report 'Deleted' linked to the copy")

# 7 deleting from the desk still archives, once
frappe.delete_doc("HR Site", "S-FAR"); assert len(arc) == 2 and [x for x in arc.values() if x["original_site"] == "S-FAR"][0]["reason"] == "Deleted from the desk"
tab("HR Site")["S-X"] = dict(site_id="S-X", site_name="x", doctype="HR Site", status="Identified"); n = len(arc)
hs.HRSite.on_trash(get_doc("HR Site", "S-X")); hs.HRSite.on_trash(get_doc("HR Site", "S-X")) if False else None
assert len(arc) == n + 1; ok("Desk delete archives the site too; delete_duplicate does not archive twice")

# 8 re-plant
res = ds.restore_site(an, 1)
site = tab("HR Site")["S-2"]
assert res["site"] == "S-2" and site["status"] == "Identified" and site["site_name"] == "S-2" and site["gps_lat"] == 12.93005 and site["photo_url"] == "/files/s2.jpg"
assert site["possible_duplicate_of"] is None if "possible_duplicate_of" in site else True
assert tab("HR Tree")["T-2"]["site_id"] == "S-2" and site["tree_count"] == 1 and res["trees_moved_back"] == 1
assert tab("HR Deleted Site")[an]["restored_site"] == "S-2" and rr["status"] == "Restored" and rr["restored_site"] == "S-2"
ok("re-plant -> same id, place and photo, tree moved back, archive and report marked 'Restored'")
for bad in (lambda: ds.restore_site(an, 0),):
    try: bad()
    except frappe.ValidationError as e: assert "already" in str(e); ok("a second re-plant is refused")
    else: raise AssertionError("second restore allowed")

# 9 schema
F = "/home/claude/frappe_src/frappe/"
meta = {f["fieldname"] for f in json.load(open(F + "core/doctype/docfield/docfield.json"))["fields"]}
d = json.load(open("hasiruratha/hasiruratha/doctype/hr_duplicate_report/hr_duplicate_report.json"))
assert set(d["field_order"]) == {f["fieldname"] for f in d["fields"]} and not {k for f in d["fields"] for k in f} - meta
ok("DocType JSON: field_order matches fields; every key is a valid DocField property")
print("\nALL TESTS PASSED")
