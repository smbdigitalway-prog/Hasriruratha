# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""Common page context for the citizen / volunteer web pages (Frappe website pages)."""
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
