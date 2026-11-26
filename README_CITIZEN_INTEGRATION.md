# Hasiru Ratha — Integrated Citizen Map + Plant/Report + Tracking

Base app source: `Hasiruratha-main-workspace-dashboard.zip` (Nov 24, 2026). Citizen map/tracking package: Nov 26, 2026.

## Integrated citizen features
1. GPS, user-entered area/road/landmark search, map click pin, and draggable pin. Selected coordinates save into form Geolocation/latitude/longitude; reverse lookup fills area, road, and address.
2. Shared citizen map shows existing HR Trees and HR Sites. Selecting an existing marker passes its context into Plant/Report.
3. Plant form shows nearby spots, lets the citizen use an existing site, pre-fills URL coordinates/site context, and keeps server-side duplicate/confirm logic.
4. Report form shows nearby trees, allows selecting a specific tree, stores the selected tree in the hidden `tree` field, and server processing prioritizes that selection; nearest-tree fallback remains.
5. Citizen tracking pages `/my-trees` and `/my-reports` and tracker API remain included.

Coordinate detection uses complete pairs in priority order `gps_lat/gps_lng`, `latitude/longitude`, `lat/lng`, then supported GeoJSON Geolocation fields. It does not mix coordinate pairs.

Search uses user-triggered Nominatim queries, not autocomplete. Public map API returns marker-safe fields only.

**This package uses the Nov 24 full app source available in the uploaded Library, not a later source that may exist in your current working repository.** Review the diff against your current app before replacing/pushing.
