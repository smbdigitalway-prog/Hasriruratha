# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
from frappe.model.document import Document

from hasiruratha import masters


class HRRoad(Document):
	def validate(self):
		masters.tidy(self)
