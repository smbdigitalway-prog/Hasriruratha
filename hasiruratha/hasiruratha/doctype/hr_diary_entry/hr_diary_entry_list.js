frappe.listview_settings["HR Diary Entry"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const c = { "Pending approval": "orange", Approved: "green", Rejected: "red" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
};
