frappe.listview_settings["HR Internship Application"] = {
	add_fields: ["status"],
	get_indicator(doc) {
		const c = { New: "blue", Shortlisted: "orange", Accepted: "green", Rejected: "red", Completed: "gray" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
};
