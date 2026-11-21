import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	web_context.require_member("/gps-tagging")
	web_context.base(context, "gps", "GPS tagging")
