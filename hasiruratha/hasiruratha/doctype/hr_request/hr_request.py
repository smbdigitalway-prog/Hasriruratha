# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
HR Request - a citizen asks the team to plant at a NEW location, or to look after an existing tree
(MAINTENANCE). Created from /request (see hasiruratha.request_api). The admin works it from the Desk:
change the status, assign a volunteer, link the spot. The citizen sees the status on /my-requests.

GPS is captured once by the phone (or the citizen's pin) and cannot be edited afterwards.
"""
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

GPS_FIELDS = ("gps_lat", "gps_lng", "gps_accuracy_m", "location_source")


def make_title(d):
	what = "New sapling" if d.request_type == "New location" else "Care: %s" % (d.issue_type or "tree")
	where = ", ".join(x for x in (d.road, d.area) if x)
	return ("%s · %s" % (what, where) if where else what)[:140]


class HRRequest(Document):
	def validate(self):
		self.pincode = re.sub(r"\D", "", self.pincode or "")
		if self.pincode and len(self.pincode) != 6:
			frappe.throw(_("Pin code must have 6 digits"))
		if not self.is_new():
			before = self.get_doc_before_save()
			if before and any(str(before.get(f) or "") != str(self.get(f) or "") for f in GPS_FIELDS):
				frappe.throw(_("The GPS location of a request cannot be changed"))
		self.latitude, self.longitude = self.gps_lat, self.gps_lng
		self.title = make_title(self)
		if self.status == "Completed" and not self.completed_on:
			self.completed_on = today()

	def on_update(self):
		if self.flags.in_insert or not self.has_value_changed("status") or not self.email:
			return
		frappe.sendmail(
			recipients=[self.email],
			subject=_("Your Hasiru Ratha request {0}: {1}").format(self.name, self.status),
			message=_("<p>Hello {0},</p><p>Your request <b>{1}</b> ({2}, {3}) is now <b>{4}</b>.</p>{5}"
			          "<p>See all your requests at <a href='{6}'>{6}</a>.</p><p>Thank you for caring for our trees.</p>").format(
				frappe.utils.escape_html(self.citizen_name or ""), self.name, self.request_type,
				frappe.utils.escape_html(self.area or self.road or ""), self.status,
				("<p>%s</p>" % frappe.utils.escape_html(self.admin_notes)) if self.admin_notes else "",
				frappe.utils.get_url("/my-requests")),
			reference_doctype=self.doctype, reference_name=self.name,
		)
