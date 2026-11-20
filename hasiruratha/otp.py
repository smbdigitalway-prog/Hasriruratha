# Copyright (c) 2026, Hasiru Ratha and contributors
# For license information, please see license.txt
"""
One-time codes sent by email (citizen sign-in, volunteer sign-up, volunteer password reset).

* 6 digits, valid for 10 minutes, 5 wrong tries then the code is thrown away.
* One email per address per 60 seconds.
* Needs an outgoing Email Account on the site. If sending fails the citizen is told so and the
  code is discarded - the site never pretends a code was sent.

SMS / WhatsApp later: add a sender in `_deliver` (Frappe SMS Settings, MSG91, WhatsApp Cloud API).
"""
import secrets

import frappe
from frappe import _

TTL = 600
MAX_TRIES = 5
RESEND_GAP = 60


def _cache():
	return frappe.cache() if callable(frappe.cache) else frappe.cache


def _key(purpose, ident):
	return "hr_otp:%s:%s" % (purpose, (ident or "").strip().lower())


def send_code(purpose, ident, email, data=None, subject=None):
	"""Create a code for (purpose, ident), email it, remember `data` with it."""
	email = (email or "").strip().lower()
	gap = "hr_otp_gap:%s" % email
	if _cache().get_value(gap):
		frappe.throw(_("A code was sent a moment ago. Please wait a minute before asking again."))
	code = "%06d" % secrets.randbelow(10**6)
	_cache().set_value(_key(purpose, ident), {"code": code, "email": email, "tries": 0, "data": data or {}},
	                   expires_in_sec=TTL)
	try:
		_deliver(email, code, subject)
	except Exception:
		_cache().delete_value(_key(purpose, ident))
		frappe.log_error(title="Hasiru Ratha: one-time code email failed")
		frappe.throw(_("We could not send the email right now. Please try again later."))
	_cache().set_value(gap, 1, expires_in_sec=RESEND_GAP)


def _deliver(email, code, subject=None):
	frappe.sendmail(
		recipients=[email], now=True,
		subject=subject or _("Your Hasiru Ratha code: {0}").format(code),
		message=_("<p>Your Hasiru Ratha code is</p><h2 style='letter-spacing:4px'>{0}</h2>"
		          "<p>It is valid for 10 minutes. If you did not ask for it, ignore this email.</p>").format(code),
	)


def check_code(purpose, ident, code):
	"""Return the stored data if `code` is right, else raise. A right code can only be used once."""
	key = _key(purpose, ident)
	rec = _cache().get_value(key)
	if not rec:
		frappe.throw(_("This code has expired. Please ask for a new one."))
	if rec["tries"] >= MAX_TRIES:
		_cache().delete_value(key)
		frappe.throw(_("Too many wrong codes. Please ask for a new one."))
	if not secrets.compare_digest(str(code or "").strip(), rec["code"]):
		rec["tries"] += 1
		_cache().set_value(key, rec, expires_in_sec=TTL)
		frappe.throw(_("That code is not correct."))
	_cache().delete_value(key)
	return frappe._dict(rec["data"])
