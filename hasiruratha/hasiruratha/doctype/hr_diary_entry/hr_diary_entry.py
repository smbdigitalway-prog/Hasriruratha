# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

from hasiruratha import masters


class HRDiaryEntry(masters.AutoLinks, Document):
	def validate(self):
		if self.area and not self.zone:
			self.zone = frappe.db.get_value("HR Area", self.area, "zone")

	def on_update(self):
		# the home page's Green Diary block shows approved entries
		from frappe.website.utils import clear_website_cache

		clear_website_cache()
