# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
from frappe.model.document import Document
from frappe.utils import flt

from hasiruratha import masters, permissions


class HRTree(masters.AutoLinks, Document):
	def validate(self):
		permissions.check_tree_changes(self)
		has_gps = bool(flt(self.gps_lat) and flt(self.gps_lng))
		self.gps_status = "Captured" if has_gps else "Pending"
		if has_gps:
			self.latitude, self.longitude = flt(self.gps_lat), flt(self.gps_lng)
		if self.planting_type != "Replacement":
			self.replaces_tree = None
		if self.owner_volunteer_id and not self.caretaker_type:
			self.caretaker_type = "Volunteer"
