import frappe

from hasiruratha import api, web_context

no_cache = 1


def get_context(context):
	user = frappe.session.user
	if user == "Guest" or not api._is_admin(user):
		frappe.local.flags.redirect_location = "/login?redirect-to=/spot-qr"
		raise frappe.Redirect
	web_context.base(context, "spot-qr", "QR labels")
	ids = [x for x in (frappe.form_dict.get("sites") or "").split(",") if x][:60]
	context.labels = frappe.get_all("HR Site", {"name": ["in", ids or [""]]}, ["name", "site_name", "road", "area"])
	context.base_url = frappe.utils.get_url()
