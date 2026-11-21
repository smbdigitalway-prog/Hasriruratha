const HR_DR_BULK = "hasiruratha.hasiruratha.doctype.hr_duplicate_report.hr_duplicate_report.bulk_delete_duplicates";

frappe.listview_settings["HR Duplicate Report"] = {
	add_fields: ["status", "distance_between_records"],
	get_indicator(doc) {
		const c = { "Pending Review": "orange", "Kept as New": "green", "Merged": "blue", "Deleted": "red", "Restored": "purple" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
	onload(listview) {
		// Tick one or more rows -> Actions -> Delete duplicate(s). Works from the workspace shortcut, the list and the Kanban.
		listview.page.add_actions_menu_item(__("Delete duplicate site(s)"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) return frappe.msgprint(__("Tick the duplicate reports to delete first."));
			frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", reqd: 1, label: __("Why are these duplicates?"),
				description: __("Trees and records move to the original site of each. A copy of every site is kept in Deleted Sites.") },
			(v) => frappe.xcall(HR_DR_BULK, { names, reason: v.reason }).then((r) => {
				const skipped = r.skipped.map((s) => `${s.report}: ${frappe.utils.escape_html(s.why)}`).join("<br>");
				frappe.show_alert({ message: __("{0} deleted, {1} skipped", [r.deleted.length, r.skipped.length]), indicator: r.skipped.length ? "orange" : "green" });
				if (skipped) frappe.msgprint({ title: __("Skipped"), message: skipped });
				listview.refresh();
			}), __("Delete {0} duplicate(s)", [names.length]), __("Delete"));
		}, true);
	},
};
