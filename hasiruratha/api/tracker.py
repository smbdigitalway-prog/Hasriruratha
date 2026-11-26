"""Citizen tracking API: returns only the logged-in citizen's own reports / plantings with status history.

Works for any field layout: the status steps are read from the doctype's own Status (Select) options,
and the Web Form route decides which doctype is used, so nothing is hard-coded to field names.
"""
import json

import frappe
from frappe import _

# kind -> (web form route, fallback doctype)
FORMS = {
    "report": ("report-a-tree", "HR Citizen Report"),
    "plant": ("plant-a-tree", "HR Citizen Planting"),
}

SKIP_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table",
              "Table MultiSelect", "Heading", "Fold", "Geolocation", "Password", "Code", "JSON"}
STATUS_KEYS = ("status", "workflow_state", "state")
TITLE_KEYS = ("problem", "issue", "problem_type", "report_type", "title", "subject", "species",
              "tree_species", "sapling", "sapling_type", "tree_type")
AREA_KEYS = ("area", "road", "locality", "location", "site", "address")
ID_KEYS = ("tree_id", "tree", "site", "spot")
NEGATIVE = ("reject", "cancel", "duplicate", "declin", "invalid", "withdraw")


def _doctype(kind):
    route, fallback = FORMS[kind]
    return frappe.db.get_value("Web Form", {"route": route}, "doc_type") or fallback


def _first(fields, keys, types=None):
    by_name = {f.fieldname: f for f in fields}
    for k in keys:
        f = by_name.get(k)
        if f and (not types or f.fieldtype in types):
            return f
    return None


def _usable_fields(meta):
    out = []
    for f in meta.fields:
        if f.fieldtype in SKIP_TYPES or f.hidden or (f.permlevel or 0) > 0 or not f.fieldname:
            continue
        out.append(f)
    return out


def _status_history(doctype, name, status_field):
    """[(status, datetime)] from Version log (needs 'Track Changes' on the doctype); [] if not available."""
    out = []
    try:
        for v in frappe.get_all("Version", filters={"ref_doctype": doctype, "docname": name},
                                fields=["data", "creation"], order_by="creation asc", limit_page_length=100):
            data = json.loads(v.data or "{}")
            for ch in data.get("changed", []):
                if ch and ch[0] == status_field and ch[2]:
                    out.append({"status": ch[2], "on": str(v.creation)})
    except Exception:
        pass
    return out


@frappe.whitelist()
def get_my_items(kind):
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in to see your submissions"), frappe.PermissionError)
    if kind not in FORMS:
        frappe.throw(_("Unknown kind"))

    doctype = _doctype(kind)
    if not frappe.db.exists("DocType", doctype):
        return {"doctype": doctype, "items": [], "steps": [], "negative": []}

    meta = frappe.get_meta(doctype)
    fields = _usable_fields(meta)
    status_f = _first(fields, STATUS_KEYS, ("Select", "Data", "Link"))
    title_f = _first(fields, TITLE_KEYS)
    area_f = _first(fields, AREA_KEYS)
    id_f = _first(fields, ID_KEYS, ("Link", "Data"))
    photo_f = next((f for f in fields if f.fieldtype in ("Attach Image", "Attach")), None)

    steps, negative = [], []
    if status_f and status_f.fieldtype == "Select":
        for o in (status_f.options or "").split("\n"):
            o = o.strip()
            if not o:
                continue
            (negative if any(n in o.lower() for n in NEGATIVE) else steps).append(o)

    shown = {f.fieldname for f in (status_f, title_f, area_f, id_f, photo_f) if f}
    extra = [f for f in fields if f.fieldname not in shown][:8]

    wanted = {"name", "creation", "modified"} | shown | {f.fieldname for f in extra}
    rows = frappe.get_all(doctype, filters={"owner": frappe.session.user},
                          fields=sorted(wanted), order_by="creation desc", limit_page_length=200)

    items = []
    for r in rows:
        status = r.get(status_f.fieldname) if status_f else None
        history = _status_history(doctype, r.name, status_f.fieldname) if status_f else []
        if not history and status:
            history = [{"status": status, "on": str(r.modified)}]
        details = []
        for f in extra:
            v = r.get(f.fieldname)
            if v in (None, "", 0):
                continue
            details.append({"label": _(f.label or f.fieldname), "value": "Yes" if f.fieldtype == "Check" else str(v)})
        items.append({
            "name": r.name,
            "title": (r.get(title_f.fieldname) if title_f else None) or r.name,
            "area": r.get(area_f.fieldname) if area_f else None,
            "tree_id": r.get(id_f.fieldname) if id_f else None,
            "photo": r.get(photo_f.fieldname) if photo_f else None,
            "status": status,
            "step": steps.index(status) if status in steps else -1,
            "created": str(r.creation),
            "updated": str(r.modified),
            "history": history,
            "details": details,
        })
    return {"doctype": doctype, "steps": steps, "negative": negative, "items": items,
            "labels": {"title": _(title_f.label) if title_f else _("Request"),
                       "area": _(area_f.label) if area_f else _("Area")}}
