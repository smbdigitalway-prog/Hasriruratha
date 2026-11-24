# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""The Web Page "hasiru-ratha" as the one-page site, built only from the "HR ..." Web Templates.

rebuild() throws away every block the page had (Section with Features, Section with CTA, ...) and puts the new blocks in,
each with ALL its fields already filled with the real text and photos, so Website -> Web Page -> Edit Values shows every
field ready to change. It also points Website Settings at the new site: Home Page, Navbar (HR Navbar), Footer (HR Footer).
Safe to run again: it rebuilds the page from the templates each time."""
import json

import frappe

from hasiruratha.website import ONE_PAGE_ROUTE

BLOCKS = [  # (web template, section id, css class)
	("HR Hero", "home", ""),
	("HR About", "about", "hrw-section"),
	("HR Take Action", "get-involved", ""),
	("HR Story", "story", "hrw-section"),
	("HR Work Tiles", "work", "hrw-section"),
	("HR Impact", "impact", "hrw-section"),
	("HR Green Diary", "diary", "hrw-section"),
	("HR Internships", "internships", "hrw-section"),
	("HR Trees Map", "map", "hrw-section"),
	("HR Learn and Stories", "learn", "hrw-section"),
	("HR Connect", "connect", "hrw-section"),
]


def _defaults(template):
	"""{fieldname: default} for every field of a Web Template, so the block opens in Edit Values fully filled."""
	out = {}
	for f in frappe.get_doc("Web Template", template).fields:
		if f.default not in (None, ""):
			out[f.fieldname] = f.default
	return out


def rebuild():
	if not all(frappe.db.exists("Web Template", t) for t, _i, _c in BLOCKS):
		return
	rows = [{"web_template": t, "web_template_values": json.dumps(_defaults(t)), "section_id": sid, "css_class": css,
	         "add_container": 0, "add_top_padding": 0, "add_bottom_padding": 0} for t, sid, css in BLOCKS]
	name = frappe.db.get_value("Web Page", {"route": ONE_PAGE_ROUTE})
	doc = frappe.get_doc("Web Page", name) if name else frappe.new_doc("Web Page")
	doc.title = doc.title or "Hasiru Ratha – Greener Bengaluru"
	doc.route, doc.published, doc.content_type, doc.full_width, doc.show_title = ONE_PAGE_ROUTE, 1, "Page Builder", 1, 0
	doc.set("page_blocks", [])
	for r in rows:
		doc.append("page_blocks", r)
	doc.meta_title = "Hasiru Ratha – We don't just plant trees. We help them grow."
	doc.meta_description = ("Citizen-led tree planting and care in South Bengaluru since 2017. Plant a new tree, volunteer, "
	                        "report a tree, see our trees on the map, or intern with us.")
	doc.meta_image = "/assets/hasiruratha/images/site/photo03.jpg"
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()

	# the earlier preview copy of the same design is not needed any more
	if frappe.db.exists("Web Page", {"route": "home-new"}):
		frappe.db.set_value("Web Page", {"route": "home-new"}, "published", 0)

	ws = frappe.get_doc("Website Settings")
	for field, value in (("home_page", ONE_PAGE_ROUTE), ("navbar_template", "HR Navbar"), ("footer_template", "HR Footer")):
		if ws.meta.has_field(field) and (field == "home_page" or frappe.db.exists("Web Template", value)):
			ws.set(field, value)
	ws.flags.ignore_permissions = True
	ws.save()
	frappe.clear_cache()


def execute():
	rebuild()
