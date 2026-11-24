# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Data for the website blocks (Web Templates "HR …"), available in templates through hooks.jinja:

  hr_impact()       live counts for the Impact block (cached for 15 minutes)
  hr_diary(n)       latest approved Green Diary entries
  hr_blog_posts(n)  latest published posts of the Blog app (empty if the app is not installed)
  hr_links()        social links and contact email from Hasiruratha Settings
  hr_account()      who is signed in (for the header menu)
"""
import frappe
from frappe.utils import add_days, cint, getdate, today

ONE_PAGE_ROUTE = "hasiru-ratha"

DEFAULT_LINKS = {
	"instagram_url": "https://www.instagram.com/hasiruratha_blr/",
	"whatsapp_url": "https://chat.whatsapp.com/FivfJpNwrBK0NYr0PuU5ks",
	"facebook_url": "https://www.facebook.com/rathahasiru",
	"x_url": "https://x.com/RathaHasiru",
	"linktree_url": "https://linktr.ee/hasiruratha",
	"contact_email": "rathahasiru@gmail.com",
}


def _cache():
	return frappe.cache() if callable(frappe.cache) else frappe.cache


def hr_links():
	s = frappe.get_cached_doc("Hasiruratha Settings")
	return frappe._dict({k: (s.get(k) or v) for k, v in DEFAULT_LINKS.items()} | {"since": cint(s.get("website_since")) or 2017})


def hr_home_route():
	"""Address of the one-page site that the header links jump into ("/hasiru-ratha"), or "/" if that page is not there."""
	if frappe.db.exists("Web Page", {"route": ONE_PAGE_ROUTE, "published": 1}):
		return "/" + ONE_PAGE_ROUTE
	return "/"


def hr_account():
	"""Who is signed in, for the site header (templates cannot call frappe.get_roles)."""
	user = frappe.session.user
	if user == "Guest":
		return frappe._dict(signed_in=False, is_admin=False, is_volunteer=False)
	roles = set(frappe.get_roles(user))
	admin = bool({"HR Admin", "System Manager"} & roles)
	return frappe._dict(signed_in=True, is_admin=admin, is_volunteer=admin or "HR Volunteer" in roles)


def hr_impact():
	key = "hr_website_impact"
	hit = _cache().get_value(key)
	if hit:
		return frappe._dict(hit)
	year_start = getdate(today()).replace(month=1, day=1)
	(cared,), = frappe.db.sql("select count(distinct tree) from `tabHR Care Log` where log_date >= %s",
	                          add_days(today(), -365))
	out = {
		"trees": frappe.db.count("HR Tree", {"status": ["!=", "Merged"]}),
		"cared": cared or frappe.db.count("HR Tree", {"owner_volunteer_id": ["is", "set"]}),
		"waterings": frappe.db.count("HR Care Log", {"activity": "Watering", "log_date": [">=", year_start]}),
		"volunteers": frappe.db.count("HR Volunteer", {"active": 1}),
		"since": hr_links().since,
	}
	_cache().set_value(key, out, expires_in_sec=900)
	return frappe._dict(out)


def hr_diary(limit=5):
	if not frappe.db.exists("DocType", "HR Diary Entry"):
		return []
	rows = frappe.get_all("HR Diary Entry", {"status": "Approved", "photo": ["is", "set"]},
	                      ["name", "entry_date", "title", "area", "zone", "activity", "photo"],
	                      order_by="entry_date desc, creation desc", limit_page_length=cint(limit) or 5)
	zones = {z.name: z.zone_name for z in frappe.get_all("HR Zone", fields=["name", "zone_name"])}
	for r in rows:
		r.zone_name = zones.get(r.zone, "")
		r.date_label = frappe.utils.formatdate(r.entry_date, "d MMM yyyy") if r.entry_date else ""
	return rows


def hr_blog_posts(limit=3):
	if not frappe.db.exists("DocType", "Blog Post"):
		return []
	try:
		return frappe.get_all("Blog Post", {"published": 1},
		                      ["title", "route", "blog_intro", "published_on"],
		                      order_by="published_on desc", limit_page_length=cint(limit) or 3)
	except Exception:
		return []
