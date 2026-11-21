# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: HR Visit got Area and Zone (copied from its site) so the list can be filtered by them. Fill the old visits."""
import frappe


def execute():
	if not frappe.db.has_column("HR Visit", "area"):
		return
	frappe.db.sql(
		"""update `tabHR Visit` v join `tabHR Site` s on s.name = v.site_id
		   set v.area = s.area, v.zone = s.zone_id
		   where (v.area is null or v.area = '' or v.zone is null or v.zone = '')"""
	)
