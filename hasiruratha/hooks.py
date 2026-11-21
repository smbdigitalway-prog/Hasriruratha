app_name = "hasiruratha"
app_title = "Hasiruratha"
app_publisher = "Hasiru Ratha"
app_description = "Hasiru Ratha plantation tracker - sites, trees, visits, volunteers"
app_email = "hello@hasiruratha.example"
app_license = "mit"

# Frappe v15 / v16
required_apps = []

# Serve the volunteer app at  /hasiruratha  (full-screen, no website navbar)
page_renderer = ["hasiruratha.renderer.HasirurathaRenderer"]
before_request = ["hasiruratha.renderer.desk_guard"]

# Create roles, settings and the starter zones on install and after every migrate (idempotent)
after_install = "hasiruratha.install.after_install"
after_migrate = "hasiruratha.install.after_install"


# keep the citizen's copy of a report / volunteer request in step with the real record
doc_events = {
	"HR Tree Report": {"on_update": "hasiruratha.citizen_forms.sync_report_status"},
	"HR Application": {"on_update": "hasiruratha.citizen_forms.sync_application_status"},
}

# Website (design handoff v1): the HR … Web Templates share one stylesheet and a few data helpers
web_include_css = ["/assets/hasiruratha/css/hr_website.css"]
jinja = {"methods": [
	"hasiruratha.website.hr_impact",
	"hasiruratha.website.hr_diary",
	"hasiruratha.website.hr_blog_posts",
	"hasiruratha.website.hr_links",
	"hasiruratha.website.hr_account",
]}
