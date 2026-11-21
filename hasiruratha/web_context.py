# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Common page context for the citizen / volunteer web pages (Frappe website pages)."""
from urllib.parse import urlencode

import frappe


def base(context, page, title):
	context.no_breadcrumbs = True
	context.hide_login = 1                 # Frappe navbar: no desk "Login" button for citizens
	context.hr_page = page
	context.title = title
	try:
		from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

		context.logo = get_app_logo()
	except Exception:
		context.logo = "/assets/frappe/images/frappe-framework-logo.svg"
	return context


def safe_next(path, default="/desk/hasiruratha/hasiru_ratha"):
	"""A local path to come back to after signing in (never another site)."""
	path = (path or "").strip()
	return path if path.startswith("/") and not path.startswith("//") and "\\" not in path else default


def need_member_url(path):
	"""Where to send someone who may not open a volunteer page: sign-in for visitors, an explanation for
	signed-in citizens. None when they are a volunteer or admin."""
	from hasiruratha import api

	user = frappe.session.user
	if user == "Guest":
		return "/volunteer-login?" + urlencode({"redirect-to": path})
	if not api._is_member(user):
		return "/sign-in-needed?" + urlencode({"for": path})
	return None


def require_member(path):
	go = need_member_url(path)
	if go:
		frappe.local.flags.redirect_location = go
		raise frappe.Redirect
