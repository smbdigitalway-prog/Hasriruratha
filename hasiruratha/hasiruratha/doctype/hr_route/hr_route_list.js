// Watering Routes list: import the volunteers' watering spreadsheet (Frappe dialog, preview first).
frappe.listview_settings["HR Route"] = {
	onload(list) {
		list.page.add_inner_button(__("Import watering sheet"), () => hr_import_sheet(list));
	},
};

function hr_import_sheet(list) {
	const M = "hasiruratha.importer.import_sheet";
	const e = frappe.utils.escape_html;
	const summary = (r, done) => `
		<div class="es-alert" data-theme="${done ? "green" : "blue"}" style="margin-bottom:10px"><span class="es-alert__title">
			${done ? __("Imported") : __("Preview: nothing has been changed yet")}</span></div>
		<table class="table table-sm"><tbody>
			<tr><td>${__("Rows read")}</td><td><b>${r.rows}</b></td></tr>
			<tr><td>${__("Spots / stretches")}</td><td><b>${r.sites}</b></td></tr>
			<tr><td>${__("Trees (GPS pending)")}</td><td><b>${r.trees}</b></td></tr>
			<tr><td>${__("Past waterings for the care log")}</td><td><b>${r.waterings}</b></td></tr>
			<tr><td>${__("Trees with a caretaker (adopted)")}</td><td><b>${r.adopted_trees || 0}</b></td></tr>
			<tr><td>${__("Already imported, skipped")}</td><td>${r.skipped}</td></tr>
			${Object.entries(r.sheets || {}).map(([n, x]) => `<tr><td class="text-muted">${__("Sheet")} “${e(n)}”</td><td class="text-muted">${x.rows} ${__("rows")}, ${x.trees} ${__("trees")}</td></tr>`).join("")}
		</tbody></table>
		${Object.keys(r.volunteers || {}).length ? `<p class="small mb-1"><b>${__("Linked to registered volunteers")}:</b> ${Object.entries(r.volunteers).map(([a, b]) => e(a) + " → " + e(b)).join(", ")}</p>` : ""}
		${Object.entries(r.new || {}).map(([dt, names]) => `<p class="text-muted small mb-1"><b>${__("New")} ${e(dt.replace("HR ", ""))}:</b> ${names.map(e).join(", ")}</p>`).join("")}
		${(r.warnings || []).map(w => `<p class="text-danger small mb-1">${e(w)}</p>`).join("")}
		${Object.keys(r.new || {}).length ? `<p class="small text-muted">${__("New names are added as Unverified. Check them in the Areas / Roads / Landmarks / Species lists afterwards.")}</p>` : ""}`;

	const d = new frappe.ui.Dialog({
		title: __("Import watering sheet"),
		fields: [
			{ fieldtype: "HTML", options: `<p class="text-muted small">${__("Excel (.xlsx) or CSV. All sheets are read. Columns: Ownership (optional), # Plants, Area, Watering Route, Location, Plant, and one column per date (a filled cell = watered that day). Trees come in with GPS pending. Rows already imported are skipped.")}</p>` },
			{ fieldname: "file", fieldtype: "Attach", label: __("Spreadsheet"), reqd: 1 },
			{ fieldname: "result", fieldtype: "HTML" },
		],
		primary_action_label: __("Preview"),
		primary_action(v) {
			frappe.xcall(M, { file_url: v.file, preview: 1 }).then((r) => {
				d.fields_dict.result.$wrapper.html(summary(r, false));
				d.set_primary_action(__("Import {0} spots", [r.sites]), () => {
					if (!r.sites) return d.hide();
					frappe.xcall(M, { file_url: v.file, preview: 0 }).then((r2) => {
						d.fields_dict.result.$wrapper.html(summary(r2, true));
						d.set_primary_action(__("Close"), () => { d.hide(); list.refresh(); });
						frappe.show_alert({ message: __("Imported {0} spots and {1} trees", [r2.sites, r2.trees]), indicator: "green" });
					});
				});
			});
		},
	});
	d.show();
}
