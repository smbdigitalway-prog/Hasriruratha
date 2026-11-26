import frappe

from hasiruratha.api import citizen

no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.title = "Report a tree"
    context.is_guest = frappe.session.user == "Guest"
    context.form = citizen.form_def("report")
    context.cf = {"mode": "report", "heading": "Report a tree", "sub": "Four short steps: find the tree, add a photo, tell us what is wrong, send. You can follow the status under My reports.", "path": "/report"}
