# Console + maps upgrade (27 Nov 2026)

## Changed files
| File | What changed |
|---|---|
| `hasiruratha/hasiruratha/page/hr_console/hr_console.js` | New shared **place picker** (search area/road/tree ID, area+road chips, My location, tap map, cards with photo + GPS + badges). New Plant / Report / Visit / Assign dialogs. Map popups show photo + GPS. |
| `hasiruratha/hasiruratha/page/hr_console/hr_console.py` | New endpoints `find_places`, `find_reports`, `check_spot`, `where_is`, `search_map`; `plant_sapling`, `report_tree`, `plan_visit` now refuse requests without a photo and check duplicates. Console payload no longer sends every tree. |
| `hasiruratha/api.py` | `reverse_geocode` falls back to OpenStreetMap when no Google key; new `search_places` (Google if key, else OSM). Google keys are now optional. |
| `hasiruratha/boards.py` | Tree Report cards also show the road. |
| `hasiruratha/hasiruratha/doctype/hasiruratha_settings/hasiruratha_settings.json` | Key fields say they are optional. |
| `hasiruratha/patches/admin_area_road_lists.py` (+ `patches.txt`) | Sites, Tree Reports, Visits: area / road columns and filters in the list views. |
| `tools/test_console_evidence.py` | 17 checks for the new console rules (run in `bench console`). |
| `README.md`, `docs/REQUIREMENTS_STATUS.md` | Updated. |

## Removed from the package
The two old zips inside it, and the `app.html.backup_*` / `app.html.final_backup` files.

## After pushing
`bench --site <site> migrate` (Frappe Cloud: deploy, then migrate) so the console page and the list-view patch load.
