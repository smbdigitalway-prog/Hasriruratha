# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: the new home page (design handoff v1) as a Web Page built from the "HR …" blocks, at the
preview address /home-new. The current home page and Website Settings are not touched; switching
over is a separate, manual step. Also fills the social links in Hasiruratha Settings when empty."""
import json

import frappe

from hasiruratha.website import DEFAULT_LINKS

ROUTE = "home-new"
BLOCKS = [  # (web template, section id, css class)
	("HR Hero", "home", ""),
	("HR Impact", "impact", ""),
	("HR Work Tiles", "work", "hrw-section"),
	("HR Story", "story", "hrw-section"),
	("HR Green Diary", "diary", "hrw-section"),
	("HR Get Involved", "volunteer", "hrw-section"),
	("HR Learn and Stories", "learn", "hrw-section"),
	("HR Connect", "connect", "hrw-section"),
]


def execute():
	s = frappe.get_doc("Hasiruratha Settings")
	changed = False
	for k, v in DEFAULT_LINKS.items():
		if s.meta.has_field(k) and not s.get(k):
			s.set(k, v)
			changed = True
	if s.meta.has_field("website_since") and not s.get("website_since"):
		s.website_since, changed = 2017, True
	if changed:
		s.flags.ignore_permissions = True
		s.save()

	if frappe.db.exists("Web Page", {"route": ROUTE}):
		return
	if not all(frappe.db.exists("Web Template", t) for t, _i, _c in BLOCKS):
		return
	frappe.get_doc({
		"doctype": "Web Page", "title": "Hasiru Ratha – In Service of Nature", "route": ROUTE, "published": 1,
		"content_type": "Page Builder", "full_width": 1, "show_title": 0,
		"meta_title": "Hasiru Ratha – We don't just plant trees. We help them grow.",
		"meta_description": "Citizen-led tree planting and care in South Bengaluru since 2017. See our trees, "
		                    "report a sapling that needs care, volunteer or intern with us.",
		"meta_image": "/assets/hasiruratha/images/site/photo03.jpg",
		"page_blocks": [{"web_template": t, "web_template_values": json.dumps({}), "section_id": sid, "css_class": css,
		                 "add_container": 0, "add_top_padding": 0, "add_bottom_padding": 0} for t, sid, css in BLOCKS],
	}).insert(ignore_permissions=True)
