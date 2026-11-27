# Requirements status (all 22 points, checked against this zip)

Read from the code only. Nothing has been run on the Frappe Cloud site yet: deploy, migrate, then walk through the list.

| # | Requirement | Status | Where / note |
|---|-------------|--------|--------------|
| 1 | Website in Frappe website builder | Done in code | Web Templates (HR Navbar, Hero, Impact, ...), `/home-new`. Go-live = Website Settings (Home Page, Navbar, Footer) |
| 2 | Application integrated in the website | Done | `/request`, `/trees`, `/events`, `/impact`, `/my-trees`, `/volunteer-signup` |
| 3 | New or maintenance request; place may be unknown or duplicate | Done | HR Request, `/request` |
| 4 | Duplicate prevention with nearby photos; admin can delete | Done | 60 m nearby cards with photos; Duplicate Reports, Deleted Sites, bulk delete |
| 5 | Mobile compliant and tested | Partly | Built mobile first; phone-size tests in `tools/e2e` exist but were not run here |
| 6 | GPS accurate enough | Partly | Accuracy shown, care GPS refused above 50 m, 25 m / 30 m duplicate rules. Real accuracy depends on the phone |
| 7 | Request from location or pin; address auto-resolved and editable; road, area, pin, door/cross/main | Done | `/request` |
| 8 | Spot > Stretch > Road > Area > Zone | Done | HR Site, HR Road, HR Area, HR Zone |
| 9 | Admin edits everything except GPS | Done (this update) | GPS fields lock once captured (HR Site, HR Tree); HR Request GPS already read-only |
| 10 | Public map of all locations | Done | `/trees` |
| 11 | Click shows details, photo, caretaker | Needs a decision | Photo and "a volunteer looks after it" shown; the volunteer's name is hidden (point 15 says no volunteer details). Show first name? |
| 12 | Email and phone of the citizen, no volunteer registration needed | Done | Both come from the citizen sign-in and are stored on the request |
| 13 | Register-as-volunteer link, all fields mandatory, zone dropdown, pin code | Done | `/volunteer-signup` |
| 14 | Volunteer adopts a sapling in their neighbourhood; admin can assign | Done (this update) | "Adopt this tree" on the map for approved volunteers (same area or zone); admin assigns in Desk |
| 15 | Soft login sees all saplings, no volunteer details | Done | `/citizen-login`, public API hides volunteer data |
| 16 | Subscribe to an upcoming event | Done (this update) | HR Event, HR Event Subscription, `/events`, confirmation email |
| 17 | Volunteer sees adopted saplings | Done | `/my-trees` |
| 18 | Map of planted / reported around GPS or chosen area (~1 sq km); moving the pin changes the set | Done | `/trees` loads spots for the visible map; GPS zoom is about 1 km |
| 19 | Dashboard: saplings, requests completed, volunteer hours, guards installed / removed, clickable | Done (this update) | `/impact` page and 6 workspace Number Cards |
| 20 | QR code per location | Done (this update) | HR Site form -> QR label; list -> Actions -> Print QR labels (`/spot-qr`) |
| 21 | Duplicate Report doctype: every duplicate with the site it is near and photo; admin deletes into Deleted Sites; admin can re-plant | Done | HR Duplicate Report, HR Deleted Site; decide on the form, Kanban card, Console or list |
| 22 | Everything in Kanban | Done | Board for every status-based doctype (13) in Desk and in the Console Boards panel |

Done 18, partly 2 (5, 6), needs a decision 1 (11), plus 21 and 22 as asked.

Needs on the live site: an outgoing Email Account (codes, confirmations), a run of `tools/e2e` and `tools/test_console_evidence.py`. Google keys are optional: without them the app uses OpenStreetMap for maps, address lookup and place search.
