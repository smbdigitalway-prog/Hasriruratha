import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "login", "Sign in")
	if frappe.session.user != "Guest":
		to = frappe.form_dict.get("redirect-to") or ""
		frappe.local.flags.redirect_location = to if to.startswith("/") and not to.startswith("//") else "/request"
		raise frappe.Redirect
