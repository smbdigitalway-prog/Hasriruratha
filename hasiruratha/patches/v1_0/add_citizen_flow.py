"""Citizen Plant a Tree (/plant) and Report a Tree (/report) pages.

1. makes sure the two citizen doctypes have the fields the pages save into (only adds what is missing)
2. points the Plant a Tree / Report a Tree card buttons on the web page to /plant and /report
3. sends the old /plant-a-tree/new and /report-a-tree/new links to the new pages
Safe to run again:  bench --site <site> execute hasiruratha.patches.v1_0.add_citizen_flow.execute
"""
import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

from hasiruratha.portal.citizen import FORMS, _doctype, _map

LAYOUT = ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Heading", "Fold")


def add_fields():
    for kind in FORMS:
        dt = _doctype(kind)
        if not frappe.db.exists("DocType", dt):
            print(f"[hasiruratha] {dt} not found, skipped")
            continue
        meta, m = frappe.get_meta(dt), _map(dt, kind)
        want = []
        if not m["lat"]:
            want.append(dict(fieldname="gps_lat", label="Latitude", fieldtype="Float", precision="6"))
        if not m["lng"]:
            want.append(dict(fieldname="gps_lng", label="Longitude", fieldtype="Float", precision="6"))
        if not m["acc"]:
            want.append(dict(fieldname="gps_accuracy_m", label="GPS accuracy (m)", fieldtype="Int", read_only=1,
                             description="Empty when the citizen placed the pin by hand"))
        if not m["src"]:
            want.append(dict(fieldname="location_source", label="Location from", fieldtype="Select", options="GPS\nMap pin", read_only=1))
        if not m["photo"]:
            want.append(dict(fieldname="photo", label="Photo", fieldtype="Attach Image"))
        if kind == "report" and not m["tree"]:
            want.append(dict(fieldname="related_tree", label="Tree", fieldtype="Link", options="HR Tree"))
        if not m["dup"]:
            want.append(dict(fieldname="possible_duplicate", label="Possible duplicate", fieldtype="Check", read_only=1))
        if not m["new"]:
            want.append(dict(fieldname="citizen_says_new", label="Citizen says this is a different spot", fieldtype="Check", read_only=1))
        last = [f.fieldname for f in meta.fields if f.fieldtype not in LAYOUT and f.fieldname]
        after = last[-1] if last else None
        for df in want:
            df["insert_after"] = after
            create_custom_field(dt, df)
            after = df["fieldname"]
        if want:
            frappe.clear_cache(doctype=dt)
            print(f"[hasiruratha] {dt}: added {', '.join(d['fieldname'] for d in want)}")


def point_cards():
    targets = {"plant a tree": "/plant", "report a tree": "/report"}
    for page in frappe.get_all("Web Page", pluck="name"):
        doc = frappe.get_doc("Web Page", page)
        changed = False
        for row in doc.get("page_blocks") or []:
            if row.web_template != "HR Block Actions":
                continue
            vals = json.loads(row.web_template_values or "{}")
            for c in vals.get("cards") or []:
                tgt = targets.get((c.get("button_label") or "").strip().lower())
                if tgt and c.get("button_link") != tgt:
                    c["button_link"] = tgt
                    changed = True
            row.web_template_values = json.dumps(vals)
        if changed:
            doc.save(ignore_permissions=True)
            print(f"[hasiruratha] {page}: card buttons now open /plant and /report")


def redirect_old_links():
    try:
        ws = frappe.get_doc("Website Settings")
        have = {r.source for r in ws.get("route_redirects") or []}
        for src, tgt in (("/plant-a-tree/new", "/plant"), ("/report-a-tree/new", "/report")):
            if src not in have:
                ws.append("route_redirects", {"source": src, "target": tgt})
        ws.save(ignore_permissions=True)
    except Exception as e:
        print(f"[hasiruratha] redirects not added ({e}); add them in Website Settings > Route Redirects")


def execute():
    add_fields()
    point_cards()
    redirect_old_links()
    frappe.clear_cache()
