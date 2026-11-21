// Copyright (c) 2026, Hasiru Ratha and contributors
// For license information, please see license.txt

// Volunteers see every tree; on the trees assigned to them they can log care, tag GPS (while pending)
// and change the care fields. Everything else stays read-only for them (checked again on the server).
const HR_VOLUNTEER_FIELDS = ["species", "condition", "tree_guard", "support_pole", "notes", "photo_url", "caretaker_name"];
const HR_ACTIVITIES = ["Watering", "Guard installed", "Guard removed", "Support pole", "Pruning", "Weeding",
	"Manure / soil", "Pest treatment", "Replanting", "Other"];

frappe.ui.form.on("HR Tree", {
	refresh(frm) {
		const volunteer = !frappe.boot.hr_is_admin && frappe.boot.hr_volunteer;
		if (!volunteer || frm.is_new()) return;
		const mine = frm.doc.owner_volunteer_id === frappe.boot.hr_volunteer;
		if (mine) {
			const editable = new Set(HR_VOLUNTEER_FIELDS);
			if (frm.doc.gps_status === "Pending") { editable.add("gps_lat"); editable.add("gps_lng"); }
			frm.meta.fields.forEach((df) => {
				if (!editable.has(df.fieldname) && !frappe.model.no_value_type.includes(df.fieldtype)) {
					frm.set_df_property(df.fieldname, "read_only", 1);
				}
			});
			frm.add_custom_button(__("Log care"), () => hr_log_care(frm)).addClass("btn-primary");
			if (frm.doc.gps_status === "Pending") frm.add_custom_button(__("Tag GPS here"), () => hr_tag_gps(frm));
			// the same actions in the banner, so they are visible on a phone too (buttons fold into "⋯" there)
			frm.dashboard.set_headline(`${__("This tree is assigned to you. You can log care and update its condition, guard and notes.")}
				<div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
					<button type="button" class="btn btn-primary btn-sm hr-log-care">${__("Log care")}</button>
					${frm.doc.gps_status === "Pending" ? `<button type="button" class="btn btn-default btn-sm hr-tag-gps">📍 ${__("Tag GPS here")}</button>` : ""}
				</div>`, "green");
			$(document).off("click.hrtree")
				.on("click.hrtree", ".hr-log-care", () => hr_log_care(frm))
				.on("click.hrtree", ".hr-tag-gps", () => hr_tag_gps(frm));
		} else {
			frm.dashboard.set_headline(__("You can view this tree. Only its assigned volunteer or an admin can change it."), "blue");
		}
	},
});

function hr_log_care(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Log care for {0}", [frm.doc.name]),
		fields: [
			{ fieldname: "activity", fieldtype: "Select", label: __("What did you do?"), options: HR_ACTIVITIES.join("\n"), default: "Watering", reqd: 1 },
			{ fieldname: "log_date", fieldtype: "Date", label: __("Date"), default: frappe.datetime.get_today(), reqd: 1 },
			{ fieldname: "hours", fieldtype: "Float", label: __("Hours (optional)") },
			{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes (optional)") },
		],
		primary_action_label: __("Save"),
		primary_action(v) {
			frappe.call({
				method: "hasiruratha.care_api.log",
				args: { trees: JSON.stringify([frm.doc.name]), activity: v.activity, log_date: v.log_date, hours: v.hours, notes: v.notes },
				freeze: true,
			}).then(() => { d.hide(); frappe.show_alert({ message: __("Saved"), indicator: "green" }); frm.reload_doc(); });
		},
	});
	d.show();
}

function hr_tag_gps(frm) {
	if (!navigator.geolocation) return frappe.msgprint(__("This browser cannot share its location."));
	let best = null, done = false, watch = null;
	const finish = () => {
		if (done) return; done = true; navigator.geolocation.clearWatch(watch); frappe.hide_progress();
		if (!best) return frappe.msgprint(__("Could not get your location. Allow location access and try again."));
		if (best.accuracy > 50) return frappe.msgprint(__("Location too rough (±{0} m). Step into the open and try again.", [Math.round(best.accuracy)]));
		frappe.call({
			method: "hasiruratha.care_api.set_gps",
			args: { tree: frm.doc.name, lat: best.latitude, lng: best.longitude, accuracy: Math.round(best.accuracy) },
			freeze: true,
		}).then((r) => {
			const near = (r.message && r.message.near) || [];
			frappe.show_alert({ message: __("GPS saved (±{0} m)", [Math.round(best.accuracy)]), indicator: "green" });
			if (near.length) frappe.msgprint(__("Another registered spot is {0} m away ({1}). If it is the same tree, tell an admin.", [near[0].distance_m, near[0].name]));
			frm.reload_doc();
		});
	};
	frappe.show_progress(__("Finding your location"), 1, 3, __("Keep the phone still for a few seconds"));
	watch = navigator.geolocation.watchPosition((p) => {
		if (!best || p.coords.accuracy < best.accuracy) best = p.coords;
		if (best.accuracy <= 12) finish();
	}, () => finish(), { enableHighAccuracy: true, maximumAge: 0, timeout: 15000 });
	setTimeout(finish, 15000);
}
