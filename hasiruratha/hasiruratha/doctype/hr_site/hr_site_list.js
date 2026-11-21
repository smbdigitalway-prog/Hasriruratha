frappe.listview_settings["HR Site"] = {
	add_fields: ["status"],
	onload(listview) {
		listview.page.add_actions_menu_item(__("Print QR labels"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) return frappe.msgprint(__("Tick the spots first."));
			window.open(`/spot-qr?sites=${names.map(encodeURIComponent).join(",")}`, "_blank");
		}, true);
	},
	get_indicator(doc) {
		const c = { "Needs Review": "orange", Merged: "gray", Urgent: "red", Completed: "green",
			Monitoring: "purple", Planned: "blue", Identified: "yellow", Hold: "gray" };
		return [__(doc.status), c[doc.status] || "gray", "status,=," + doc.status];
	},
};
