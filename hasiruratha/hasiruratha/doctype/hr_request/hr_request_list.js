frappe.listview_settings["HR Request"] = {
	add_fields: ["status", "request_type", "possible_duplicate"],
	get_indicator(doc) {
		const c = { Received: "blue", "Under review": "orange", Accepted: "cyan", Scheduled: "purple",
			Completed: "green", Duplicate: "gray", Rejected: "red" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
	formatters: {
		request_type(v) {
			return v === "Maintenance" ? `🛠 ${__("Maintenance")}` : `🌱 ${__("New location")}`;
		},
	},
};
