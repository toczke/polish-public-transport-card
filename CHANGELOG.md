# Changelog

## [1.7.0] - unreleased

### Added
- **Card presets** - added `native` (Home Assistant look) next to `standard`,
  `compact`, `minimal` and `e_ink`; optional header clock and
  `time_format: auto|24h|12h`; `header_style: provider|theme|custom`
- **Display modes** - added the `minimal` preset next to `standard`, `compact` and
  `e_ink`, plus row-level switches for countdown, vehicle number, platform/stand,
  accessibility icons, stop name, footer and last-update time
- **Filters** - `exclude_routes`, `filter_vehicle_types`, `filter_providers` and
  `hide_cancelled`, alongside the existing route/destination/platform/track filters;
  added `max_minutes`, `only_low_floor`, `only_bike`, `only_ac` and
  `only_ticket_machine`
- **Views and layout** - `view_mode: grouped` groups rows by line, `columns: 1|2|3`
  renders a multi-column board, the optional header refresh button re-queries sensors,
  and provider subtitles use friendly operator names
- **Interactions** - tap / hold / double-tap actions are now editable in the GUI with
  Home Assistant's native action picker, including navigation, URL and service calls
- **Live map** - vehicle markers show hover tooltips and detail popups, overlapping
  markers are spread apart, the selected vehicle opens its popup automatically, and
  the map follows a dark HA theme
- **Per-sensor editor** - stop-name labels, override reset, row reordering and
  validation for departure limits and header colour
- **Per-sensor editor** - the GUI editor now has a second form for per-sensor overrides
  (routes, destinations, vehicle type, provider, platform/track, max rows, realtime,
  highlight mode)
- **Map discoverability** - rows with a live vehicle position open the map when clicked; the extra row pin icon was removed to keep rows compact
- **YAML documentation** - README options table and example config updated with all
  global/per-sensor keys and theme examples

### Fixed
- **Duplicate departures** - schedule and realtime rows for the same route and time
  are now merged when one headsign is a prefix of the other (for example
  `Brzeźno` and `Brzeźno Dom Zdrojowy`); the more specific terminus and the richer
  vehicle/trip fields are kept
- **Vehicle marker** - replaced the old clipped arrow shape with a circular puck
  centred on the vehicle and a small direction pointer; the selected vehicle stays
  centred at zoom 16. The map now has one compact detail popup opened by clicking a
  marker (no auto-opened giant bubble and no tiny hover tooltip), without emoji
- **Live vehicle marker** - removed the black vehicle-code badge that overlapped the
  route circle. Markers now show only the route number and direction arrow, with a
  white ring around the selected vehicle. The map also always waits for Leaflet CSS,
  so tiles no longer render as a checkerboard.

## [1.6.7-hotfix2] - 2026-11-06

### Fixed
- **Checkerboard map tiles / missing vehicle marker** - Home Assistant may already
  expose the global `L` object without its Leaflet stylesheet. The card now always
  injects and waits for `leaflet.css` before creating the map, so tiles are positioned
  absolutely and vehicle markers render correctly.

## [1.6.7-hotfix] - 2026-11-06

### Fixed
- **Live vehicle map** - the map overlay no longer throws a temporal-dead-zone
  `ReferenceError` before `ctx` is initialized; clicking a row with GPS now opens the
  map and the close button, backdrop and Escape key all work again.

## [1.6.7] - 2026-11-06

### Added
- **Beta 1.6.x features** - PLK delay binary sensor, native route colors, `refresh_gtfs`
  service, walking distance/time attributes, English card editor, advanced OptionsFlow
  filters and parallel GTFS downloads
- **Bielsko-Biała** provider, **Bytów** on Time4BUS, `timetable` attribute for
  kiedyPrzyjedzie full-day schedules
- **Card** `exclude_destinations`, `min_departures`, per-sensor overrides and
  OpenStreetMap/HA `map_tiles` basemap support


### Changed
- **ZTP KrakĂłw â†’ zbiorkom.live api6-open** â€” departures, stops and vehicle positions from `api.zbiorkom.live/api6-open/krakow` (4.8 API is being retired, #37). Existing stops switch to api6 ids automatically; entity ids and history are kept
- **KrakĂłw stop picker** â€” adds Mobilis / agglomeration stops and all tram platforms (fixes Plac Centralny im. R. Reagana 03/04, #17)
- **KrakĂłw GPS** â€” vehicles matched by brigade (buses) or next stops (within ~3 stops); adds `vehicle_model`; covers edge stops (KamieĹ„, Rusocice). `vehicle_code` now only for GPS-matched vehicles, so distant trams show none
- `STOP_ID_PATTERN` accepts `+` (P+R stops)

### Fixed
- **KrakĂłw outages** â€” departures keep updating when the stop list or vehicle positions are down
- **KrakĂłw DST** â€” correct order and times in the October fall-back hour
- **Vehicle map tiles** â€” OpenStreetMap instead of CARTO, whose basemaps now need an API key (#35). On Home Assistant 2026.9+ tiles come through HA's own tile proxy, so OpenStreetMap never sees your instance's address; older versions load them directly and send your Home Assistant's origin (e.g. `https://xyz.ui.nabu.casa`) as the Referer, which OpenStreetMap requires from browsers. Attribution links open in a new tab
- **PLK API usage sensor** — created once per Home Assistant instead of once per PLK
  entry, so several stations no longer log "does not generate unique IDs" on startup (#41)
- **Deprecated `via_device`** — stop devices are linked to their operator device through
  `via_device_id` after registration; entity re-adds on HA 2026.9+ no longer raise
  `RuntimeError` (#27, #44)
- **Recorder attribute warnings** — `departures`, `last_update` and `timetable` are marked
  as unrecorded attributes, so large stop attributes no longer trigger the 16 KiB recorder
  warning (#39)
- **Departures from all service days** — feeds that only ship `calendar_dates.txt`
  (Elbląg, Kielce and other api6 exports) are now filtered to the services running today
  (#32, #33)
- **Retired zbiorkom CDN feeds** — Lublin, Kielce, Radom, Elbląg, Gorzów, Suwałki,
  Przemyśl, Rybnik, Kutno, Legnica, Leszno and Wrocław now use `api6-open` static and
  realtime endpoints. Wrocław schedules work again (#36, #44, #46)
- **Bytów** — moved from kiedyPrzyjedzie to Time4BUS; existing provider ids keep working (#38)
- **Bielsko-Biała** — new MZK Bielsko-Biała provider (#16)
- **Bydgoszcz** — already supported since 1.6.0; added to the supported-operators table (#26)
- **Offline GTFS fallback** — the last downloaded schedule is stored under
  `.storage/mzkzg_transport/gtfs/` and served when the upstream feed is unreachable (#18)
- **Full timetable attribute** — kiedyPrzyjedzie entries can list timetable lines and expose
  today/tomorrow departures in the `timetable` sensor attribute (#28)
- **Card destination exclusions and minimum rows** — new `exclude_destinations` and
  `min_departures` options, per-sensor overrides, and the cap raised to 100 so PLK can show a
  whole day (#22, #24)
- **Card lifecycle** — Leaflet assets are shared across cards, the refresh timer only runs
  while connected, and an open map is disposed with the card (#21)
- **GTFS concurrency lock** — several stops of one provider now load the archive once instead
  of racing to parse it in parallel (#20, #21)
- **GTFS-RT log spam** — malformed/retired realtime feeds are logged at debug level instead
  of warning on every poll (#44)
- **PLK 429 backoff** — after a rate-limit response the integration stops polling PLK for
  15 minutes and serves the last schedule/operations snapshot instead of retrying every cycle
- **TLS verification** — removed the remaining `ssl=False` overrides from the Gdańsk and
  Łódź providers; certificate verification is now enabled for all integrations
- **Config-flow translations** — fixed the English `stop` title placeholder and added the
  timetable-lines option label, removing the translation placeholder error on startup
- **PLK station labels** — rail stations now end with `PKP` (e.g. `Zabierzów PKP`), so a
  rail search doesn't pick a nearby bus stop from another provider (#40)
- **GTFS parsing off the event loop** — Gdańsk and Łódź archives are parsed in the executor
  as well, not just GTFS-RT providers (#20, #21)

## [1.6.0] - 2026-07-29

### New Providers (+8)
- **MKS Mielec** â€” GTFS-RT + GPS (19 TU, 19 VP) (`api.zbiorkom.live api6-open`)
- **MZK OĹ›wiÄ™cim** â€” GTFS-RT + GPS (59 TU, 10 VP) (`api.zbiorkom.live api6-open`)
- **MPK Radomsko** â€” GTFS-RT + GPS (1 TU, 1 VP) (`api.zbiorkom.live api6-open`)
- **ZDMiKP Bydgoszcz** â€” static GTFS, 1194 stops (`mkuran.pl`)
- **MKS DÄ™bica** â€” static GTFS (`api.zbiorkom.live api6-open`)
- **KM KoĹ‚obrzeg** â€” static GTFS (`api.zbiorkom.live api6-open`)
- **SPGK Sanok** â€” static GTFS (`api.zbiorkom.live api6-open`)
- **MZK OstroĹ‚Ä™ka** â€” static GTFS (`api.zbiorkom.live api6-open`)

### Card UX Improvements
- **Per-entity `max_departures`** â€” override global cap per sensor in the card editor
- **Platform/peron display** â€” compact chip showing platform/stand number when available
- **Multi-vehicle live map** â€” all GPS-tracked vehicles from a stop shown simultaneously; clicked vehicle highlighted
- **Stop location marker** â€” colored circle marking the stop position on the live map
- **Editor live preview** â€” real-time mini card preview in the Lovelace editor
- **Map refresh indicator** â€” subtle "đź”„ co 30s" status showing map auto-update interval

### Security
- **SSL enabled by default** â€” `ssl=False` removed from all GTFSRT provider requests and config_flow; only WrocĹ‚aw (`mapadlugoleka.klosok.eu`) requires opt-out

### Internationalization (i18n)
- Full English + Polish translations for all 5 config flow steps (`user`, `stop`, `api_key`, `lodz_mode`, `lodz_group`)
- Error and abort messages translated in both languages

### Maintenance
- Removed `from __future__ import annotations` from 4 files (Python 3.12+ no-op)
- Updated `hacs.json` minimum Home Assistant version to 2025.1.0

### Fixed
- **Card never rendered and took down the whole dashboard section** â€” three references to undefined variables in `polish-transport-card.js`:
  - `_getDepartures()` used `d` outside the filter callback when computing the departure cap (`ReferenceError: d is not defined`)
  - `_getDepartures()` referenced `showProviderHeaders` and `providerLabel`, neither of which was declared in that scope; the resulting throw was swallowed by a `try/catch`, so every departure row silently rendered empty
  - `_getAllDepartures()` read `c.group_by_provider` without declaring `c`
  - Removed the dead provider-header rows (`_header` / `_headerLabel` / `_provider_label` were never consumed by the renderer)
- **Vehicle map opened as an unclosable blank overlay** â€” `_showVehicleMap()` used a `ctx` object that was never declared. The throw happened right after the overlay was appended to the document, so the close button, backdrop click and Leaflet initialisation were never wired up. `ctx` now owns the map handle, markers, refresh interval and resize observer, and its `destroy()` tears all of them down. <kbd>Esc</kbd> also closes the map, and an open map is disposed in `disconnectedCallback()` so a removed card cannot leak a 30 s interval.
- **Card resource could disappear from Lovelace after a restart** â€” `_register_card()` deleted every existing resource entry before creating the new one, so any failure in between left the dashboard with no card resource at all (`Custom element doesn't exist: polish-transport-card`). The current entry is now created first and only stale entries are removed. Lovelace YAML mode and a missing resource collection now log the URL to add manually instead of failing silently.
- **Out-of-memory crashes that kill Home Assistant Core on large GTFS feeds (ZTM Warszawa)** ([#20](https://github.com/toczke/polish-public-transport-card/issues/20))
  - `stop_times.txt` is now streamed row by row from the zip instead of being decoded into one string plus a full list of rows â€” Warsaw's feed has millions of rows and previously allocated several GB
  - `_get_tomorrow_departures()` no longer materialises the whole `stop_times.txt`, and its result is memoised so the nightly "no departures left today" path stops rescanning the feed on every refresh
  - GTFS zip parsing moved off the event loop (`async_add_executor_job`)
  - Config flow stop loading streams `stops.txt` and releases the downloaded zip afterwards

---

## [1.5.0] â€” 2026-07-28

### New Providers (+11)
- **MZK Kalisz** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Konin** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Koszalin** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MKS Krosno** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK PiĹ‚a** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **KM PĹ‚ock** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK Siedlce** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MZK Starachowice** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK TarnĂłw** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **ZKM WaĹ‚brzych** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **KA ĹšwinoujĹ›cie** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)

### New Providers (+3)
- **MZK ToruĹ„** â€” GTFS-RT + GPS (`api.zbiorkom.live api6-open`)
- **MPK WrocĹ‚aw** â€” GTFS + live GPS (`mapadlugoleka.klosok.eu`)
- **MZK EĹ‚k** â€” GTFS-RT + GPS (`mkuran.pl`)

### ĹĂłdĹş â€” Major Rework
- **Switched to official GTFS-RT** from `otwarte.miasto.lodz.pl` (replaces custom XML provider)
- GTFS-RT feed with 100% trip_id overlap
- 257 vehicle positions with GPS and route_id
- Removed blocking I/O (file operations moved to executor threads)
- **120 bus stop groups** ("wÄ™zĹ‚y przesiadkowe") from `rozklady.lodz.pl/GetMapBusStopGroupList` API
- Groups expand to multi-stop aggregated sensors (`MzkzgAggregatedSensor`)

### GPS â€” Live Vehicle Map
- **All 35 GTFS-RT cities now have GPS**, including previously non-working cities
- **GPS enrichment without vehicle_code** â€” positions fetched and matched via `trip_id` / `route_id` fallback when TripUpdates are unavailable
- **Warszawa**: trip_id matching from `positions.json` (6 GPS per sensor)
- **WrocĹ‚aw**: route_id matching from `vehicle_positions.pb` mapadlugoleka
- **KrakĂłw**: route_id matching from ZTP GTFS-RT for **bus stops** (tram stops: RT only, vehicle ID mismatch)
- **PoznaĹ„**: route-only matching when GTFS and RT trip_ids differ
- **Route-level RT fallback** â€” `delays[f"route_{route_id}"]` for cities with mismatched GTFS/RT trip_ids
- Minimal SVG vehicle markers (circle + arrow, no popup, no pulse)

### GTFS-RT â€” Data Source Fixes
- **6 api6-open cities fixed**: BiaĹ‚ystok, CzÄ™stochowa, Olsztyn, Opole, RzeszĂłw, ToruĹ„ switched from incompatible CDN GTFS to `api.zbiorkom.live/api6-open/{city}/gtfs/default` â€” enabled **realtime delays + GPS** (previously 0% overlap)
- **GTFS calendar resilience** â€” when no weekday services match (`any_weekday_match=False`), fall back to showing all scheduled departures (fixes PoznaĹ„ showing 0 departures when GTFS calendar covers future dates)

### Bug Fixes
- `HasField("bearing")` / `HasField("speed")` protobuf compatibility â€” fixed crash on newer protobuf versions by using `vehicle.position.HasField()` (not `vehicle.HasField()`)
- **Speed normalization** â€” `vehicle_speed` always reported in km/h across all providers (protobuf m/s â†’ Ă—3.6 in `provider_lodz`, `provider_krakow`, `provider_gtfsrt`)
- **Double `f.read()`** in ĹĂłdĹş provider metadata parsing â€” file content consumed twice, condition always False
- **Orphaned `except` + dead code** in ĹĂłdĹş GTFS cache function
- `mkdir` converted to async (`asyncio.to_thread`) in `gtfs_provider.py`
- **MAX_DEPARTURES=20** cap â€” prevents recorder size warnings from oversized sensor attributes
- **Resilient setup** â€” individual stop first-refresh failures don't block sibling stops

### Config Flow
- **ĹĂłdĹş bus stop groups** â€” new `lodz_mode` / `lodz_group` steps with 120 transfer hubs
- **HH:MM validation** on sleep start/end fields (`vol.Match(r"^\d{1,2}:\d{2}$")`)
- **DRY `PROVIDER_OPTIONS`** â€” now derived from `PROVIDER_LABELS` (single `PROVIDER_TCZEW` override)
- `PROVIDER_TORUN` + `PROVIDER_WROCLAW` added to config_flow UI (were missing)

### Card (JS)
- Minimal vehicle markers on Leaflet map (circle + route number + arrow, no popup, no pulsation)
- Compact popup styling removed
- Cleaner CSS

### Tests
- **90 tests** (+3 new: route_id position fallback, round-robin distribution, speed normalization)
- Fixed 2 pre-existing ĹĂłdĹş test failures (timing-dependent `th="10"` â†’ future time)
- Full provider consistency verified (53 providers Ă— labels Ă— colors Ă— options Ă— imports)

### Documentation
- Complete README rewrite â€” 53 operators table, data sources breakdown, feature matrix, architecture diagram
- Example config updated with realistic HA entity IDs
- HACS minimum HA version bumped to 2025.1.0

### Chores
- Renamed to "Polish Public Transport Card" (manifest, HACS, README)
- Cleaned up stale test-results file
- Provider dead code removed (`seen_rt_order` in ZTM)

---

[1.5.0]: https://github.com/toczke/polish-public-transport-card/compare/main...v1.5.0
