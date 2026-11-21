# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document


class HREventSubscription(Document):
	def validate(self):
		if self.is_new() and frappe.db.exists("HR Event Subscription", {"event": self.event, "user": self.user, "status": ["!=", "Cancelled"]}) and self.user:
			frappe.throw(_("Already subscribed to this event"))

	def on_update(self):
		_recount(self.event)

	def on_trash(self):
		frappe.db.after_commit.add(lambda: _recount(self.event))


def _recount(event):
	n = frappe.db.count("HR Event Subscription", {"event": event, "status": ["!=", "Cancelled"]})
	frappe.db.set_value("HR Event", event, "subscribers", n, update_modified=False)
