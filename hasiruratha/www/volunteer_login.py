import frappe

from hasiruratha import api, web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "volunteer", "Volunteer sign-in")
	user = frappe.session.user
	if user != "Guest" and api._is_member(user):
		# already signed in: admins work in the Desk, volunteers in the phone app
		frappe.local.flags.redirect_location = "/desk/hasiruratha/hasiru_ratha_admin" if api._is_admin(user) else "/hasiruratha"
		raise frappe.Redirect
