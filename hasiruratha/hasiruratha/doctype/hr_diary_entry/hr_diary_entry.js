frappe.ui.form.on("HR Diary Entry", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.status !== "Pending approval") return;
		frm.add_custom_button(__("Approve"), () => { frm.set_value("status", "Approved"); frm.save(); }).addClass("btn-primary");
		frm.add_custom_button(__("Reject"), () => { frm.set_value("status", "Rejected"); frm.save(); });
		if (!frm.doc.consent) frm.dashboard.set_headline_alert(__("The submitter did not confirm that the people in the photos agreed to publication."), "orange");
	},
});
