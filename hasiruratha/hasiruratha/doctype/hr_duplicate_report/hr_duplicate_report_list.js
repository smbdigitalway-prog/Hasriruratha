frappe.listview_settings["HR Duplicate Report"] = {
	add_fields: ["status", "distance_between_records"],
	get_indicator(doc) {
		const c = { "Pending Review": "orange", "Kept as New": "green", "Merged": "blue", "Deleted": "red", "Restored": "purple" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
};
