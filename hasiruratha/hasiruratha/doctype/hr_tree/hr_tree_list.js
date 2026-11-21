// HR Tree list: a "My trees" filter for volunteers, and a link to the phone GPS tagging page.
frappe.listview_settings["HR Tree"] = {
	onload(list) {
		if (frappe.boot.hr_volunteer && !frappe.boot.hr_is_admin) {
			list.page.add_inner_button(__("My trees"), () => {
				list.filter_area.clear(false).then(() => list.filter_area.add([["HR Tree", "owner_volunteer_id", "=", frappe.boot.hr_volunteer]]));
			});
		}
		list.page.add_inner_button(__("GPS tagging (phone)"), () => { window.location.href = "/gps-tagging"; });
	},
};
