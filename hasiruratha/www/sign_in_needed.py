"""/sign-in-needed?for=/my-trees  -  why this person cannot open a page, and what they can do instead.

Visitors are asked to sign in or register; signed-in citizens are told the page is for volunteers (or for
the admin team) and offered volunteer registration; volunteers waiting for approval are told so."""
from urllib.parse import urlencode

import frappe

from hasiruratha import api, web_context

no_cache = 1


def get_context(context):
	web_context.base(context, "access", "Sign in or register")
	user = frappe.session.user
	target = web_context.safe_next(frappe.form_dict.get("for"))
	admin_area = target.strip("/").split("/")[0] in ("desk", "app")
	if user != "Guest" and (api._is_admin(user) or (api._is_member(user) and not admin_area)):
		frappe.local.flags.redirect_location = target          # they can open it after all
		raise frappe.Redirect
	if user == "Guest":
		who = "guest"
	elif api._is_member(user):
		who = "volunteer"                                       # a volunteer opening the admin area
	elif frappe.db.get_value("HR Volunteer", {"user": user}, "name"):
		who = "pending"
	else:
		who = "citizen"
	context.who = who
	context.admin_area = admin_area
	context.target = target
	context.full_name = frappe.utils.get_fullname(user) if user != "Guest" else ""
	context.login_url = ("/login?" if admin_area else "/volunteer-login?") + urlencode({"redirect-to": target})
	return context
