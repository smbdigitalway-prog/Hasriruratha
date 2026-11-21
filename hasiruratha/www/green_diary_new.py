import frappe

from hasiruratha import api, web_context

no_cache = 1


def get_context(context):
	user = frappe.session.user
	if user == "Guest" or not api._is_member(user):
		frappe.local.flags.redirect_location = "/volunteer-login"
		raise frappe.Redirect
	web_context.base(context, "diary", "Add to the Green Diary")
