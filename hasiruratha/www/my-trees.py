import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.throw("Please log in to track your trees", frappe.PermissionError)
    context.no_cache = 1
    context.title = "My trees"
