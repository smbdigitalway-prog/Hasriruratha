# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""HR Deleted Site: the archive of deleted sites. An admin can re-plant (restore) a site from here."""
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

# keys of a saved site that must not be copied onto the re-planted one
_SKIP = {"name", "owner", "creation", "modified", "modified_by", "docstatus", "idx", "doctype", "parent", "parenttype",
         "parentfield", "possible_duplicate_of", "duplicate_map", "tree_count", "status", "notes"}


class HRDeletedSite(Document):
	pass


@frappe.whitelist(methods=["POST"])
def restore_site(name, move_trees_back=0):
	"""Admin: re-plant a deleted site with its original id, place and photo. Optionally move back the trees
	that were moved to the original site when it was deleted."""
	from hasiruratha.hasiruratha.doctype.hr_site.hr_site import _require_admin

	_require_admin()
	arc = frappe.get_doc("HR Deleted Site", name)
	if arc.restored_site:
		frappe.throw(_("This site was already re-planted as {0}").format(arc.restored_site))
	if frappe.db.exists("HR Site", arc.original_site):
		frappe.throw(_("A site with id {0} already exists").format(arc.original_site))

	snap = json.loads(arc.snapshot or "{}")
	data = {k: v for k, v in snap.items() if k not in _SKIP and not isinstance(v, (list, dict))}
	back_to = arc.status_at_delete if arc.status_at_delete not in (None, "", "Needs Review", "Merged") else "Identified"
	data.update({
		"doctype": "HR Site", "site_id": snap.get("site_id") or arc.original_site, "status": back_to, "tree_count": 0,
		"notes": ((snap.get("notes") or "") + "\n" + _("Re-planted from {0} by {1}").format(arc.name, frappe.session.user)).strip(),
	})
	site = frappe.get_doc(data)
	site.flags.ignore_duplicate_check = True       # the admin has decided this is a real place
	site.insert(ignore_permissions=True)

	moved = 0
	if int(move_trees_back or 0) and arc.moved_to and arc.trees_moved:
		for t in [x.strip() for x in arc.trees_moved.split(",") if x.strip()]:
			if frappe.db.get_value("HR Tree", t, "site_id") == arc.moved_to:
				frappe.db.set_value("HR Tree", t, "site_id", site.name, update_modified=False)
				moved += 1
		for s in (site.name, arc.moved_to):
			frappe.db.set_value("HR Site", s, "tree_count", frappe.db.count("HR Tree", {"site_id": s}))

	frappe.db.set_value("HR Deleted Site", name, {"restored_site": site.name, "restored_on": now_datetime(),
	                                               "restored_by": frappe.session.user})
	for r in frappe.get_all("HR Duplicate Report", {"deleted_site": name}, pluck="name"):
		frappe.db.set_value("HR Duplicate Report", r, {"status": "Restored", "restored_site": site.name,
		                                               "resolved_by": frappe.session.user, "resolved_on": now_datetime()})
	return {"success": True, "site": site.name, "trees_moved_back": moved}
