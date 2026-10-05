# Changelog

## [Unreleased]

### Changed
- **ZTP Kraków → zbiorkom.live api6-open** — departures, stop list and vehicle positions now come from `api.zbiorkom.live/api6-open/krakow` (the 4.8 API is being retired, #37). Existing stops keep working: pre-api6 ids (e.g. `bonarka-ska02`) are resolved to api6 ids (`bonarka-ska02-xruaf`) at runtime.
- Stop picker now includes Mobilis / agglomeration stops (e.g. Bonarka SKA) and all tram platforms (fixes Plac Centralny im. R. Reagana 03/04, #17).
- Kraków GPS: vehicles matched by route + brigade (buses) or upcoming stop + scheduled time (trams near the stop); adds `vehicle_code` and `vehicle_model`. Each vehicle is shown only on its next departure. The ZTP GTFS-RT feeds are no longer needed for Kraków.
- `STOP_ID_PATTERN` accepts `+` (api6 ids of P+R stops).

## [1.6.0] — unreleased

### New Providers (+8)
- **MKS Mielec** — GTFS-RT + GPS (19 TU, 19 VP) (`api.zbiorkom.live api6-open`)
- **MZK Oświęcim** — GTFS-RT + GPS (59 TU, 10 VP) (`api.zbiorkom.live api6-open`)
- **MPK Radomsko** — GTFS-RT + GPS (1 TU, 1 VP) (`api.zbiorkom.live api6-open`)
- **ZDMiKP Bydgoszcz** — static GTFS, 1194 stops (`mkuran.pl`)
- **MKS Dębica** — static GTFS (`api.zbiorkom.live api6-open`)
- **KM Kołobrzeg** — static GTFS (`api.zbiorkom.live api6-open`)
- **SPGK Sanok** — static GTFS (`api.zbiorkom.live api6-open`)
- **MZK Ostrołęka** — static GTFS (`api.zbiorkom.live api6-open`)

### Card UX Improvements
- **Per-entity `max_departures`** — override global cap per sensor in the card editor
- **Platform/peron display** — compact chip showing platform/stand number when available
- **Multi-vehicle live map** — all GPS-tracked vehicles from a stop shown simultaneously; clicked vehicle highlighted
- **Stop location marker** — colored circle marking the stop position on the live map
- **Editor live preview** — real-time mini card preview in the Lovelace editor
- **Map refresh indicator** — subtle "🔄 co 30s" status showing map auto-update interval

### Security
- **SSL enabled by default** — `ssl=False` removed from all GTFSRT provider requests and config_flow; only Wrocław (`mapadlugoleka.klosok.eu`) requires opt-out

### Internationalization (i18n)
- Full English + Polish translations for all 5 config flow steps (`user`, `stop`, `api_key`, `lodz_mode`, `lodz_group`)
- Error and abort messages translated in both languages

### Maintenance
- Removed `from __future__ import annotations` from 4 files (Python 3.12+ no-op)
- Updated `hacs.json` minimum Home Assistant version to 2025.1.0

---

## [1.5.0] — 2026-07-28

### New Providers (+11)
- **MZK Kalisz** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Konin** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Koszalin** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MKS Krosno** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Piła** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **KM Płock** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK Siedlce** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Starachowice** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK Tarnów** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **ZKM Wałbrzych** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **KA Świnoujście** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)

### New Providers (+3)
- **MZK Toruń** — GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK Wrocław** — GTFS + live GPS (`mapadlugoleka.klosok.eu`)
- **MZK Ełk** — GTFS-RT + GPS (`mkuran.pl`)

### Łódź — Major Rework
- **Switched to official GTFS-RT** from `otwarte.miasto.lodz.pl` (replaces custom XML provider)
- GTFS-RT feed with 100% trip_id overlap
- 257 vehicle positions with GPS and route_id
- Removed blocking I/O (file operations moved to executor threads)
- **120 bus stop groups** ("węzły przesiadkowe") from `rozklady.lodz.pl/GetMapBusStopGroupList` API
- Groups expand to multi-stop aggregated sensors (`MzkzgAggregatedSensor`)

### GPS — Live Vehicle Map
- **All 35 GTFS-RT cities now have GPS**, including previously non-working cities
- **GPS enrichment without vehicle_code** — positions fetched and matched via `trip_id` / `route_id` fallback when TripUpdates are unavailable
- **Warszawa**: trip_id matching from `positions.json` (6 GPS per sensor)
- **Wrocław**: route_id matching from `vehicle_positions.pb` mapadlugoleka
- **Kraków**: route_id matching from ZTP GTFS-RT for **bus stops** (tram stops: RT only, vehicle ID mismatch)
- **Poznań**: route-only matching when GTFS and RT trip_ids differ
- **Route-level RT fallback** — `delays[f"route_{route_id}"]` for cities with mismatched GTFS/RT trip_ids
- Minimal SVG vehicle markers (circle + arrow, no popup, no pulse)

### GTFS-RT — Data Source Fixes
- **6 api6-open cities fixed**: Białystok, Częstochowa, Olsztyn, Opole, Rzeszów, Toruń switched from incompatible CDN GTFS to `api.zbiorkom.live/api6-open/{city}/gtfs/default` — enabled **realtime delays + GPS** (previously 0% overlap)
- **GTFS calendar resilience** — when no weekday services match (`any_weekday_match=False`), fall back to showing all scheduled departures (fixes Poznań showing 0 departures when GTFS calendar covers future dates)

### Bug Fixes
- `HasField("bearing")` / `HasField("speed")` protobuf compatibility — fixed crash on newer protobuf versions by using `vehicle.position.HasField()` (not `vehicle.HasField()`)
- **Speed normalization** — `vehicle_speed` always reported in km/h across all providers (protobuf m/s → ×3.6 in `provider_lodz`, `provider_krakow`, `provider_gtfsrt`)
- **Double `f.read()`** in Łódź provider metadata parsing — file content consumed twice, condition always False
- **Orphaned `except` + dead code** in Łódź GTFS cache function
- `mkdir` converted to async (`asyncio.to_thread`) in `gtfs_provider.py`
- **MAX_DEPARTURES=20** cap — prevents recorder size warnings from oversized sensor attributes
- **Resilient setup** — individual stop first-refresh failures don't block sibling stops

### Config Flow
- **Łódź bus stop groups** — new `lodz_mode` / `lodz_group` steps with 120 transfer hubs
- **HH:MM validation** on sleep start/end fields (`vol.Match(r"^\d{1,2}:\d{2}$")`)
- **DRY `PROVIDER_OPTIONS`** — now derived from `PROVIDER_LABELS` (single `PROVIDER_TCZEW` override)
- `PROVIDER_TORUN` + `PROVIDER_WROCLAW` added to config_flow UI (were missing)

### Card (JS)
- Minimal vehicle markers on Leaflet map (circle + route number + arrow, no popup, no pulsation)
- Compact popup styling removed
- Cleaner CSS

### Tests
- **90 tests** (+3 new: route_id position fallback, round-robin distribution, speed normalization)
- Fixed 2 pre-existing Łódź test failures (timing-dependent `th="10"` → future time)
- Full provider consistency verified (53 providers × labels × colors × options × imports)

### Documentation
- Complete README rewrite — 53 operators table, data sources breakdown, feature matrix, architecture diagram
- Example config updated with realistic HA entity IDs
- HACS minimum HA version bumped to 2025.1.0

### Chores
- Renamed to "Polish Public Transport Card" (manifest, HACS, README)
- Cleaned up stale test-results file
- Provider dead code removed (`seen_rt_order` in ZTM)

---

[1.5.0]: https://github.com/toczke/polish-public-transport-card/compare/main...v1.5.0
