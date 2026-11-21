import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "volunteer", "Become a volunteer")
	user = frappe.session.user
	if user != "Guest":
		context.me_name = frappe.utils.get_fullname(user)
		context.me_email = frappe.db.get_value("User", user, "email") or user
		context.me_mobile = frappe.db.get_value("User", user, "mobile_no") or ""
