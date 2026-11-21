from urllib.parse import quote

import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		qs = frappe.local.request.query_string.decode() if frappe.local.request else ""
		frappe.local.flags.redirect_location = "/citizen-login?redirect-to=" + quote("/request" + ("?" + qs if qs else ""))
		raise frappe.Redirect
	web_context.base(context, "request", "Raise a request")
	context.user_name = frappe.utils.get_fullname(frappe.session.user)
