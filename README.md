# Hasiruratha (Frappe app)

Hasiru Ratha plantation tracker rebuilt on Frappe. Same volunteer app (map, zones, sites,
trees, visits, team, dashboard), same look, now backed by real DocTypes instead of a Google Sheet.

* Volunteer app: `/hasiruratha`  (mobile number sign-in)
* Admin: the normal Frappe desk `/app` (roles **HR Admin** or **System Manager**), and the same
  `/hasiruratha` page once signed in as an admin

## DocTypes (1:1 with the old Sheet tabs)

| Sheet tab   | DocType        | Name (primary key) |
|-------------|----------------|--------------------|
| Zones       | HR Zone        | zone_id            |
| Sites       | HR Site        | site_id            |
| Trees       | HR Tree        | tree_id            |
| Visits      | HR Visit       | visit_id           |
| Conditions  | HR Condition   | condition_id       |
| Volunteers  | HR Volunteer   | volunteer_id       |
| -           | Hasiruratha Settings (single) | Google keys, login switches |

Column names are unchanged except `Sites.name -> site_name` and `Volunteers.name -> volunteer_name`
(Frappe reserves `name`). The browser app still sees `name`.

## Install

    bench get-app https://github.com/<you>/hasiruratha
    bench --site <site> install-app hasiruratha
    bench --site <site> migrate

Then open **Hasiruratha Settings** and fill in:

Both Google keys are **optional**. With the fields empty the app uses free OpenStreetMap everywhere
(maps in the Desk and website, road/area lookup from a pin, and place search). Add keys later only if you want
Google's address quality:

1. *Maps JavaScript key (browser)* - restrict by HTTP referrer to your site URL
2. *Geocoding key (server)* - a SEPARATE key, restricted to the Geocoding API only

## Local demo data

    bench --site <site> execute hasiruratha.install.make_demo_data

## Backend API

Browser -> `POST /api/method/hasiruratha.api.call` with `action` + JSON `data`
(same action names as the old Apps Script). Also: `login_phone`, `register_phone`, `upload_photo`.

## Test locally (Frappe v15 dev bench)

    cd ~/frappe-bench
    bench get-app /path/to/hasiruratha          # or the GitHub URL once pushed
    bench new-site hasiruratha.localhost --install-app hasiruratha
    bench --site hasiruratha.localhost execute hasiruratha.install.make_demo_data   # optional sample data
    bench start
    # open http://hasiruratha.localhost:8000/hasiruratha

* Admin: tick "Admin login" on the first screen -> normal Frappe login (Administrator or a user with role HR Admin)
* Volunteer: register with a mobile number on the same screen
* Automated check: `python tools/smoke_test.py` (server must be running)

Geolocation on a phone needs HTTPS (or localhost). Use Frappe Cloud / a tunnel for real phone GPS tests.

## Deploy on Frappe Cloud

1. Push this folder to a GitHub repo (the repo root must contain `pyproject.toml` and the `hasiruratha/` package).
2. Frappe Cloud -> Apps -> *Add App* -> from GitHub -> pick the repo/branch.
3. Create a Bench Group (Frappe v15) with this app, deploy, then *New Site* on that bench with the app installed.
4. On the site open *Hasiruratha Settings*, add the two Google keys, then visit `https://<site>/hasiruratha`.
5. Create your admin users in Frappe and give them the role **HR Admin**.

Importing the old Sheet: Frappe *Data Import* per DocType, in this order: HR Zone, HR Volunteer, HR Site, HR Tree, HR Visit, HR Condition.
Use the Sheet headers; rename `name` to `site_name` / `volunteer_name`, and put the old ID in `site_id` / `tree_id` / etc.


## Duplicate sites
New sites close to an existing one (25 m, or same road/area within 150 m) are set to *Needs Review* and an admin approves or merges them. See `docs/PROJECT_NOTES.md`.
Actions: `getNearbySites` (all members), `approveSite` / `mergeSite` (admin).


## Admin Console (Desk -> Hasiru Ratha Console)
Every action needs photo evidence and a place the admin can see.

* **Find a place** (used by Report, Visit and Assign): type an area, road or tree ID, tap an area/road chip to browse,
  use *My location*, or tap the map. Results are cards with photo, tree/site ID, road, area, GPS, status, and
  *Already reported* / *Visit planned* badges. Nothing is typed blind.
* **Plant a sapling**: search or pin the spot (drag to adjust), road and area fill in by themselves, photo is mandatory.
  If a tree or site is within 25 m the admin sees the neighbours with photos and chooses *Move the pin*,
  *Find a free spot for me* or *Plant anyway* (goes to duplicate review).
* **Report a tree**: pick the tree from the cards (photo + GPS). If it already has an open report the admin is told
  which one and must tick *Report again anyway*. Photo mandatory.
* **Plan a visit**: pick the site card (area, road, GPS, photo). The site photo is used as evidence, or the admin attaches one.
  The visit keeps area and zone; a second visit for the same site and day asks for confirmation.
* **Assign a volunteer**: pick the report or tree card; volunteers from the same area are listed first.

Server side: `hasiruratha/hasiruratha/page/hr_console/hr_console.py` (`find_places`, `find_reports`, `check_spot`,
`where_is`, `search_map`, `plant_sapling`, `report_tree`, `plan_visit`, `assign`). All refuse a request without a photo.
Check on a dev bench: paste `tools/test_console_evidence.py` into `bench console` and run `run()`.
