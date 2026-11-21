import frappe

from hasiruratha import web_context

no_cache = 1


def get_context(context):
	web_context.require_member("/green-diary-new")
	web_context.base(context, "diary", "Add to the Green Diary")
