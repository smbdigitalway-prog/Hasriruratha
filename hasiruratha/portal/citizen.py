"""Citizen side of Plant a Tree / Report a Tree (your own doctypes, found through the Web Form routes).

Public (visitors can look at the map):  trees_in_view, nearby, tree_info, free_spot
Logged-in only:                          submit
Field names are detected from the doctype, and the extra questions (how many, what is wrong...) come from the
Web Form's own field list, so the page follows whatever you configure there.
"""
import base64
import math

import frappe
from frappe import _
from frappe.utils import cint, flt

FORMS = {"plant": ("plant-a-tree", "HR Citizen Planting", "/my-trees"),
         "report": ("report-a-tree", "HR Citizen Report", "/my-reports")}
DUP_M, FREE_GAP_M, MAX_PHOTO = 20, 25, 3 * 1024 * 1024
LAT, LNG = ("gps_lat", "latitude", "lat"), ("gps_lng", "longitude", "lng")
SKIP = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect", "Heading",
        "Fold", "Geolocation", "Password", "Code", "JSON", "Attach", "Attach Image", "Image", "Read Only"}
CAND = {"lat": LAT, "lng": LNG, "acc": ("gps_accuracy_m", "gps_accuracy", "accuracy"), "src": ("location_source",),
        "road": ("road", "street", "road_name"), "area": ("area", "locality"), "landmark": ("landmark",),
        "pin": ("pincode", "pin_code"), "addr": ("address_line", "address", "location_text"),
        "tree": ("related_tree", "tree", "tree_id"), "dup": ("possible_duplicate",), "new": ("citizen_says_new",)}


def _doctype(kind):
    route, fallback, _n = FORMS[kind]
    return frappe.db.get_value("Web Form", {"route": route}, "doc_type") or fallback


def _pick(doctype, names):
    if not frappe.db.exists("DocType", doctype):
        return None
    meta = frappe.get_meta(doctype)
    return next((n for n in names if meta.has_field(n)), None)


def _map(doctype, kind):
    m = {k: _pick(doctype, v) for k, v in CAND.items()}
    if kind != "report":
        m["tree"] = None
    meta = frappe.get_meta(doctype)
    m["photo"] = next((f.fieldname for f in meta.fields if f.fieldtype in ("Attach Image", "Attach")), None)
    return m


def _label_field(doctype):
    meta = frappe.get_meta(doctype)
    return meta.title_field or _pick(doctype, ("site_name", "road_name", "area_name", "landmark_name", "name1", "title"))


def form_def(kind):
    """What the page needs to know: which special fields exist, and the extra questions to ask."""
    dt = _doctype(kind)
    meta, m = frappe.get_meta(dt), _map(dt, kind)
    special = {v for v in m.values() if v}
    extras = []
    wf = frappe.db.get_value("Web Form", {"route": FORMS[kind][0]}, "name")
    rows = frappe.get_doc("Web Form", wf).web_form_fields if wf else []
    for r in rows:
        fn = r.fieldname
        if not fn or fn in special or r.fieldtype in SKIP or r.get("hidden") or r.get("read_only"):
            continue
        item = {"fieldname": fn, "label": r.label or fn.replace("_", " ").title(), "fieldtype": r.fieldtype,
                "reqd": cint(r.reqd), "help": r.get("description") or "", "options": []}
        if r.fieldtype == "Select":
            item["options"] = [o.strip() for o in (r.options or "").split("\n") if o.strip()]
        elif r.fieldtype == "Link" and r.options and frappe.db.exists("DocType", r.options):
            lf = _label_field(r.options)
            rows_ = frappe.get_all(r.options, fields=["name"] + ([lf] if lf and lf != "name" else []), limit_page_length=200,
                                   ignore_permissions=True)
            item["options"] = [{"v": x.name, "l": x.get(lf) or x.name} for x in rows_]
        extras.append(item)
    return {"kind": kind, "doctype": dt, "next": FORMS[kind][2], "extras": extras,
            "has": {"address": bool(m["addr"]), "landmark": bool(m["landmark"]), "tree": bool(m["tree"])}}


# ---------- map data ----------
def _dist_m(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


def _box(doctype, s, w, n, e, extra, limit=400):
    la, ln = _pick(doctype, LAT), _pick(doctype, LNG)
    if not (la and ln):
        return []
    fields = ["name", f"{la} as lat", f"{ln} as lng"]
    for alias, cands in extra.items():
        f = _pick(doctype, cands)
        if f:
            fields.append(f"{f} as {alias}")
    rows = frappe.get_all(doctype, filters=[[la, "between", [s, n]], [ln, "between", [w, e]]], fields=fields,
                          limit_page_length=limit, ignore_permissions=True)
    return [r for r in rows if r.lat and r.lng]


TREE_X = {"species": ("species", "tree_species"), "status": ("status",), "photo": ("photo_url", "photo", "image")}


def _sites_x():
    return {"label": (_label_field("HR Site") or "name",), "tree_count": ("tree_count",)}


@frappe.whitelist(allow_guest=True)
def trees_in_view(south, west, north, east):
    s, w, n, e = flt(south), flt(west), flt(north), flt(east)
    if (n - s) > 0.08 or (e - w) > 0.08:
        return {"too_wide": True, "trees": [], "sites": []}
    sites = _box("HR Site", s, w, n, e, _sites_x(), 300) if frappe.db.exists("DocType", "HR Site") else []
    return {"trees": _box("HR Tree", s, w, n, e, TREE_X), "sites": sites}


def _around(lat, lng, radius):
    d = radius / 111320.0
    dl = radius / (111320.0 * max(math.cos(math.radians(lat)), 0.01))
    out = {"trees": [], "sites": []}
    out["trees"] = _box("HR Tree", lat - d, lng - dl, lat + d, lng + dl, TREE_X)
    if frappe.db.exists("DocType", "HR Site"):
        out["sites"] = _box("HR Site", lat - d, lng - dl, lat + d, lng + dl, _sites_x())
    for k in out:
        for r in out[k]:
            r["distance_m"] = round(_dist_m(lat, lng, flt(r.lat), flt(r.lng)))
        out[k] = sorted([r for r in out[k] if r["distance_m"] <= radius], key=lambda r: r["distance_m"])[:30]
    return out


@frappe.whitelist(allow_guest=True)
def nearby(lat, lng, radius_m=150):
    return _around(flt(lat), flt(lng), min(flt(radius_m) or 150, 500))


@frappe.whitelist(allow_guest=True)
def tree_info(name):
    la, ln = _pick("HR Tree", LAT), _pick("HR Tree", LNG)
    if not (la and ln) or not frappe.db.exists("HR Tree", name):
        return None
    d = frappe.db.get_value("HR Tree", name, [la, ln], as_dict=True)
    r = frappe._dict(name=name, lat=d[la], lng=d[ln])
    for alias, cands in TREE_X.items():
        f = _pick("HR Tree", cands)
        r[alias] = frappe.db.get_value("HR Tree", name, f) if f else None
    return r


@frappe.whitelist(allow_guest=True)
def free_spot(lat, lng, gap_m=FREE_GAP_M):
    """Nearest point to (lat, lng) with no registered tree or spot within gap_m. Rings of 8 m up to 120 m."""
    lat, lng, gap = flt(lat), flt(lng), flt(gap_m) or FREE_GAP_M
    around = _around(lat, lng, 250)
    pts = [(flt(r.lat), flt(r.lng)) for k in around for r in around[k]]
    names = ["east", "north-east", "north", "north-west", "west", "south-west", "south", "south-east"]
    for ring in range(0, 121, 8):
        steps = 1 if ring == 0 else 16
        for i in range(steps):
            a = 2 * math.pi * i / steps
            la = lat + (ring * math.sin(a)) / 111320.0
            ln = lng + (ring * math.cos(a)) / (111320.0 * max(math.cos(math.radians(lat)), 0.01))
            if all(_dist_m(la, ln, p, q) >= gap for p, q in pts):
                return {"found": True, "lat": la, "lng": ln, "moved_m": ring, "direction": names[round(a / (math.pi / 4)) % 8] if ring else "",
                        "gap_m": gap}
    return {"found": False}


# ---------- submit ----------
def _match(doctype, text):
    text = (text or "").strip()
    if not text or not frappe.db.exists("DocType", doctype):
        return None
    if frappe.db.exists(doctype, text):
        return text
    label = _label_field(doctype)
    if label:
        hit = frappe.db.get_value(doctype, {label: text}, "name")
        if hit:
            return hit
        like = frappe.get_all(doctype, filters={label: ["like", f"%{text}%"]}, pluck="name", limit_page_length=2)
        if len(like) == 1:
            return like[0]
    return None


def _save_photo(data_url):
    if not data_url or "," not in data_url or "image/" not in data_url.split(",", 1)[0]:
        frappe.throw(_("Please add a photo"))
    raw = base64.b64decode(data_url.split(",", 1)[1])
    if len(raw) > MAX_PHOTO:
        frappe.throw(_("The photo is too large. Please try another one."))
    f = frappe.get_doc({"doctype": "File", "file_name": f"{frappe.generate_hash(length=8)}.jpg", "is_private": 0, "content": raw})
    f.insert(ignore_permissions=True)
    return f


@frappe.whitelist()
def submit(kind, data):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to send your request"), frappe.PermissionError)
    if kind not in FORMS:
        frappe.throw(_("Unknown form"))
    d = frappe.parse_json(data)
    lat, lng = flt(d.get("lat")), flt(d.get("lng"))
    if not (lat and lng):
        frappe.throw(_("Set the location first"))
    dt = _doctype(kind)
    meta, m, fdef = frappe.get_meta(dt), _map(dt, kind), form_def(kind)
    photo = _save_photo(d.get("photo"))

    doc = frappe.new_doc(dt)

    def put(key, value):
        if m.get(key) and value not in (None, ""):
            doc.set(m[key], value)

    put("lat", lat); put("lng", lng)
    put("acc", cint(d.get("acc")) if d.get("src") == "GPS" else None)
    put("src", "GPS" if d.get("src") == "GPS" else "Map pin")
    put("pin", (d.get("pincode") or "").strip())
    put("tree", d.get("tree"))
    put("new", cint(d.get("says_new")))
    leftovers = []
    for key, link in (("road", "HR Road"), ("area", "HR Area"), ("landmark", "HR Landmark")):
        text = (d.get(key) or "").strip()
        if not text or not m.get(key):
            leftovers.append(text) if text else None
            continue
        if meta.get_field(m[key]).fieldtype == "Link":
            hit = _match(link, text)
            if hit:
                doc.set(m[key], hit)
            else:
                leftovers.append(text)      # not in your list: keep the text so the team can link it
        else:
            doc.set(m[key], text)
    addr = ", ".join(x for x in [(d.get("address") or "").strip()] + leftovers if x)
    put("addr", addr)

    near = _around(lat, lng, DUP_M)
    put("dup", 1 if kind == "plant" and (near["trees"] or near["sites"]) else 0)

    allowed = {e["fieldname"]: e for e in fdef["extras"]}
    for fn, val in (d.get("extra") or {}).items():
        e = allowed.get(fn)
        if not e or val in (None, ""):
            continue
        t = e["fieldtype"]
        doc.set(fn, cint(val) if t in ("Check", "Int") else flt(val) if t in ("Float", "Currency", "Percent") else val)

    if m["photo"]:
        doc.set(m["photo"], photo.file_url)
    doc.insert(ignore_permissions=True)          # created as the logged-in citizen, so it shows under My trees / My reports
    frappe.db.set_value("File", photo.name, {"attached_to_doctype": dt, "attached_to_name": doc.name,
                                             "attached_to_field": m["photo"] or None})
    return {"name": doc.name, "next": FORMS[kind][2], "duplicate": bool(near["trees"] or near["sites"])}
