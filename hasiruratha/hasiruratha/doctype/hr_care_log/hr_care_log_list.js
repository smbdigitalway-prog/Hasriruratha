frappe.listview_settings["HR Care Log"] = {
	add_fields: ["activity"],
	get_indicator(doc) {
		const c = { Watering: "blue", "Guard installed": "green", "Guard removed": "orange", Replanting: "purple" };
		return [__(doc.activity), c[doc.activity] || "gray", "activity,=," + doc.activity];
	},
};
