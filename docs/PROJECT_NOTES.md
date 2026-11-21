# Hasiruratha: discussion notes and status

## Review points (11 Nov 2026)
| # | Point | Status |
|---|-------|--------|
| 1 | Walkthrough of the HR app built on the local bench | Done |
| 2 | Duplicate site detection / review / verify for user and admin | Built, needs test on Frappe Cloud (see below) |
| 3 | App did not follow Frappe UI/UX | Admin side uses Desk (workspace, list, form, number cards, ToDo). User app (`/hasiruratha`) is still a custom SPA: re-skin is a later phase |
| 4 | New bench/site on Frappe Cloud, redo doctypes | Site `hasiruratha.nvi.frappe.cloud` created, data restored |
| 5 | "Submit report" wording unsuitable for citizens | Reworded on the user screens (see CHANGELOG below) |
| 6 | Use common Frappe UI components | Number Cards, list indicators, form buttons, ToDo assignment, workspace shortcuts |
| 7 | Mobile compliant | SPA is responsive; the new "spots near you" panel is built for phones |

## Duplicate-site mechanism
Server (`hr_site.py`, runs on every new HR Site):
* a new site is flagged **Needs Review** (not blocked) when another non-merged site of the same type is within **25 m**, or is on the **same road + area within 150 m**
* "same road + area" alone is NOT used: `add_site` sets area = road, so it would flag every site on a long road
* `Possible Duplicate Of` is filled, and every HR Admin gets a ToDo

Admin (Desk):
* open the flagged HR Site: orange banner + **Review** menu: *Different site - keep it* / *Same place - merge*
* merge moves trees, visits, conditions and tree reports to the existing site, recounts trees, marks the duplicate **Merged**
* Number Cards: *Sites Needing Review*, *Volunteer Applications Pending*, *Open Tree Reports*

Citizen (Quick Add, `/hasiruratha`):
* after GPS is captured the app shows **spots near you** (300 m) as a radar plot + cards, closest first
* tap **This is my spot** to add the tree to the existing spot, or **No, this is a different spot** to create a new one
* within 30 m the user must choose one of the two before saving
* if the server still finds a near match, the user sees a thank-you message and the admin confirms

## Admin Console (Desk page `hr-console`)
Open `/app/hr-console`. Tiles: Plant a sapling (opens `/hasiruratha`), Report a tree, Plan a visit, Assign a volunteer (to a tree or a report), Review duplicates. Below: live OpenStreetMap map of all sites (orange = Needs Review, popup has Open / Plan a visit) and the duplicate queue with Different site / Merge buttons. Add a Shortcut to it in the workspace (Type = Page, Link To = hr-console).

## Planting flows
* **Quick Add (live GPS):** GPS -> spots near you (radar + cards) -> reuse a spot or create new
* **Manual Add (pin on map):** after the pin is set and Save is tapped, if a spot is within 30 m the user must choose *Use this spot* or *No, this is a different spot*
* both flows: the server still flags Needs Review if a near match slips through

## Citizen portal (`/citizen`)
* **Login:** mobile number + email, no OTP. First time also asks for a name. Creates a user with only the `HR Citizen` role. An existing email must come with the same mobile number. Admin accounts can never sign in here.
* **Dashboard:** totals (trees, zones, sites, volunteers), trees per month, trees by status, browse zones -> sites -> trees, volunteer NAMES only (phone/email are never sent to the browser).
* **Plant a tree:** photo (required) -> location from the photo, else phone GPS, else a map pin -> area/road/zone auto-filled and editable -> tree type -> "willing to volunteer?" -> save. If a spot is within 30 m the citizen is asked to reuse it.
* **Report a tree:** photo (required) -> location -> pick the nearest registered tree (or "not listed") -> issue -> send. A tree that is not in the records is saved as a flagged, unconfirmed entry for admin to verify.
* **Volunteer:** email verification code, then an HR Application (Pending, email verified) and a ToDo for HR Admins. Approve / Reject buttons on the HR Application form. Several volunteers can apply for the same tree; the first approved one becomes the tree's owner volunteer.
* **My status:** the citizen's own trees, reports (with assigned volunteer name) and volunteer application.
* **Admin side:** Console tile + panel "Citizen submissions" (photo, address, zone guess and why, who, when; confirm or change the zone; plan a visit; open site). ToDos for every submission. Number Cards: Citizen Plantings To Review, Citizen Reports To Review.
* **Needs setup:** an outgoing Email Account on the site (for the verification code); the HR Citizen role is created on migrate.

## Admin: area search, map and filters
* Console map filter bar: search area/road (e.g. "Electronic City"), zone, sites/reports, issue type, status. The summary line lists the zones the matches fall in. Report pins are coloured by priority; popups have Open / Assign volunteer / Plan a visit. Citizen submissions are filtered the same way.
* HR Site, HR Tree, HR Tree Report have `latitude` / `longitude` (copied from GPS), so Frappe's own **Map** view works: `/app/hr-tree-report/view/map`, `/app/hr-site/view/map`.
* Standard filters: HR Tree Report (zone, site, area, issue type, status, priority, submitted via, admin reviewed), HR Site (area, road, zone, status).
* Citizen "My status": thank-you note, tree messages, report progress bar (Received, Seen, Volunteer, In progress, Resolved).

## Frappe-native citizen side (replaces the custom `/citizen` page)
Citizens use Frappe Web Forms and website pages. Each submission is first saved as a record the admin can filter and map (HR Citizen Planting, HR Citizen Report, HR Volunteer Request), then processed into the real site / tree / report / volunteer application by `citizen_forms.py`. Status flows back to the citizen automatically. The earlier custom page (`templates/citizen.html`, route `/citizen`) is still in the repo and can be deleted. See `docs/FRAPPE_SETUP.md`.

## CHANGELOG
### 21 Nov 2026: places hierarchy, care log, spreadsheet import (#5 and related)
* Lists (dropdown or type a new name): **HR Area** (zone, part of), **HR Road**, **HR Landmark**,
  **HR Route** (watering route = just a name for a group of spots), **HR Species** (Kannada and botanical
  name, photo, about, care notes). Typed names that are new are added as *Unverified*; names matching an
  existing name or one of its "Other spellings" are filed under it. Join duplicates with
  Rename -> "Merge with existing" (updates every linked record).
* HR Site: area/road/landmark/route are links; Door no/Cross/Main + pin code (typed) and "Address from GPS"
  (automatic); companion plants (noted, not counted); GPS status. Zone comes from the area when empty.
* HR Tree: species link, planting type (New / Replacement / Rescued / Existing), replaces tree, GPS status,
  last watered / last maintenance.
* **HR Care Log**: per tree per activity (watering, guard installed/removed, pruning, ...), volunteer, hours,
  notes, photo. Volunteers log for their assigned trees at **/my-trees** and add GPS for imported trees.
* Public map: "Watered X days ago", species details, landmark, companion plants.
* **Import watering sheet** (Desk: Watering Routes list): each row -> spot/stretch + trees (GPS pending),
  planting type from the text, "along with ..." -> companion plants, date columns -> past waterings.
  Preview first; rows already imported are skipped.
* Fix: volunteer app home was blank (script-order error with hrOpenTreeReport).
* Workspace: "Places & care" section. Admin to-do after deploy: check the Unverified Areas / Roads /
  Landmarks / Species, merge spelling variants, set zones on new areas.

### 22 Nov 2026: Duplicate Reports, Deleted Sites, re-plant
* New DocType **HR Duplicate Report** (in code). `HR Site.after_insert` creates one Pending Review report for every flagged site, with the existing site, distance, nearest tree, zone/road/area, map point and both photos. The old UI Server Script is not needed (it never fired: `validate` had already set `possible_duplicate_of`).
* Admin decisions on the report: Different site - keep it / Same place - merge / Delete duplicate / Re-plant. Each closes the report (Kept as New, Merged, Deleted, Restored).
* Every deleted site, by any route (button or Desk Delete), is copied to **HR Deleted Site**. `hr_deleted_site.restore_site` re-plants it with the same id, place and photo, and can move the trees back.
* `HR Site.photo_url` is now an Attach Image field. Number cards Open Duplicate Reports and Deleted Sites added. Patch `create_duplicate_reports` backfills reports for sites already in Needs Review and adds the cards and shortcuts under the workspace heading "Duplicate detection & review".
### 20 Nov 2026 (later): citizen and volunteer sign-in rebuilt
* Public map `/trees` (no sign-in): spots in view load as the map moves; a spot shows photo, tree type, date
  planted, age and whether it has a caretaker. No volunteer names/phones/emails. `/trees?spot=<id>` opens one spot.
* Citizen sign-in `/citizen-login`: mobile + email + 6-digit code by email; "keep me signed in" (HR Device Login).
* Requests `/request` (HR Request DocType): *New location* or *Maintenance*. GPS with accuracy shown, or a pin;
  address (Door/Cross/Main, road, area, pin code, zone) filled from the map and editable; spots/trees within 60 m
  shown with photos to avoid duplicates; photo shrunk on the phone before upload. Possible duplicates go to
  *Under review*. GPS cannot be edited. Citizen emailed on status change. `/my-requests` shows progress.
* Volunteers: sign up at `/volunteer-signup` (all details, email code, password; admin approves; citizens can
  upgrade). Sign in at `/hasiruratha` with mobile + password (admins too). `/volunteer-reset` sets or resets
  the password by email code, also for volunteers added by an admin who never had one.
* Retired: mobile-number-only sign-in (`api.login_phone`) and instant self-registration (`api.register_phone`).
* Fixed: `/citizen-home` and `/my-status` returned 500 (controller files must use `_`, not `-`).
* Needs on the live site: an outgoing Email Account (codes and status emails), then deploy + migrate.
* Tests: `tools/e2e/` (phone-size, citizen + volunteer).

### 20 Nov 2026: volunteer form fix + admin workspace in code
* `web_form/become_a_volunteer/become_a_volunteer.py` was missing, so Frappe could not import the form module and the page never opened. Added.
* `become_a_volunteer.js` was a copy of the map script. Replaced with a note; the real logic is the Web Form `client_script` (prefill via `citizen_api.my_profile`, "Send code" button with 60 s cooldown, pin code check).
* `HR Application.tree` was mandatory, so every volunteer application without a chosen tree failed on save. Now optional; still required for *Admin Assignment* (`hr_application.py`).
* Volunteer form now captures name, mobile, email, address, road, area, pin code, zone (dropdown). Saved on `HR Volunteer` (new fields address, road, pincode; zone goes to primary_zone_id).
* Two number cards sat in `hasiruratha/hasiruratha/hasiruratha/number_card` (wrong folder) and never synced. Moved. Added 4 cards.
* Workspace `Hasiru Ratha Admin` is kept on the site, not in code.
* `citizen_api.py`, `templates/citizen.html`, `renderer.py` route `/citizen`; new fields `submitted_via`, `address_full`, `zone_note`, `admin_reviewed` (HR Site / Tree / Tree Report), `email_verified` (HR Application)
* `page/hr_console/*`: the Console page; python endpoints reuse `api.add_visit`, `create_tree_report`, `assign_tree`, `assign_tree_report`
* `hr_site.py`: duplicate detection, approve and merge
* `hr_site.json`: field `possible_duplicate_of`, status `Needs Review`
* `hr_site.js`, `hr_site_list.js`: admin review buttons, status colours
* `api.py`: actions `getNearbySites`, `approveSite`, `mergeSite`; `addSite` returns `needs_review`
* `number_card/*`: three admin cards
* `templates/app.html`: nearby-spots panel; wording: "Save plantation to Tree Registry" -> "Save my planted tree", "Report condition" -> "How is this tree doing?", "Submit report" -> "Send update" / "Send to the Hasiru Ratha team", "Report a Tree" -> "Help a tree", "Report a tree issue" -> "Tell us what this tree needs"

## Open items
* test on the cloud site: create two sites 10 m apart, confirm Needs Review, ToDo, approve, merge
* decide whether to rebuild the user app with Frappe UI (Vue) later
