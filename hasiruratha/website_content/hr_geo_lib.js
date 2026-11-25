/* Hasiru Ratha geolocation helpers (shared by the HR Site and HR Visit form scripts) */
window.hr_geo = window.hr_geo || (function () {
	var LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js";
	var LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css";

	function load_leaflet(cb) {
		if (window.L && window.L.map) return cb();
		if (!document.getElementById("hr-leaflet-css")) {
			var l = document.createElement("link");
			l.id = "hr-leaflet-css"; l.rel = "stylesheet"; l.href = LEAFLET_CSS;
			document.head.appendChild(l);
		}
		var s = document.createElement("script");
		s.src = LEAFLET_JS; s.onload = cb;
		document.head.appendChild(s);
	}

	// Find the latitude / longitude fields of a doctype meta, in form order: [start_lat, start_lng, end_lat, end_lng]
	function geo_fields(meta) {
		var lat = [], lng = [];
		(meta.fields || []).forEach(function (df) {
			if (["Float", "Data", "Currency", "Small Text"].indexOf(df.fieldtype) < 0) return;
			var n = df.fieldname || "";
			if (/(^|_)lat(itude)?\d*$/i.test(n)) lat.push(n);
			else if (/(^|_)(lng|lon|long|longitude)\d*$/i.test(n)) lng.push(n);
		});
		return { start: [lat[0], lng[0]], end: [lat[1], lng[1]] };
	}

	function num(v) { var x = parseFloat(v); return isNaN(x) ? null : x; }

	function box(id, title) {
		return '<div class="form-section hr-geo-section" id="' + id + '"><div class="section-body">' +
			'<div style="margin:6px 0 8px;display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">' +
			'<b>' + title + '</b><span class="hr-geo-actions"></span></div>' +
			'<div class="hr-geo-map" style="height:340px;border-radius:8px;border:1px solid var(--border-color,#ddd)"></div>' +
			'<div class="hr-geo-note text-muted small" style="margin-top:6px"></div></div></div>';
	}

	function mount(frm, id, title, anchor_field) {
		var $old = frm.$wrapper.find("#" + id);
		if ($old.length) { return $old; }
		var $box = $(box(id, title));
		var anchor = anchor_field && frm.fields_dict[anchor_field] && frm.fields_dict[anchor_field].$wrapper
			? frm.fields_dict[anchor_field].$wrapper.closest(".form-section") : null;
		if (anchor && anchor.length) anchor.after($box); else frm.$wrapper.find(".form-page").first().prepend($box);
		return $box;
	}

	function draw($box, points, opts) {
		opts = opts || {};
		load_leaflet(function () {
			var el = $box.find(".hr-geo-map")[0];
			if (el._hr_map) { el._hr_map.remove(); el._hr_map = null; }
			var valid = points.filter(function (p) { return p.lat !== null && p.lng !== null; });
			var note = $box.find(".hr-geo-note");
			if (!valid.length) {
				el.innerHTML = '<div style="padding:40px;text-align:center;color:#888">No location saved yet.</div>';
				note.text(""); return;
			}
			el.innerHTML = "";
			var map = L.map(el, { scrollWheelZoom: false });
			el._hr_map = map;
			L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
				maxZoom: 19, attribution: "&copy; OpenStreetMap contributors"
			}).addTo(map);
			var latlngs = [];
			valid.forEach(function (p, i) {
				var m = L.marker([p.lat, p.lng], { draggable: !!(opts.draggable && i === 0) }).addTo(map);
				m.bindPopup(frappe.utils.escape_html(p.label || "") + "<br>" + p.lat.toFixed(6) + ", " + p.lng.toFixed(6));
				if (opts.draggable && i === 0 && opts.on_drag) {
					m.on("dragend", function () { var c = m.getLatLng(); opts.on_drag(c.lat, c.lng); });
				}
				latlngs.push([p.lat, p.lng]);
			});
			if (latlngs.length > 1) {
				L.polyline(latlngs, { color: "#304745", weight: 4 }).addTo(map);
				map.fitBounds(latlngs, { padding: [30, 30], maxZoom: 19 });
			} else {
				map.setView(latlngs[0], 18);
			}
			setTimeout(function () { map.invalidateSize(); }, 250);
			note.text(opts.note || "");
		});
	}

	function capture(cb, silent) {
		if (!navigator.geolocation) { if (!silent) frappe.msgprint(__("This browser cannot give its location.")); return; }
		navigator.geolocation.getCurrentPosition(function (pos) {
			cb(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
		}, function (err) {
			frappe.show_alert({ message: __("Could not get your location: ") + err.message + __(" (allow location access for this site)"), indicator: "orange" }, 8);
		}, { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
	}

	return { geo_fields: geo_fields, num: num, mount: mount, draw: draw, capture: capture };
})();
