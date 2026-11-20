import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/citizen-login?redirect-to=/my-requests"
		raise frappe.Redirect
	context.no_breadcrumbs = True
	context.hr_page = "mine"
	context.user_name = frappe.utils.get_fullname(frappe.session.user)
