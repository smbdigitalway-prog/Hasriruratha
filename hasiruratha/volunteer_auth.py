# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
Volunteer accounts.

* Sign up (/volunteer-signup): name, mobile, email, Door/Cross/Main, road, area, pin code and zone
  are all required. The email is confirmed with a one-time code and the volunteer chooses a password.
  A signed-in citizen can upgrade: the same account keeps its requests. The volunteer is inactive
  until an admin approves the HR Application (HR Application form -> Approve).
* Sign in (/hasiruratha): mobile number + password. Admins use the same screen.
* Forgot / set password (/volunteer-reset): code sent to the volunteer's email. Volunteers who were
  added by an admin (or imported) and never had a password use the same screen to set one.
"""
import re
import secrets

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, validate_email_address
from frappe.utils.password import update_password

from hasiruratha import api, citizen_api, citizen_auth, otp

MIN_PASSWORD = 8
PLACEHOLDER_EMAIL = re.compile(r"@volunteer\.hasiruratha\.local$")


# ───────────────────────────── helpers ─────────────────────────────
def _users_with_mobile(mobile10):
	out = []
	for u in frappe.get_all("User", {"mobile_no": ["like", "%" + mobile10], "enabled": 1}, ["name", "mobile_no"]):
		if api._last10(u.mobile_no) == mobile10:
			out.append(u.name)
	return out


def _check_password(pwd):
	pwd = pwd or ""
	if len(pwd) < MIN_PASSWORD:
		frappe.throw(_("Please choose a password of at least {0} characters").format(MIN_PASSWORD))
	if pwd.isdigit() or pwd.lower() == pwd and pwd.isalpha():
		frappe.throw(_("Please mix letters with numbers or symbols in the password"))
	return pwd


def _account_for(mobile10):
	"""User account that a volunteer/admin signs in with, found by mobile number."""
	users = _users_with_mobile(mobile10)
	vol = api._find_volunteer(mobile10)
	if vol and vol.user and frappe.db.exists("User", vol.user):
		if vol.user not in users:
			users.insert(0, vol.user)
	if not users:
		return None, vol
	# prefer the account linked to the volunteer record, then a privileged one
	users.sort(key=lambda u: (u != (vol.user if vol else None), not (api.PRIVILEGED & set(frappe.get_roles(u)))))
	return users[0], vol


# ───────────────────────────── sign up ─────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def signup_start(full_name=None, mobile=None, email=None, address=None, road=None, area=None, pincode=None,
                 zone=None, reason=None):
	me = frappe.session.user
	if me != "Guest":
		if api.PRIVILEGED & set(frappe.get_roles(me)):
			frappe.throw(_("You are signed in as an admin. Sign out first."))
		mobile = mobile or frappe.db.get_value("User", me, "mobile_no")
		email = email or me
	mobile10, email = citizen_auth._clean(mobile, email)
	p = frappe._dict(full_name=(full_name or "").strip()[:60], address=(address or "").strip()[:200],
	                 road=(road or "").strip()[:140], area=(area or "").strip()[:140], pincode=api._digits(pincode),
	                 zone=zone, reason=(reason or "").strip()[:500], mobile=mobile10, email=email)
	missing = [label for label, v in (("name", p.full_name), ("Door no / Cross / Main", p.address), ("road", p.road),
	                                  ("area", p.area), ("zone", p.zone)) if not v]
	if missing:
		frappe.throw(_("Please fill in: {0}").format(", ".join(missing)))
	if len(p.pincode) != 6:
		frappe.throw(_("Please enter the 6-digit pin code"))
	if not frappe.db.exists("HR Zone", p.zone):
		frappe.throw(_("Please choose your zone"))

	vol = api._find_volunteer(mobile10)
	if vol and cint(vol.active) and vol.user:
		frappe.throw(_("This mobile number is already registered as a volunteer. Please sign in."))
	if me == "Guest":
		user = frappe.db.get_value("User", {"email": email}, "name")
		if user:
			if api.PRIVILEGED & set(frappe.get_roles(user)):
				frappe.throw(_("This email cannot be used here. Please use a different email."))
			if api._last10(frappe.db.get_value("User", user, "mobile_no")) != mobile10:
				frappe.throw(_("This email is linked to a different mobile number."))
		elif [u for u in _users_with_mobile(mobile10) if u != email]:
			frappe.throw(_("This mobile number is linked to a different email."))
	elif api._last10(frappe.db.get_value("User", me, "mobile_no")) != mobile10 or email != me:
		frappe.throw(_("Please use the mobile number and email you signed in with."))

	otp.send_code("volunteer_signup", email, email, dict(p), subject=_("Confirm your Hasiru Ratha volunteer sign-up"))
	return {"success": True, "sent_to": citizen_auth._mask(email)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def signup_verify(email=None, code=None, password=None):
	email = (email or "").strip().lower()
	pwd = _check_password(password)
	p = otp.check_code("volunteer_signup", email, code)
	user = frappe.db.get_value("User", {"email": email}, "name")
	if user and api.PRIVILEGED & set(frappe.get_roles(user)):
		frappe.throw(_("This email cannot be used here."))
	if not user:
		frappe.get_doc({
			"doctype": "User", "email": email, "first_name": p.full_name, "mobile_no": p.mobile, "enabled": 1,
			"user_type": "Website User", "send_welcome_email": 0, "new_password": secrets.token_urlsafe(24),
			"roles": [{"role": citizen_auth.CITIZEN_ROLE}],
		}).insert(ignore_permissions=True)
		user = email
	update_password(user, pwd)
	vol = api._find_volunteer(p.mobile)
	if vol and not vol.user:
		# volunteer added by an admin / imported: link this account to it
		frappe.db.set_value("HR Volunteer", vol.name, {"user": user, "email": email})
	res = citizen_api.apply_core(user, email, p.area, p.reason, None, {
		"full_name": p.full_name, "mobile": p.mobile, "address": p.address, "road": p.road,
		"pincode": p.pincode, "zone": p.zone})
	vol_name = res.get("volunteer") or frappe.db.get_value("HR Volunteer", {"user": user}, "name")
	if vol_name:
		frappe.db.set_value("HR Volunteer", vol_name, {"address": p.address, "road": p.road, "area": p.area,
		                                               "pincode": p.pincode, "primary_zone_id": p.zone})
	if frappe.session.user == "Guest":
		frappe.local.login_manager.login_as(user)
	return {"success": True, "approved": bool(res.get("already")), "pending": not res.get("already")}


# ───────────────────────────── sign in ─────────────────────────────
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=300)
def login(mobile=None, password=None):
	mobile10 = api._last10(mobile)
	if len(mobile10) < 10 or not password:
		return {"success": False, "error": _("Enter your mobile number and password.")}
	user, vol = _account_for(mobile10)
	generic = _("Mobile number or password is not correct.")
	if not user:
		if vol:
			return {"success": False, "need_password": True,
			        "error": _("You have not set a password yet. Tap “Forgot or set password”.")}
		return {"success": False, "error": generic}
	try:
		frappe.local.login_manager.authenticate(user=user, pwd=password)
	except frappe.AuthenticationError:
		return {"success": False, "error": generic}
	except frappe.SecurityException:
		return {"success": False, "error": _("Too many attempts. Please wait a few minutes.")}
	roles = set(frappe.get_roles(user))
	is_admin = bool(api.PRIVILEGED & roles)
	if not is_admin and api.VOLUNTEER_ROLE not in roles:
		if frappe.db.get_value("HR Volunteer", {"user": user}, "name"):
			return {"success": False, "error": _("Thank you for signing up! An admin still has to approve you. We will email you.")}
		return {"success": False, "error": _("This account is not a volunteer account. Citizens raise requests at /request.")}
	if vol and not cint(vol.active) and not is_admin:
		return {"success": False, "error": _("Your volunteer account is inactive. Please contact the Hasiru Ratha team.")}
	frappe.local.login_manager.post_login()
	frappe.form_dict.pop("password", None)
	return {"success": True, "is_admin": is_admin}


# ───────────────────────────── forgot / set password ─────────────────────────────
def _reset_target(mobile10):
	user, vol = _account_for(mobile10)
	email = None
	if user and not PLACEHOLDER_EMAIL.search(user):
		email = frappe.db.get_value("User", user, "email")
	elif vol:
		email = (frappe.db.get_value("HR Volunteer", vol.name, "email") or "").strip().lower() or None
	return user, vol, email


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=900)
def reset_start(mobile=None):
	mobile10 = api._last10(mobile)
	if len(mobile10) < 10:
		frappe.throw(_("Please enter your 10-digit mobile number"))
	user, vol, email = _reset_target(mobile10)
	if not (user or vol):
		return {"success": False, "error": _("We could not find a volunteer with this mobile number.")}
	if user and api.PRIVILEGED & set(frappe.get_roles(user)) and not vol:
		return {"success": False, "error": _("Admins reset their password from the admin login page.")}
	if not email or not validate_email_address(email):
		return {"success": False, "error": _("We do not have an email for this number. Please ask an admin to add your email.")}
	otp.send_code("volunteer_reset", mobile10, email, {"email": email}, subject=_("Reset your Hasiru Ratha password"))
	return {"success": True, "sent_to": citizen_auth._mask(email)}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=900)
def reset_verify(mobile=None, code=None, password=None):
	mobile10 = api._last10(mobile)
	pwd = _check_password(password)
	data = otp.check_code("volunteer_reset", mobile10, code)
	user, vol, email = _reset_target(mobile10)
	if (not user or PLACEHOLDER_EMAIL.search(user)) and not vol:
		frappe.throw(_("We could not find a volunteer with this mobile number."))
	if not user or PLACEHOLDER_EMAIL.search(user):
		# volunteer added by an admin / imported (or from the old mobile-only sign-in): give them a
		# real account on the email we just confirmed, and retire the placeholder one
		if frappe.db.exists("User", data.email):
			frappe.throw(_("This email already belongs to another account. Please contact the Hasiru Ratha team."))
		frappe.get_doc({
			"doctype": "User", "email": data.email, "first_name": vol.volunteer_name or "Volunteer", "mobile_no": mobile10,
			"enabled": 1, "user_type": "Website User", "send_welcome_email": 0, "new_password": secrets.token_urlsafe(24),
			"roles": [{"role": api.VOLUNTEER_ROLE}] if cint(vol.active) else [],
		}).insert(ignore_permissions=True)
		if user:
			frappe.db.set_value("User", user, "enabled", 0)
		user = data.email
		frappe.db.set_value("HR Volunteer", vol.name, "user", user)
	update_password(user, pwd)
	return {"success": True}
