"""Checks for the upgraded Hasiru Ratha Console (photo evidence, duplicates, area/road search).

Run on a dev bench:   paste the file into `bench --site <site> console` and call run()
Needs an admin session (Administrator is fine). Creates and removes its own records (deleted sites leave a copy in HR Deleted Site, as always).
"""
import frappe

from hasiruratha.hasiruratha.page.hr_console import hr_console as c


def run():
	frappe.set_user("Administrator")
	out = []

	def check(name, ok):
		out.append(("PASS" if ok else "FAIL", name))

	def throws(fn, **kw):
		try:
			fn(**kw)
			return False
		except Exception:
			return True

	# 1. no photo -> refused everywhere
	check("plant without photo is refused", throws(c.plant_sapling, gps_lat=12.9, gps_lng=77.58, road="Test Rd", area="Test Area"))
	check("report without photo is refused", throws(c.report_tree, tree_id="X", issue_type="Watering"))
	check("visit without site is refused", throws(c.plan_visit, planned_date=frappe.utils.today(), photo_url="/files/x.jpg"))

	# 2. plant -> duplicate on the same pin -> free spot
	lat, lng = 12.912345, 77.583456
	r1 = c.plant_sapling(gps_lat=lat, gps_lng=lng, road="Evidence Test Road", area="Evidence Test Area", photo_url="/files/test.jpg", count=1)
	check("first planting works", r1.get("success") and r1.get("tree_ids"))
	r2 = c.plant_sapling(gps_lat=lat, gps_lng=lng, road="Evidence Test Road", area="Evidence Test Area", photo_url="/files/test.jpg")
	check("second planting on the same pin is flagged as duplicate", r2.get("duplicate") is True)
	check("a free spot is offered", bool(r2.get("free_spot")))
	fs = r2["free_spot"]
	r3 = c.plant_sapling(gps_lat=fs["lat"], gps_lng=fs["lng"], road="Evidence Test Road", area="Evidence Test Area", photo_url="/files/test.jpg", force=1)
	check("planting on the suggested free spot works", r3.get("success"))

	# 3. find by area / road / tree id, with photo and GPS
	res = c.find_places(q="Evidence Test")
	check("search by area text finds the trees", len(res["trees"]) >= 2)
	t = res["trees"][0]
	check("card has photo, GPS, area and road", t["photo"] and t["lat"] and t["area"] and t["road"])
	check("search by tree id works", len(c.find_places(q=r1["tree_ids"][0])["trees"]) >= 1)
	check("search near a pin works", len(c.find_places(lat=lat, lng=lng, radius=50)["trees"]) >= 1)

	# 4. report once, second time says "already reported"
	rep = c.report_tree(tree_id=r1["tree_ids"][0], issue_type="Watering", photo_url="/files/test.jpg")
	check("report saved", rep.get("success"))
	again = c.report_tree(tree_id=r1["tree_ids"][0], issue_type="Watering", photo_url="/files/test.jpg")
	check("second report is told it is already reported", again.get("already_reported") is True)
	check("find_places shows the open report on the card", bool(c.find_places(q=r1["tree_ids"][0])["trees"][0]["open_reports"]))

	# 5. visit uses the site photo, keeps area, and warns about a same-day duplicate
	site = r1["site_id"]
	v1 = c.plan_visit(site_id=site, planned_date=frappe.utils.today())
	check("visit planned with the site photo", v1.get("success"))
	check("visit stores the area", frappe.db.get_value("HR Visit", v1["visit_id"], "area") == "Evidence Test Area")
	check("same-day visit is flagged", c.plan_visit(site_id=site, planned_date=frappe.utils.today()).get("already_planned") is True)

	# clean up
	for dt, f in (("HR Visit", {"site_id": site}), ("HR Tree Report", {"site_id": site})):
		for n in frappe.get_all(dt, f, pluck="name"):
			frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
	for s in {r1["site_id"], r3["site_id"]}:
		for n in frappe.get_all("HR Duplicate Report", {"site": s}, pluck="name"):
			frappe.delete_doc("HR Duplicate Report", n, force=True, ignore_permissions=True)
		for n in frappe.get_all("HR Tree", {"site_id": s}, pluck="name"):
			frappe.delete_doc("HR Tree", n, force=True, ignore_permissions=True)
		frappe.delete_doc("HR Site", s, force=True, ignore_permissions=True)
	frappe.db.commit()
	for status, name in out:
		print(status, name)
	print("%d/%d passed" % (sum(1 for s, _ in out if s == "PASS"), len(out)))
	return out
