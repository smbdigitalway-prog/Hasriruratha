# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Redirects for the retired single-page apps (/hasiruratha, /citizen), and the Desk guard that shows
signed-in citizens a clear message instead of Frappe's "Not Permitted" page.
"""
import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response

ROUTES = {"hasiruratha": "app.html", "hasiruratha/index": "app.html", "citizen": "citizen.html", "citizen/index": "citizen.html"}


class HasirurathaRenderer(BaseRenderer):
	"""The old single-page apps (/hasiruratha for volunteers, /citizen for citizens) are retired: volunteers
	and admins work in the Frappe Desk, citizens on the website pages. Old links and bookmarks redirect."""

	def can_render(self):
		return (self.path or "").strip("/ ") in ROUTES

	def render(self):
		from hasiruratha import api
		from hasiruratha.web_context import need_member_url

		if ROUTES[(self.path or "").strip("/ ")] == "citizen.html":
			return _redirect("/my-requests" if frappe.session.user != "Guest" else "/trees")
		user = frappe.session.user
		if user != "Guest" and api._is_admin(user):
			return _redirect("/desk/hasiruratha/hasiru_ratha_admin")
		go = need_member_url("/hasiruratha")
		if go:     # visitors sign in; signed-in citizens are told why they cannot come in
			return _redirect("/volunteer-login" if go.startswith("/volunteer-login") else go)
		return _redirect("/desk/hasiruratha/hasiru_ratha")


def _redirect(location):
	resp = Response(status=302)
	resp.headers["Location"] = location
	resp.headers["Cache-Control"] = "no-store"
	return resp


class _RedirectTo(HTTPException):
	"""Frappe returns an HTTPException's own response as is, so this works from a before_request hook."""
	code = 302

	def __init__(self, location):
		super().__init__()
		self.location = location

	def get_response(self, environ=None, scope=None):
		return _redirect(self.location)


def desk_guard():
	"""before_request: a signed-in citizen (Website User) who opens the admin area would get Frappe's bare
	"Not Permitted" page. Send them to /sign-in-needed, which explains it and offers volunteer registration.
	(Frappe v16 serves /desk before any app page renderer, so this cannot be a renderer.)"""
	req = getattr(frappe.local, "request", None)
	if not req or req.method != "GET" or frappe.session.user == "Guest":
		return
	path = (req.path or "").strip("/")
	if path.split("/")[0] not in ("desk", "app"):
		return
	if frappe.get_cached_value("User", frappe.session.user, "user_type") != "Website User":
		return
	from urllib.parse import urlencode

	raise _RedirectTo("/sign-in-needed?" + urlencode({"for": "/" + path}))
