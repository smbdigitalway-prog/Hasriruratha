import frappe

from hasiruratha.api import citizen

no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.title = "Plant a tree"
    context.is_guest = frappe.session.user == "Guest"
    context.form = citizen.form_def("plant")
    context.cf = {"mode": "plant", "heading": "Plant a tree", "sub": "Four short steps: choose the spot, add a photo, answer a few questions, send. Our team checks the spot before planting.", "path": "/plant"}
