# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Once: build the Area / Road / Species lists from the free text already in the database and point
existing records at them. Entries made here are Unverified: an admin checks the spellings and joins
duplicates with Rename -> Merge with existing."""
import frappe

from hasiruratha import masters


def execute():
	for dt, zone_field in (("HR Site", "zone_id"), ("HR Request", "zone"), ("HR Volunteer", "primary_zone_id")):
		for field, master in (("area", "HR Area"), ("road", "HR Road")):
			rows = frappe.db.sql(
				"select distinct `{f}` as v, max(`{z}`) as zone from `tab{dt}` where ifnull(`{f}`, '') != '' group by `{f}`".format(
					f=field, z=zone_field, dt=dt), as_dict=True)
			for r in rows:
				name = masters.ensure(master, r.v, zone=r.zone)
				if name and name != r.v:
					frappe.db.sql("update `tab{dt}` set `{f}`=%s where `{f}`=%s".format(dt=dt, f=field), (name, r.v))
				elif not name:
					frappe.db.sql("update `tab{dt}` set `{f}`=null where `{f}`=%s".format(dt=dt, f=field), (r.v,))

	for (v,) in frappe.db.sql("select distinct species from `tabHR Tree` where ifnull(species, '') != ''"):
		name = masters.ensure("HR Species", v)
		if name != v:
			frappe.db.sql("update `tabHR Tree` set species=%s where species=%s", (name, v))

	for dt in ("HR Site", "HR Tree"):
		frappe.db.sql("""update `tab{0}` set gps_status = if(ifnull(gps_lat, 0) != 0 and ifnull(gps_lng, 0) != 0,
		                 'Captured', 'Pending')""".format(dt))
	frappe.db.sql("update `tabHR Tree` set planting_type='New' where ifnull(planting_type, '')=''")
