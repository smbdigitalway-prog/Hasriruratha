// HR Request in the Desk: the admin works a citizen request with Frappe's own form UI.
const HR_RQ = "hasiruratha.request_api";
const HR_LF = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/";

function hr_rq_set_status(frm, status, extra) {
	frm.set_value("status", status);
	if (extra) Object.entries(extra).forEach(([k, v]) => frm.set_value(k, v));
	return frm.save();
}

function hr_rq_map(frm) {
	const f = frm.fields_dict.location_map;
	if (!f || !frm.doc.gps_lat) return;
	f.$wrapper.html(`<div class="hr-rq-map" style="height:260px;border-radius:var(--border-radius-md);margin-bottom:8px"></div>
		<div class="text-muted small">${__("Red: requested spot. Green: registered spots nearby (click to open).")}</div>`);
	const box = f.$wrapper.find(".hr-rq-map");
	frappe.require([HR_LF + "leaflet.css", HR_LF + "leaflet.js"], () => {
		const here = [frm.doc.gps_lat, frm.doc.gps_lng];
		const map = L.map(box[0]).setView(here, 18);
		L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(map);
		L.circleMarker(here, { radius: 10, color: "#fff", weight: 2, fillColor: "#dc2626", fillOpacity: 0.95 }).addTo(map).bindTooltip(__("Requested spot"), { permanent: true, direction: "top" });
		if (frm.doc.gps_accuracy_m) L.circle(here, { radius: frm.doc.gps_accuracy_m, weight: 1, fillOpacity: 0.08 }).addTo(map);
		frappe.xcall("hasiruratha.public_api.spots", {
			south: here[0] - 0.002, north: here[0] + 0.002, west: here[1] - 0.002, east: here[1] + 0.002,
		}).then((r) => (r.spots || []).forEach((s) =>
			L.circleMarker([s.lat, s.lng], { radius: 8, color: "#fff", weight: 2, fillColor: "#16a34a", fillOpacity: 0.95 })
				.addTo(map).bindTooltip(frappe.utils.escape_html(s.name)).on("click", () => frappe.set_route("Form", "HR Site", s.id))));
		setTimeout(() => map.invalidateSize(), 200);
	});
}

frappe.ui.form.on("HR Request", {
	refresh(frm) {
		if (frm.is_new()) return;
		const d = frm.doc, open = ["Received", "Under review", "Accepted", "Scheduled"].includes(d.status);

		if (d.possible_duplicate && open) {
			frm.dashboard.set_headline_alert(
				__("Possible duplicate: a registered spot or another open request is very close ({0} m to {1}). Check before accepting.",
					[d.nearest_distance_m ?? "?", d.nearest_site || __("another request")]), "orange");
		}

		if (open) {
			if (d.request_type === "New location" && !d.site) {
				frm.add_custom_button(__("Register as new spot"), () =>
					frappe.confirm(__("Create a new spot (HR Site) at this request's location?"), () =>
						frappe.xcall(`${HR_RQ}.register_spot`, { name: d.name }).then((r) => {
							frappe.show_alert({ message: __("Spot {0} created", [r.site]), indicator: r.needs_review ? "orange" : "green" });
							frm.reload_doc();
						})), __("Actions"));
			}
			frm.add_custom_button(__("Plan a visit"), () => {
				const dlg = new frappe.ui.Dialog({
					title: __("Plan a visit"),
					fields: [
						{ fieldname: "planned_date", fieldtype: "Date", label: __("Date"), reqd: 1, default: frappe.datetime.add_days(frappe.datetime.get_today(), 2) },
						{ fieldname: "service_type", fieldtype: "Select", label: __("Work"),
							options: ["", "New plantation", "Watering / follow-up", "Maintenance visit", "Tree Guard Needed", "Tree Guard Removal",
								"Support pole needed", "Pesticide needed", "Debris cleanup"].join("\n") },
						{ fieldname: "volunteers_needed", fieldtype: "Int", label: __("Volunteers needed"), default: 2 },
						{ fieldname: "notes", fieldtype: "Small Text", label: __("Notes") },
					],
					primary_action_label: __("Plan visit"),
					primary_action(v) {
						frappe.xcall(`${HR_RQ}.plan_visit`, { name: d.name, ...v }).then((r) => {
							dlg.hide();
							frappe.show_alert({ message: __("Visit {0} planned", [r.visit]), indicator: "green" });
							frm.reload_doc();
						});
					},
				});
				dlg.show();
			}, __("Actions"));
			frm.add_custom_button(__("Assign volunteer"), () =>
				frappe.prompt({ fieldname: "v", fieldtype: "Link", options: "HR Volunteer", label: __("Volunteer"), reqd: 1,
					get_query: () => ({ filters: { active: 1 } }) },
				(v) => hr_rq_set_status(frm, d.status === "Received" || d.status === "Under review" ? "Accepted" : d.status, { assigned_volunteer: v.v }),
				__("Assign volunteer")), __("Actions"));
			if (d.status !== "Accepted" && d.status !== "Scheduled") frm.add_custom_button(__("Accept"), () => hr_rq_set_status(frm, "Accepted"), __("Status"));
			frm.add_custom_button(__("Completed"), () => hr_rq_set_status(frm, "Completed"), __("Status"));
			frm.add_custom_button(__("Duplicate"), () =>
				frappe.prompt({ fieldname: "n", fieldtype: "Small Text", label: __("Note for the citizen"),
					default: __("This spot is already registered with Hasiru Ratha. Thank you for letting us know!") },
				(v) => hr_rq_set_status(frm, "Duplicate", { admin_notes: v.n }), __("Mark as duplicate")), __("Status"));
			frm.add_custom_button(__("Reject"), () =>
				frappe.prompt({ fieldname: "n", fieldtype: "Small Text", label: __("Reason (shown to the citizen)"), reqd: 1 },
				(v) => hr_rq_set_status(frm, "Rejected", { admin_notes: v.n }), __("Reject request")), __("Status"));
		}
		if (d.site) frm.add_custom_button(__("Spot on public map"), () => window.open(`/trees?spot=${encodeURIComponent(d.site)}`), __("View"));
		if (d.gps_lat) frm.add_custom_button(__("Google Maps"), () => window.open(`https://www.google.com/maps?q=${d.gps_lat},${d.gps_lng}`), __("View"));
		hr_rq_map(frm);
	},
});
