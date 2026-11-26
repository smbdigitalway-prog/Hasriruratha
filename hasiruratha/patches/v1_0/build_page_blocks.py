"""Create the Hasiru Ratha Page Builder blocks (Web Templates) and rebuild /hasiru-ratha with them.

Replaces the old single-HTML page. Safe to run more than once.
  bench --site <site> execute hasiruratha.patches.v1_0.build_page_blocks.execute
"""
import json
import os

import frappe

APP = "hasiruratha"
PAGE_ROUTE = "hasiru-ratha"
IMG = f"/assets/{APP}/images/site"
BLOCK_DIR = ("website_content", "blocks")

D, T, I, TB = "Data", "Small Text", "Attach Image", "Table Break"


def f(fieldname, label, fieldtype=D, default=None):
	return {"fieldname": fieldname, "label": label, "fieldtype": fieldtype, "default": default}


# name -> (html file, fields).  A Table Break must come last: the fields after it are the table's columns.
BLOCKS = {
	"HR Block Hero": ("hr_block_hero.html", [
		f("eyebrow", "Small heading"), f("headline", "Headline (line 1)"), f("headline_accent", "Headline (green line 2)"),
		f("text", "Text", T), f("button_label", "Button label"), f("button_link", "Button link"),
		f("image", "Photo", I), f("image_alt", "Photo description")]),
	"HR Block Actions": ("hr_block_actions.html", [
		f("heading", "Heading"), f("subtext", "Text", T), f("cards", "Cards", TB),
		f("title", "Title"), f("text", "Text", T), f("button_label", "Button label"),
		f("button_link", "Button link"), f("image", "Photo", I), f("image_alt", "Photo description")]),
	"HR Block Login": ("hr_block_login.html", [
		f("title", "Title"), f("text", "Text", T), f("login_label", "Log in label"), f("login_link", "Log in link"),
		f("signup_label", "Sign up label"), f("signup_link", "Sign up link")]),
	"HR Block Impact": ("hr_block_impact.html", [
		f("stats", "Numbers", TB), f("number", "Number"), f("label", "Label")]),
	"HR Block Work": ("hr_block_work.html", [
		f("heading", "Heading"), f("subtext", "Text", T), f("tiles", "Tiles", TB),
		f("title", "Title"), f("text", "Text", T), f("image", "Photo", I)]),
	"HR Block About": ("hr_block_about.html", [
		f("eyebrow", "Small heading"), f("heading", "Heading"), f("subheading", "Sub heading"), f("text", "Text", T),
		f("image", "Photo", I), f("image_alt", "Photo description"), f("points", "Points", TB),
		f("point_title", "Title"), f("point_text", "Text", T)]),
	"HR Block Diary": ("hr_block_diary.html", [
		f("heading", "Heading"), f("subtext", "Text", T), f("entries", "Diary photos (first one is shown large)", TB),
		f("image", "Photo", I), f("caption", "Caption"), f("place", "Place / date")]),
	"HR Block People": ("hr_block_people.html", [
		f("left_eyebrow", "Left small heading"), f("left_heading", "Left heading"), f("left_text", "Left text", T),
		f("right_eyebrow", "Right small heading"), f("right_heading", "Right heading"), f("right_text", "Right text", T),
		f("button_label", "Button label"), f("button_link", "Button link")]),
	"HR Block Connect": ("hr_block_connect.html", [
		f("heading", "Heading"), f("text", "Text", T), f("links", "Links", TB), f("label", "Label"), f("url", "URL")]),
}

# Web Forms are found by the DocType they save into; fallbacks used if none is published.
FORM_FOR = {
	"plant": ("HR Citizen Planting", "/plant-a-tree"),
	"report": ("HR Citizen Report", "/report-a-tree"),
	"volunteer": ("HR Volunteer Request", "/become-a-volunteer"),
	"intern": ("HR Internship Application", "/internship"),
}


def page_values(u):
	p = lambda n: f"{IMG}/photo{n:02d}.jpg"
	return [
		("HR Block Hero", {
			"eyebrow": "Citizen-led since 2017", "headline": "We don't just plant trees.", "headline_accent": "We help them grow.",
			"text": "Early mornings, neighbourhood streets and a shared commitment to caring for Bengaluru's trees.",
			"button_label": "Be part of it", "button_link": "#hr-join", "image": p(3),
			"image_alt": "Hasiru Ratha volunteers caring for a sapling"}),
		("HR Block Actions", {
			"heading": "Be part of it", "subtext": "Three simple ways to help Bengaluru's trees. Pick one and it takes less than a minute.",
			"cards": [
				{"title": "Plant a Tree", "text": "Tell us where a sapling can go and how many. Our team checks the spot and plans the planting.",
				 "button_label": "Plant a Tree", "button_link": u["plant"], "image": p(6), "image_alt": "Volunteers digging a planting pit"},
				{"title": "Report a Tree", "text": "Spotted a sapling that needs water, a repair or a guard? Send a photo and its location.",
				 "button_label": "Report a Tree", "button_link": u["report"], "image": p(8), "image_alt": "A sapling growing inside a tree guard"},
				{"title": "Become a Volunteer", "text": "Retirees, students and working professionals all have a place with us. Give a little time near you.",
				 "button_label": "Become a Volunteer", "button_link": u["volunteer"], "image": p(1), "image_alt": "Volunteers with a tree guard"}]}),
		("HR Block Login", {
			"title": "Citizen login", "text": "Log in with your mobile number or email to follow the status of your plantings and reports.",
			"login_label": "Log in", "login_link": "/login", "signup_label": "Create account", "signup_link": "/login#signup"}),
		("HR Block Impact", {"stats": [
			{"number": "~5,000", "label": "Saplings planted directly"}, {"number": "~8,000", "label": "Saplings maintained so far"},
			{"number": "~400", "label": "New saplings planted each year"}, {"number": "2017", "label": "Year initiative began"}]}),
		("HR Block Work", {
			"heading": "Our work, every week.", "subtext": "Plant. Nurture. Protect. Reuse.",
			"tiles": [
				{"title": "Plant", "text": "Choose appropriate locations, mindful of pathways and utilities.", "image": p(10)},
				{"title": "Nurture", "text": "Regular watering and maintenance for young saplings.", "image": p(9)},
				{"title": "Protect", "text": "Install, repair and maintain tree guards.", "image": p(7)},
				{"title": "Reuse", "text": "Free mature trees from guards and reuse them for new saplings.", "image": p(2)}]}),
		("HR Block About", {
			"eyebrow": "About us", "heading": "About Hasiru Ratha", "subheading": "The Green Chariot – Growing a Greener Bengaluru",
			"text": "Hasiru means green. Ratha means chariot. Our Maruti Omni, contributed by founder Dr Nagaraj Manya from his retirement funds, helps volunteers carry tools, materials and recovered tree guards to neighbourhood sites. The van is a practical symbol of a community that shows up, again and again.",
			"image": p(4), "image_alt": "The Hasiru Ratha van, the Green Chariot",
			"points": [
				{"point_title": "Our Meaning", "point_text": "Hasiru Ratha means Green Chariot, symbolising our journey towards a greener and healthier Bengaluru."},
				{"point_title": "Our Mission", "point_text": "To plant, protect and nurture trees while creating greener and healthier neighbourhoods."},
				{"point_title": "Our Community", "point_text": "Bringing together citizens, volunteers and nature enthusiasts to take collective environmental action."},
				{"point_title": "Our Commitment", "point_text": "Going beyond plantation by ensuring that every sapling receives care, protection and regular maintenance."}]}),
		("HR Block Diary", {
			"heading": "From the Green Diary", "subtext": "Real photographs from everyday work on the streets of south Bengaluru.",
			"entries": [
				{"image": p(5), "caption": "Every sapling gets a second look", "place": "South Bengaluru"},
				{"image": p(1), "caption": "Guards go up, saplings stay safe", "place": "Field day"},
				{"image": p(9), "caption": "Watering rounds before the sun gets hot", "place": "Neighbourhood streets"},
				{"image": p(10), "caption": "A new sapling goes in", "place": "Planting day"},
				{"image": p(6), "caption": "Digging the pit, together", "place": "Volunteers at work"}]}),
		("HR Block People", {
			"left_eyebrow": "People make this possible", "left_heading": "Age is just a number.",
			"left_text": "Retirees, students and working professionals contribute their time, skills and energy. There is a place for everyone who cares about our neighbourhood trees.",
			"right_eyebrow": "1–3 months · Documentation and storytelling", "right_heading": "Intern with Hasiru Ratha",
			"right_text": "Help record field activities, edit photographs and videos, write stories and maintain our Green Diary. A certificate may be issued after successful completion of agreed work.",
			"button_label": "Apply for internship", "button_link": u["intern"]}),
		("HR Block Connect", {
			"heading": "Stay connected.", "text": "Follow field updates and share locations where saplings need attention.",
			"links": [{"label": "Facebook", "url": "https://www.facebook.com/rathahasiru/"}, {"label": "X", "url": "https://x.com/RathaHasiru"}]}),
	]


def web_form_route(doctype, fallback):
	route = frappe.db.get_value("Web Form", {"doc_type": doctype, "published": 1}, "route")
	return "/" + route.strip("/") if route else fallback


def execute():
	make_templates()
	rebuild_page()


def make_templates():
	for name, (html_file, fields) in BLOCKS.items():
		with open(frappe.get_app_path(APP, *BLOCK_DIR, html_file), encoding="utf-8") as fh:
			html = fh.read()
		doc = frappe.get_doc("Web Template", name) if frappe.db.exists("Web Template", name) else frappe.new_doc("Web Template")
		doc.name = name
		doc.type = "Section"
		doc.standard = 0
		doc.template = html
		doc.set("fields", [])
		for fd in fields:
			row = {"fieldname": fd["fieldname"], "label": fd["label"], "fieldtype": fd["fieldtype"], "reqd": 0}
			if fd["default"]:
				row["default"] = fd["default"]
			doc.append("fields", row)
		doc.save(ignore_permissions=True) if not doc.is_new() else doc.insert(ignore_permissions=True)
		print(f"[hasiruratha] block ready: {name}")


def rebuild_page():
	name = frappe.db.get_value("Web Page", {"route": PAGE_ROUTE}, "name")
	if name:
		doc = frappe.get_doc("Web Page", name)
		backup = frappe.get_site_path("private", "files", f"web_page_{name}_before_blocks.json")
		with open(backup, "w") as fh:
			json.dump(doc.as_dict(), fh, default=str, indent=1)
		print(f"[hasiruratha] old page backed up to {backup}")
	else:
		doc = frappe.new_doc("Web Page")
		doc.title = "Hasiru Ratha – Greener Bengaluru"
		doc.route = PAGE_ROUTE

	urls = {k: web_form_route(*v) for k, v in FORM_FOR.items()}
	urls["plant"], urls["report"] = "/plant", "/report"   # guided citizen pages
	doc.content_type = "Page Builder"
	doc.main_section_html = ""
	if doc.meta.has_field("slideshow"):
		doc.slideshow = None
	doc.published = 1
	doc.full_width = 1
	doc.show_title = 0
	if doc.meta.has_field("add_breadcrumbs"):
		doc.add_breadcrumbs = 0

	doc.set("page_blocks", [])
	block_meta = frappe.get_meta("Web Page Block")
	for template, values in page_values(urls):
		row = {"web_template": template, "web_template_values": json.dumps(values)}
		for key in ("add_container", "add_top_padding", "add_bottom_padding"):
			if block_meta.has_field(key):
				row[key] = 0
		doc.append("page_blocks", row)
	doc.save(ignore_permissions=True) if name else doc.insert(ignore_permissions=True)
	print(f"[hasiruratha] /{PAGE_ROUTE} rebuilt with {len(doc.page_blocks)} blocks; links:", urls)
