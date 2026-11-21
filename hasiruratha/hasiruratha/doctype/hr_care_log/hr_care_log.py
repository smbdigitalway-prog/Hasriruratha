# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""HR Care Log - one row per tree per activity. Keeps the tree's "last watered", "last maintenance"
and tree-guard state up to date."""
import frappe
from frappe.model.document import Document

GUARD = {"Guard installed": "Yes", "Guard removed": "No"}


class HRCareLog(Document):
	def validate(self):
		t = frappe.db.get_value("HR Tree", self.tree, ["site_id", "species"], as_dict=True) or {}
		self.site = t.get("site_id")
		self.species = t.get("species")
		self.route = frappe.db.get_value("HR Site", self.site, "route") if self.site else None

	def on_update(self):
		refresh_tree(self.tree)
		if self.activity in GUARD and frappe.db.get_value("HR Care Log", {"tree": self.tree,
		        "activity": ["in", list(GUARD)]}, "name", order_by="log_date desc, creation desc") == self.name:
			frappe.db.set_value("HR Tree", self.tree, "tree_guard", GUARD[self.activity])

	def after_delete(self):
		refresh_tree(self.tree)


def refresh_tree(tree):
	"""Recompute the tree's last watered / last maintenance dates from its care log."""
	(watered, any_care), = frappe.db.sql(
		"""select max(case when activity='Watering' then log_date end), max(log_date)
		   from `tabHR Care Log` where tree=%s""", tree)
	frappe.db.set_value("HR Tree", tree, {"last_watered": watered, "last_maintenance": any_care}, update_modified=False)
