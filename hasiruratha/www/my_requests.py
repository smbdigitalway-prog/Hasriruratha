import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/citizen-login?redirect-to=/my-requests"
		raise frappe.Redirect
	web_context.base(context, "mine", "My requests")
	context.user_name = frappe.utils.get_fullname(frappe.session.user)
