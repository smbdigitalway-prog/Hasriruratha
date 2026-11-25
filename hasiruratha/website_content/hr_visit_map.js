/* HR Visit form: show the map of the visit's site */
frappe.ui.form.on("HR Visit", {
	refresh: function (frm) { hr_visit_paint(frm); },
	site: function (frm) { hr_visit_paint(frm); }
});

function hr_visit_paint(frm) {
	var $box = hr_geo.mount(frm, "hr-visit-map", __("Site location"), "site");
	if (!frm.doc.site) { hr_geo.draw($box, [], {}); return; }
	frappe.model.with_doctype("HR Site", function () {
		var g = hr_geo.geo_fields(frappe.get_meta("HR Site"));
		if (!g.start[0] || !g.start[1]) return;
		var cols = [g.start[0], g.start[1], g.end[0], g.end[1]].filter(Boolean);
		frappe.db.get_value("HR Site", frm.doc.site, cols).then(function (r) {
			var v = (r && r.message) || {};
			var pts = [{ lat: hr_geo.num(v[g.start[0]]), lng: hr_geo.num(v[g.start[1]]), label: frm.doc.site }];
			if (g.end[0] && g.end[1]) pts.push({ lat: hr_geo.num(v[g.end[0]]), lng: hr_geo.num(v[g.end[1]]), label: __("End of stretch") });
			hr_geo.draw($box, pts, {});
		});
	});
}
