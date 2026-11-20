frappe.ui.form.on("HR Deleted Site", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.restored_site) {
			frm.dashboard.set_headline_alert(__("Re-planted as {0}", [frm.doc.restored_site]), "green");
			return;
		}
		frm.add_custom_button(__("Re-plant this site"), () => {
			frappe.prompt({ fieldname: "back", fieldtype: "Check", default: frm.doc.moved_to ? 1 : 0, hidden: frm.doc.moved_to ? 0 : 1,
				label: __("Also move back the trees that were moved to {0}", [frm.doc.moved_to || ""]) },
			(v) => frappe.xcall("hasiruratha.hasiruratha.doctype.hr_deleted_site.hr_deleted_site.restore_site",
				{ name: frm.name, move_trees_back: v.back ? 1 : 0 }).then((r) => {
				frappe.show_alert({ message: __("Re-planted as {0}", [r.site]), indicator: "green" });
				frm.reload_doc();
			}), __("Re-plant this site"), __("Re-plant"));
		});
	},
});
