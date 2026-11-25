"""Add the geolocation map to HR Site (and the site's map to HR Visit) as Client Scripts.

Client Scripts live in the database, so this works on Frappe Cloud without touching the doctype JSON.
Run again any time to refresh:  bench --site <site> execute hasiruratha.patches.v1_0.add_geolocation_map.execute
"""
import frappe

APP = "hasiruratha"


def _read(name):
	with open(frappe.get_app_path(APP, "website_content", name), encoding="utf-8") as fh:
		return fh.read()


def _upsert(name, dt, script):
	if frappe.db.exists("Client Script", name):
		doc = frappe.get_doc("Client Script", name)
	else:
		doc = frappe.new_doc("Client Script")
		doc.name = name
	doc.dt = dt
	doc.view = "Form"
	doc.enabled = 1
	doc.script = script
	doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)
	print(f"[hasiruratha] client script ready: {name}")


def execute():
	lib = _read("hr_geo_lib.js")
	_upsert("HR Site Map", "HR Site", lib + "\n" + _read("hr_site_map.js"))
	_upsert("HR Visit Map", "HR Visit", lib + "\n" + _read("hr_visit_map.js"))
	frappe.clear_cache()
