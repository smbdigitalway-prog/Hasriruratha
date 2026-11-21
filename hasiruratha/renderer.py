# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Serves the single-page volunteer app at /hasiruratha.

The page is a plain HTML file (templates/app.html). We only fill in three things per request:
  __HR_BOOT__     who is signed in + the CSRF token (JSON)
  __GMAPS_KEY__   Google Maps JavaScript key from "Hasiruratha Settings" (never hard-coded in the repo)
"""
import json
import os

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response

ROUTES = {"hasiruratha": "app.html", "hasiruratha/index": "app.html", "citizen": "citizen.html", "citizen/index": "citizen.html"}
_cached = {}


def _template(name):
	path = os.path.join(os.path.dirname(__file__), "templates", name)
	m = os.path.getmtime(path)
	hit = _cached.get(name)
	if not hit or hit["mtime"] != m:
		with open(path, encoding="utf-8") as f:
			hit = _cached[name] = {"mtime": m, "html": f.read()}
	return hit["html"]


class HasirurathaRenderer(BaseRenderer):
	def can_render(self):
		return (self.path or "").strip("/ ") in ROUTES

	def render(self):
		from hasiruratha.api import build_boot

		tpl = ROUTES[(self.path or "").strip("/ ")]
		if tpl == "citizen.html":
			u = frappe.session.user
			boot = {"logged_in": u != "Guest"}
			if u != "Guest":
				boot["user"] = {"name": frappe.utils.get_fullname(u), "email": u}
		else:
			boot = build_boot()
			if not boot.get("logged_in"):
				# visitors sign in on /volunteer-login; signed-in citizens are told why they cannot come in
				# (no "come back here" for visitors: /hasiruratha is the normal way in, and admins go to the Desk)
				from hasiruratha.web_context import need_member_url

				go = need_member_url("/hasiruratha") or "/volunteer-login"
				return _redirect("/volunteer-login" if go.startswith("/volunteer-login") else go)
		try:
			boot["csrf_token"] = frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else ""
		except Exception:
			boot["csrf_token"] = ""
		maps_key = frappe.db.get_single_value("Hasiruratha Settings", "google_maps_browser_key") or ""

		blob = json.dumps(boot).replace("</", "<\\/")
		html = _template(tpl).replace("__HR_BOOT__", blob).replace("__GMAPS_KEY__", maps_key)

		resp = Response(html, status=200, content_type="text/html; charset=utf-8")
		resp.headers["Cache-Control"] = "no-store"
		return resp


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
