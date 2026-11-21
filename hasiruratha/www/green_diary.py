import frappe

from hasiruratha import api, web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "diary", "Green Diary")
	context.full_width = 1
	user = frappe.session.user
	context.is_volunteer = user != "Guest" and api._is_member(user)
