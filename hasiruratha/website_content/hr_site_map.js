/* HR Site form: geolocation map, auto-capture on a new site, location required */
frappe.ui.form.on("HR Site", {
	refresh: function (frm) {
		var g = hr_geo.geo_fields(frm.meta);
		if (!g.start[0] || !g.start[1]) return;
		var anchor = g.end[1] || g.end[0] || g.start[1];
		var $box = hr_geo.mount(frm, "hr-site-map", __("Location map"), anchor);

		var paint = function () {
			var pts = [{ lat: hr_geo.num(frm.doc[g.start[0]]), lng: hr_geo.num(frm.doc[g.start[1]]), label: (frm.doc.site_name || frm.doc.name || __("Start")) }];
			if (g.end[0] && g.end[1]) {
				pts.push({ lat: hr_geo.num(frm.doc[g.end[0]]), lng: hr_geo.num(frm.doc[g.end[1]]), label: __("End of stretch") });
			}
			hr_geo.draw($box, pts, {
				draggable: !frm.doc.docstatus,
				note: __("Drag the pin to adjust the start point, then Save."),
				on_drag: function (lat, lng) {
					frm.set_value(g.start[0], +lat.toFixed(7));
					frm.set_value(g.start[1], +lng.toFixed(7));
				}
			});
		};
		paint();
		if (!frm._hr_bound) {
			frm._hr_bound = true;
			g.start.concat(g.end).forEach(function (fn) {
				var fld = fn && frm.fields_dict[fn];
				if (fld && fld.$input) fld.$input.on("change", function () { clearTimeout(frm._hr_t); frm._hr_t = setTimeout(paint, 400); });
			});
		}

		var $actions = $box.find(".hr-geo-actions").empty();
		$('<button class="btn btn-xs btn-default">' + __("Use my current location") + "</button>")
			.appendTo($actions).on("click", function () {
				hr_geo.capture(function (lat, lng, acc) {
					frm.set_value(g.start[0], +lat.toFixed(7));
					frm.set_value(g.start[1], +lng.toFixed(7));
					frappe.show_alert({ message: __("Location captured (accuracy about {0} m)", [Math.round(acc)]), indicator: "green" });
				});
			});

		if (frm.is_new() && !hr_geo.num(frm.doc[g.start[0]]) && !frm._hr_auto) {
			frm._hr_auto = true;
			hr_geo.capture(function (lat, lng, acc) {
				frm.set_value(g.start[0], +lat.toFixed(7));
				frm.set_value(g.start[1], +lng.toFixed(7));
				frappe.show_alert({ message: __("Your current location was captured (about {0} m)", [Math.round(acc)]), indicator: "green" });
			}, true);
		}
	},
	validate: function (frm) {
		var g = hr_geo.geo_fields(frm.meta);
		if (!g.start[0] || !g.start[1]) return;
		if (hr_geo.num(frm.doc[g.start[0]]) === null || hr_geo.num(frm.doc[g.start[1]]) === null) {
			frappe.throw(__("Location is required. Tap 'Use my current location' or drag the pin on the map."));
		}
	}
});
