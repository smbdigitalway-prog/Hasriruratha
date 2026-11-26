"""Public, read-only marker API for the citizen tree/site map."""
import json
import frappe

PAIR_PRIORITY = (("gps_lat", "gps_lng"), ("latitude", "longitude"), ("lat", "lng"), ("gps_latitude", "gps_longitude"))
GEO_FIELDS = {"location", "geolocation", "gps_location", "geo_location", "map_location"}
NAME_FIELDS = ("tree_id", "site_name", "site_id", "title", "name")
AREA_FIELDS = ("area", "area_name", "locality", "road", "road_name", "address", "address_full")
STATUS_FIELDS = ("status", "tree_status", "status_of_tree", "tree_condition", "condition")


def _first(meta, candidates):
    names = {df.fieldname for df in meta.fields}
    return next((f for f in candidates if f in names), None)


def _coordinate_pairs(meta):
    fields = {df.fieldname: df for df in meta.fields}
    pairs = []
    for latf, lngf in PAIR_PRIORITY:
        lat, lng = fields.get(latf), fields.get(lngf)
        if lat and lng and lat.fieldtype in ("Float", "Int", "Data") and lng.fieldtype in ("Float", "Int", "Data"):
            pairs.append((latf, lngf))
    geof = next((df.fieldname for df in meta.fields if df.fieldtype == "Geolocation" and (df.fieldname or "").lower() in GEO_FIELDS), None)
    return pairs, geof


def _geo_coords(value):
    try:
        obj = json.loads(value) if isinstance(value, str) else value
        if isinstance(obj, dict):
            for feature in obj.get("features", []):
                geom = feature.get("geometry") or {}
                if geom.get("type") == "Point":
                    coords = geom.get("coordinates") or []
                    if len(coords) >= 2: return float(coords[1]), float(coords[0])
            if obj.get("type") == "Point":
                coords = obj.get("coordinates") or []
                if len(coords) >= 2: return float(coords[1]), float(coords[0])
    except (TypeError, ValueError, json.JSONDecodeError): pass
    return None, None


def _valid(lat, lng): return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180


def _markers(doctype, kind, limit=3000):
    if not frappe.db.exists("DocType", doctype): return []
    meta=frappe.get_meta(doctype); pairs, geof=_coordinate_pairs(meta)
    titlef=_first(meta, NAME_FIELDS); areaf=_first(meta, AREA_FIELDS); statusf=_first(meta, STATUS_FIELDS)
    if not pairs and not geof: return []
    fields=["name"]
    for pair in pairs:
        for f in pair:
            if f not in fields: fields.append(f)
    for f in (geof,titlef,areaf,statusf):
        if f and f not in fields: fields.append(f)
    try: rows=frappe.get_all(doctype,fields=fields,limit_page_length=limit,order_by="modified desc")
    except Exception:
        frappe.log_error(f"Citizen map query failed for {doctype}","Citizen Map API"); return []
    out=[]
    for row in rows:
        lat=lng=None
        for latf,lngf in pairs:
            try:
                if row.get(latf) not in (None,"") and row.get(lngf) not in (None,""):
                    a,b=float(row.get(latf)),float(row.get(lngf))
                    if _valid(a,b): lat,lng=a,b; break
            except (TypeError,ValueError): pass
        if (lat is None or lng is None) and geof: lat,lng=_geo_coords(row.get(geof))
        if not _valid(lat,lng): continue
        title=str(row.get(titlef) or row.name) if titlef else row.name
        out.append({"id":row.name,"doctype":doctype,"kind":kind,"title":title,"tree_id":str(row.get(titlef) or row.name) if kind=="tree" else "","area":str(row.get(areaf) or "") if areaf else "","status":str(row.get(statusf) or "") if statusf else "","lat":lat,"lng":lng})
    return out


@frappe.whitelist(allow_guest=True)
def get_tree_markers():
    markers=[]
    for doctype,kind in (("HR Tree","tree"),("HR Site","site")):
        markers.extend(_markers(doctype,kind))
    return {"markers":markers[:6000]}
