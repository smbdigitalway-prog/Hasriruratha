# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: admin list views show area / road and can be filtered by them (Sites, Trees, Tree Reports, Visits).

Uses Property Setters, so the DocType JSON files stay as they are and an admin can still change it in Customize Form.
"""
import frappe

WANT = {
	"HR Site": {"area": ("in_standard_filter", "in_list_view"), "road": ("in_standard_filter", "in_list_view")},
	"HR Tree Report": {"area": ("in_standard_filter", "in_list_view"), "road": ("in_standard_filter", "in_list_view")},
	"HR Visit": {"area": ("in_standard_filter", "in_list_view")},
	"HR Tree": {"site_id": ("in_standard_filter",)},
}


def execute():
	for dt, fields in WANT.items():
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		for fieldname, props in fields.items():
			if not meta.has_field(fieldname):
				continue
			for prop in props:
				if not meta.get_field(fieldname).get(prop):
					frappe.make_property_setter(
						{"doctype": dt, "doctype_or_field": "DocField", "fieldname": fieldname,
						 "property": prop, "value": 1, "property_type": "Check"}, ignore_validate=True)
	frappe.clear_cache()
