# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Upcoming events (/events): anyone can look, a signed-in citizen or volunteer can subscribe (requirement 16)."""
import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate, today

from hasiruratha import api

LIVE = ("Planned", "Open")


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=300, seconds=300)
def events():
	rows = frappe.get_all(
		"HR Event", {"status": ["in", LIVE], "event_date": [">=", today()]},
		["name", "title", "event_type", "status", "event_date", "start_time", "end_time", "area", "zone", "location",
		 "description", "photo", "volunteers_needed", "subscribers", "gps_lat", "gps_lng"],
		order_by="event_date asc, start_time asc", limit_page_length=50)
	mine = set()
	if frappe.session.user != "Guest":
		mine = set(frappe.get_all("HR Event Subscription", {"user": frappe.session.user, "status": ["!=", "Cancelled"]}, pluck="event"))
	zones = {z.name: z.zone_name for z in frappe.get_all("HR Zone", fields=["name", "zone_name"])}
	for r in rows:
		r.update(event_date=str(r.event_date), start_time=str(r.start_time or "")[:5], end_time=str(r.end_time or "")[:5],
		         zone=zones.get(r.zone, r.zone or ""), subscribed=r.name in mine)
	return {"events": rows, "signed_in": frappe.session.user != "Guest"}


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=40, seconds=3600)
def subscribe(event=None):
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in first"), frappe.AuthenticationError)
	ev = frappe.db.get_value("HR Event", event, ["title", "status", "event_date", "start_time", "location", "area"], as_dict=True)
	if not ev or ev.status not in LIVE or getdate(ev.event_date) < getdate(today()):
		frappe.throw(_("This event is not open for subscription"))
	row = frappe.db.get_value("HR Event Subscription", {"event": event, "user": user}, ["name", "status"], as_dict=True)
	if row and row.status != "Cancelled":
		return {"success": True, "already": True}
	u = frappe.db.get_value("User", user, ["full_name", "mobile_no", "email"], as_dict=True)
	if row:
		frappe.db.set_value("HR Event Subscription", row.name, "status", "Subscribed")
		doc = frappe.get_doc("HR Event Subscription", row.name)
		doc.save(ignore_permissions=True)
	else:
		frappe.get_doc({"doctype": "HR Event Subscription", "event": event, "user": user, "full_name": u.full_name,
		                "mobile": u.mobile_no, "email": u.email or user, "status": "Subscribed",
		                "is_volunteer": 1 if api._is_member(user) else 0}).insert(ignore_permissions=True)
	try:
		frappe.sendmail(recipients=[u.email or user], subject=_("You are in: {0}").format(ev.title),
		                message=_("Thank you for subscribing to {0} on {1}{2}. Meeting point: {3}. See you there! - Hasiru Ratha").format(
			                ev.title, ev.event_date, (" at " + str(ev.start_time)[:5]) if ev.start_time else "", ev.location or ev.area or _("to be shared")))
	except Exception:
		frappe.log_error(title="HR event subscription email")
	return {"success": True}


@frappe.whitelist(methods=["POST"])
def unsubscribe(event=None):
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in first"), frappe.AuthenticationError)
	name = frappe.db.get_value("HR Event Subscription", {"event": event, "user": user, "status": "Subscribed"}, "name")
	if name:
		doc = frappe.get_doc("HR Event Subscription", name)
		doc.status = "Cancelled"
		doc.save(ignore_permissions=True)
	return {"success": True}
