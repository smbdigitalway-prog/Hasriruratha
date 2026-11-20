import frappe

no_cache = 1


def get_context(context):
	context.no_breadcrumbs = True
	context.hr_page = "login"
	if frappe.session.user != "Guest":
		to = frappe.form_dict.get("redirect-to") or ""
		frappe.local.flags.redirect_location = to if to.startswith("/") and not to.startswith("//") else "/request"
		raise frappe.Redirect
