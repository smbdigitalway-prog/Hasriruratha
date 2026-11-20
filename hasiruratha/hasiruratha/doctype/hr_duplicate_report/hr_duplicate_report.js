// Admin review of one duplicate report, in Frappe's own form UI.
const HR_SITE = "hasiruratha.hasiruratha.doctype.hr_site.hr_site";
const HR_DS = "hasiruratha.hasiruratha.doctype.hr_deleted_site.hr_deleted_site";
const HR_DR = "hasiruratha.hasiruratha.doctype.hr_duplicate_report.hr_duplicate_report";

function hr_dr_card(title, s, color) {
	const e = frappe.utils.escape_html;
	if (!s || !s.name) return `<div class="col-sm-6"><div class="text-muted">${title}: ${__("not found")}</div></div>`;
	const img = s.photo
		? `<a href="${e(s.photo)}" target="_blank"><img src="${e(s.photo)}" style="width:100%;height:220px;object-fit:cover"></a>`
		: `<div style="height:220px;display:flex;align-items:center;justify-content:center;background:#f3f4f6;color:#9ca3af">${__("No photo")}</div>`;
	const link = s.status === __("deleted") ? e(s.name) : `<a href="/app/hr-site/${e(s.name)}">${e(s.site_name || s.name)}</a>`;
	return `<div class="col-sm-6" style="margin-bottom:10px"><div style="border:2px solid ${color};border-radius:10px;overflow:hidden">${img}
		<div style="padding:8px 10px"><b>${title}</b>: ${link}<br><span class="text-muted small">${e([s.road, s.area].filter(Boolean).join(", "))}
		· ${s.tree_count || 0} ${__("trees")} · ${e(s.status || "")}</span></div></div></div>`;
}

function hr_dr_reload(frm) {
	frappe.xcall(`${HR_DR}.comparison`, { name: frm.doc.name }).then((r) => {
		const d = r.distance_m != null ? `<div class="text-muted" style="margin:4px 0 10px">${__("Distance between the two: {0} m", [r.distance_m])}</div>` : "";
		frm.fields_dict.comparison_html.$wrapper.html(
			`<div class="row">${hr_dr_card(__("New site"), r.this, "#f97316")}${hr_dr_card(__("Existing site"), r.other, "#2563eb")}</div>${d}`);
	});
}

frappe.ui.form.on("HR Duplicate Report", {
	refresh(frm) {
		if (frm.is_new()) return;
		hr_dr_reload(frm);
		const st = frm.doc.status, site = frm.doc.site;
		const done = () => frm.reload_doc();
		if (st === "Pending Review") {
			frm.dashboard.set_headline_alert(
				__("{0} looks like a duplicate of {1}. Compare the photos below, then decide.", [site, frm.doc.possible_duplicate_of_site]), "orange");
			frm.add_custom_button(__("Different site - keep it"), () =>
				frappe.xcall(`${HR_SITE}.approve_site`, { name: site }).then(done), __("Decide"));
			frm.add_custom_button(__("Same place - merge"), () =>
				frappe.confirm(__("Move all trees, visits and reports to {0} and mark {1} Merged?", [frm.doc.possible_duplicate_of_site, site]), () =>
					frappe.xcall(`${HR_SITE}.merge_site`, { name: site }).then(done)), __("Decide"));
			frm.add_custom_button(__("Delete duplicate"), () =>
				frappe.prompt({ fieldname: "reason", fieldtype: "Small Text", reqd: 1, label: __("Why is this a duplicate?"),
					description: __("Trees and records move to {0}. A full copy is kept in Deleted Sites and can be re-planted.", [frm.doc.possible_duplicate_of_site]) },
				(v) => frappe.xcall(`${HR_SITE}.delete_duplicate`, { name: site, reason: v.reason }).then(() => {
					frappe.show_alert({ message: __("Deleted. A copy is in Deleted Sites."), indicator: "green" }); done();
				}), __("Delete duplicate site {0}", [site]), __("Delete")), __("Decide"));
			frm.page.set_inner_btn_group_as_primary(__("Decide"));
		}
		if (st === "Deleted" && frm.doc.deleted_site) {
			frm.add_custom_button(__("Re-plant this site"), () => hr_replant_dialog(frm.doc.deleted_site, done));
			frm.add_custom_button(__("Open Deleted Site copy"), () => frappe.set_route("Form", "HR Deleted Site", frm.doc.deleted_site));
		}
		if (st === "Restored" && frm.doc.restored_site) {
			frm.add_custom_button(__("Open re-planted site"), () => frappe.set_route("Form", "HR Site", frm.doc.restored_site));
		}
		if (frm.doc.possible_duplicate_of_site) {
			frm.add_custom_button(__("Open existing site"), () => frappe.set_route("Form", "HR Site", frm.doc.possible_duplicate_of_site), __("Open"));
		}
	},
});

function hr_replant_dialog(archive, done) {
	frappe.prompt({ fieldname: "back", fieldtype: "Check", label: __("Also move back the trees that were moved to the other site"), default: 1 },
		(v) => frappe.xcall(`${HR_DS}.restore_site`, { name: archive, move_trees_back: v.back ? 1 : 0 }).then((r) => {
			frappe.show_alert({ message: __("Re-planted as {0}", [r.site]), indicator: "green" });
			done && done();
		}), __("Re-plant this site"), __("Re-plant"));
}
window.hr_replant_dialog = hr_replant_dialog;
