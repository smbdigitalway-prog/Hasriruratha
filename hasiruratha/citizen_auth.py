# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Citizen sign-in: mobile number + email, confirmed with a one-time code sent to the email.

1. start(mobile, email[, full_name])  -> emails a 6-digit code (asks for a name the first time)
2. verify(email, code, remember=1)    -> signs in; creates the citizen account on first use
3. A citizen who ticks "keep me signed in" gets a device cookie (1 year). When the normal session
   ends, resume() signs them in again from that cookie. Admins can sign a phone out by deleting its
   row in "HR Device Login".

Admin accounts can never sign in here. Volunteers may (they are citizens too).
"""
import hashlib
import secrets
from datetime import timedelta
from urllib.parse import unquote

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime, validate_email_address

from hasiruratha import api, otp

CITIZEN_ROLE = "HR Citizen"
ALLOWED_ROLES = {CITIZEN_ROLE, api.VOLUNTEER_ROLE}
DEVICE_COOKIE = "hr_device"
DEVICE_DAYS = 365


def _clean(mobile, email):
	digits = api._digits(mobile)
	email = (email or "").strip().lower()
	if len(digits) < 10:
		frappe.throw(_("Please enter a valid 10-digit mobile number"))
	if not validate_email_address(email):
		frappe.throw(_("Please enter a valid email"))
	return digits[-10:], email


def _existing_user(mobile10, email):
	"""(user or None). Raises when the pair does not fit an account we may sign in."""
	user = frappe.db.get_value("User", {"name": email}, "name") or frappe.db.get_value("User", {"email": email}, "name")
	if user:
		roles = set(frappe.get_roles(user))
		if api.PRIVILEGED & roles or not (ALLOWED_ROLES & roles):
			frappe.throw(_("This email cannot be used here. Please use a different email."))
		if api._last10(frappe.db.get_value("User", user, "mobile_no")) != mobile10:
			frappe.throw(_("This email is linked to a different mobile number."))
		if not cint(frappe.db.get_value("User", user, "enabled")):
			frappe.throw(_("This account is disabled. Please contact Hasiru Ratha."))
		return user
	for u in frappe.get_all("User", {"mobile_no": ["like", "%" + mobile10]}, pluck="name"):
		if api._last10(frappe.db.get_value("User", u, "mobile_no")) == mobile10:
			frappe.throw(_("This mobile number is linked to a different email."))
	return None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=600)
def start(mobile=None, email=None, full_name=None):
	mobile10, email = _clean(mobile, email)
	user = _existing_user(mobile10, email)
	name = (full_name or "").strip()[:60]
	if not user and not name:
		return {"success": True, "need_name": True}
	otp.send_code("citizen", email, email, {"mobile": mobile10, "email": email, "name": name, "new": not user})
	return {"success": True, "sent_to": _mask(email)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=600)
def verify(email=None, code=None, remember=1):
	email = (email or "").strip().lower()
	data = otp.check_code("citizen", email, code)
	user = _existing_user(data.mobile, email)        # re-check: things may have changed in 10 minutes
	if not user:
		frappe.get_doc({
			"doctype": "User", "email": email, "first_name": data.name or "Citizen", "mobile_no": data.mobile,
			"enabled": 1, "user_type": "Website User", "send_welcome_email": 0,
			"new_password": secrets.token_urlsafe(24), "roles": [{"role": CITIZEN_ROLE}],
		}).insert(ignore_permissions=True)
		user = email
	elif CITIZEN_ROLE not in frappe.get_roles(user):
		frappe.get_doc("User", user).add_roles(CITIZEN_ROLE)
	frappe.local.login_manager.login_as(user)
	if cint(remember):
		_remember_device(user)
	return {"success": True}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def resume():
	"""Sign in again from the 'keep me signed in' cookie."""
	if frappe.session.user != "Guest":
		return {"success": True}
	raw = _device_cookie()
	name, _sep, secret = raw.partition(":")
	row = frappe.db.get_value("HR Device Login", name, ["user", "token_hash"], as_dict=True) if name and secret else None
	if not row or not secrets.compare_digest(row.token_hash or "", _hash(secret)):
		frappe.local.cookie_manager.delete_cookie(DEVICE_COOKIE)
		return {"success": False}
	roles = set(frappe.get_roles(row.user))
	if not cint(frappe.db.get_value("User", row.user, "enabled")) or api.PRIVILEGED & roles or not (ALLOWED_ROLES & roles):
		frappe.delete_doc("HR Device Login", name, ignore_permissions=True, force=True)
		frappe.local.cookie_manager.delete_cookie(DEVICE_COOKIE)
		return {"success": False}
	frappe.local.login_manager.login_as(row.user)
	frappe.db.set_value("HR Device Login", name, "last_used", now_datetime(), update_modified=False)
	return {"success": True}


@frappe.whitelist(methods=["POST"])
def sign_out():
	raw = _device_cookie()
	name = raw.partition(":")[0]
	if name and frappe.db.get_value("HR Device Login", name, "user") == frappe.session.user:
		frappe.delete_doc("HR Device Login", name, ignore_permissions=True, force=True)
	frappe.local.cookie_manager.delete_cookie(DEVICE_COOKIE)
	frappe.local.login_manager.logout()
	return {"success": True}


@frappe.whitelist(allow_guest=True)
def me():
	user = frappe.session.user
	if user == "Guest":
		return {"logged_in": False}
	roles = set(frappe.get_roles(user))
	return {"logged_in": True, "name": frappe.utils.get_fullname(user), "email": user,
	        "mobile": frappe.db.get_value("User", user, "mobile_no") or "",
	        "is_volunteer": api.VOLUNTEER_ROLE in roles, "is_admin": bool(api.PRIVILEGED & roles)}


def _device_cookie():
	# Frappe URL-encodes cookie values when it sets them
	return unquote((frappe.request.cookies.get(DEVICE_COOKIE) or "") if frappe.request else "")


def _remember_device(user):
	secret = secrets.token_urlsafe(32)
	ua = (frappe.request.headers.get("User-Agent") or "")[:300] if frappe.request else ""
	row = frappe.get_doc({"doctype": "HR Device Login", "user": user, "token_hash": _hash(secret),
	                      "last_used": now_datetime(), "user_agent": ua}).insert(ignore_permissions=True)
	frappe.local.cookie_manager.set_cookie(DEVICE_COOKIE, "%s:%s" % (row.name, secret),
	                                       expires=now_datetime() + timedelta(days=DEVICE_DAYS), httponly=True)


def _hash(secret):
	return hashlib.sha256((secret or "").encode()).hexdigest()


def _mask(email):
	local, _at, dom = email.partition("@")
	return (local[:2] + "***@" + dom) if dom else email
