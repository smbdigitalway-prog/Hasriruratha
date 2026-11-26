"""Add the citizen tracking pages (/my-reports, /my-trees) to the 'My account' menu and send citizens there after they submit.

Safe to run more than once:
  bench --site <site> execute hasiruratha.patches.v1_0.add_citizen_tracking.execute
"""
import frappe

MENU = [("My reports", "/my-reports"), ("My trees", "/my-trees")]
AFTER_SUBMIT = {"report-a-tree": "/my-reports", "plant-a-tree": "/my-trees"}


def execute():
    add_menu()
    redirect_forms()
    frappe.clear_cache()


def add_menu():
    try:
        ps = frappe.get_doc("Portal Settings")
        have = {r.route for r in ps.get("custom_menu") or []}
        for title, route in MENU:
            if route not in have:
                ps.append("custom_menu", {"title": title, "route": route, "enabled": 1})
        ps.save(ignore_permissions=True)
        print("[hasiruratha] My account menu: My reports, My trees")
    except Exception as e:
        print(f"[hasiruratha] menu not added ({e}). Add them by hand in Portal Settings > Custom Menu.")


def redirect_forms():
    for route, url in AFTER_SUBMIT.items():
        name = frappe.db.get_value("Web Form", {"route": route}, "name")
        if name:
            frappe.db.set_value("Web Form", name, "success_url", url)
            print(f"[hasiruratha] /{route}: after submit go to {url}")
    frappe.db.commit()
