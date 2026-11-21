# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Website forms from the design handoff.

* internship_apply  public form (/internship). Rate limited, a hidden "website" field catches bots,
                    consent is required. Admins get a to-do; the applicant gets a confirmation email.
* diary_submit      volunteers add a Green Diary entry (/green-diary/new); it waits for admin approval.
* diary_list        approved entries for the public /green-diary page.
"""
import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, escape_html, getdate, today, validate_email_address

from hasiruratha import api, citizen_api

DURATIONS = ("1 month", "2 months", "3 months")
SKILLS = ("Photography", "Video editing", "Writing", "Social media", "Design", "Research / data", "Other")
ACTIVITIES = ("Planting", "Watering", "Tree guards", "Maintenance", "Awareness", "Other")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def internship_apply(full_name=None, email=None, phone=None, area=None, duration=None, skills=None,
                     portfolio_url=None, about=None, consent=0, website=None):
	if website:                                   # hidden field: people never fill it, bots do
		return {"success": True}
	name, email = (full_name or "").strip()[:80], (email or "").strip().lower()
	phone = api._digits(phone)
	if not name:
		frappe.throw(_("Please enter your name"))
	if not validate_email_address(email):
		frappe.throw(_("Please enter a valid email"))
	if len(phone) < 10:
		frappe.throw(_("Please enter a valid 10-digit mobile number"))
	if duration not in DURATIONS:
		frappe.throw(_("Please choose how long you can intern"))
	if not cint(consent):
		frappe.throw(_("Please agree to be contacted about your application"))
	url = (portfolio_url or "").strip()[:300]
	if url and not re.match(r"^https?://", url):
		url = "https://" + url
	picked = [s for s in (skills or "").split(",") if s.strip() in SKILLS]
	if frappe.db.exists("HR Internship Application", {"email": email, "status": ["in", ["New", "Shortlisted"]]}):
		return {"success": True, "already": True}
	doc = frappe.get_doc({
		"doctype": "HR Internship Application", "full_name": name, "email": email, "phone": phone[-10:],
		"area": (area or "").strip()[:140], "duration": duration, "skills": ", ".join(s.strip() for s in picked),
		"portfolio_url": url, "about": (about or "").strip()[:1500], "consent": 1, "status": "New",
	}).insert(ignore_permissions=True)
	citizen_api._todo_admins("HR Internship Application", doc.name,
	                         _("Internship application from {0} ({1})").format(name, duration))
	frappe.sendmail(recipients=[email], subject=_("We received your internship application"),
	                message=_("<p>Hello {0},</p><p>Thank you for applying to intern with Hasiru Ratha ({1}). "
	                          "Our team will get back to you.</p>").format(escape_html(name), duration),
	                reference_doctype=doc.doctype, reference_name=doc.name)
	return {"success": True}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def diary_submit(entry_date=None, title=None, activity=None, area=None, photo_url=None, photo_2=None, photo_3=None,
                 story=None, volunteers=None, consent=0):
	user = frappe.session.user
	if user == "Guest" or not api._is_member(user):
		frappe.throw(_("Please sign in as a volunteer"), frappe.PermissionError)
	if not (title or "").strip():
		frappe.throw(_("Please add a short caption"))
	day = getdate(entry_date or today())
	if day > getdate(today()):
		frappe.throw(_("The date cannot be in the future"))
	photos = [citizen_api._check_photo(p) for p in (photo_url, photo_2, photo_3) if p]
	if not photos:
		frappe.throw(_("Please add at least one photo"))
	doc = frappe.get_doc({
		"doctype": "HR Diary Entry", "entry_date": day, "title": title.strip()[:140],
		"activity": activity if activity in ACTIVITIES else "Other", "area": (area or "").strip()[:140] or None,
		"photo": photos[0], "photo_2": photos[1] if len(photos) > 1 else None, "photo_3": photos[2] if len(photos) > 2 else None,
		"story": (story or "").strip()[:1500], "volunteers": (volunteers or "").strip()[:140],
		"consent": cint(consent), "submitted_by": user, "status": "Pending approval",
	}).insert(ignore_permissions=True)
	citizen_api._todo_admins("HR Diary Entry", doc.name, _("Green Diary entry to approve: {0}").format(doc.title))
	return {"success": True, "name": doc.name}


@frappe.whitelist(allow_guest=True)
def diary_list(start=0, page_length=24):
	rows = frappe.get_all("HR Diary Entry", {"status": "Approved"},
	                      ["name", "entry_date", "title", "activity", "area", "photo", "photo_2", "photo_3", "story", "volunteers"],
	                      order_by="entry_date desc, creation desc", start=cint(start), page_length=min(cint(page_length) or 24, 60))
	for r in rows:
		r.entry_date = str(r.entry_date or "")
	return rows
