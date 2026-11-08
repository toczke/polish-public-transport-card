# Polish Public Transport Card

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/toczke/polish-public-transport-card/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-success.svg)]()

Home Assistant integration + Lovelace card for real-time public transport departures across Poland — **60 operators, 44 GTFS-RT cities with live GPS vehicle map**.

![Standard light](docs/screenshots/standard-light.png)

---

## Scope and disclaimer

This project was built primarily for **Gdańsk** (ZTM Gdańsk), with the PKP PLK rail feed used in the author's own Home Assistant setup. Other providers are included on a **best-effort** basis because their public feeds are available, but they are not all verified to the same level.

- Data comes from third-party GTFS, GTFS-RT and operator APIs. It may be incomplete, delayed, stale or unavailable.
- Stop IDs, schedules, vehicle positions and delay calculations can change without notice when an operator updates its feed.
- No warranty is given for correctness, completeness or availability of data for any provider.
- This project is not affiliated with any transport operator.

If something is wrong for your city or provider, please **open an issue** with the provider name, stop ID/entity ID, the time of the problem and — if possible — a sample of the raw API/GTFS response:

**https://github.com/toczke/polish-public-transport-card/issues**

> **PL:** Projekt był tworzony przede wszystkim pod Gdańsk. Nie odpowiadam za poprawność danych innych providerów — jeśli coś jest nie tak, załóż issue na GitHubie.

---

## Features

### Core

- **60 transport operators** across Poland — municipal, regional, and rail
- **Real-time departures** with delay indicators, live countdown, and animated status dots
- **Live GPS vehicle map** — click any positioned departure to open a Leaflet map tracking the vehicle in real time (updates every 30 s)
- **Multi-provider views** — merged timeline or per-stop tabs, filter by route, destination, platform, or track
- **Five display presets** — `native`, `standard`, `compact`, `minimal` and `e_ink` — optimized for different dashboards and e-paper displays

### Data Quality

| Feature | | | Description |
|---|---|---|---|
| Realtime delays | ✅ | GTFS-RT TripUpdates across the supported GTFS-RT cities; route-level fallback matching |
| GPS positions | ✅ | VehiclePosition protobuf, JSON, and custom API parsing; `trip_id`/`route_id`/`vehicle_code` multi-strategy matching |
| Speed (km/h) | ✅ | Normalized across all providers — protobuf m/s → km/h conversion |
| Schedule fallback | ✅ | Static GTFS departures supplement real-time when coverage is limited |
| Next-day schedule | ✅ | Tomorrow's timetable when no departures remain today |
| Sleep mode | ✅ | Configurable per-operator night-time polling pause (default 00:00–04:30) |

### UX

- **Visual editor** — no YAML required; fully configurable via Lovelace card editor
- **Row actions** — `tap`, `hold`, and `double_tap` actions per departure row
- **Accessibility** — keyboard focus, ARIA labels, reduced-motion support
- **PLK rate limiting** — dynamic request throttling with API usage sensor

---

## Supported Operators

| Operator | Area | Source | RT | Map | Extra |
|---|---|---|---:|---:|---|
| [ZTM Gdańsk](https://ztm.gda.pl) | Gdańsk (bus, tram) | TRISTAR CKAN | ✅ | 🗺️ | bike, wheelchair, AC, USB |
| [ZKM Gdynia](https://zkmgdynia.pl) | Gdynia (bus, trolley) | ZDiZ API | ✅ | ❌ | side number |
| [MZK Wejherowo](https://mzkwejherowo.pl) | Wejherowo (bus) | Static GTFS | ❌ | ❌ | — |
| [Time4BUS Tczew](https://time4bus.com) | Tczew (bus) | Time4BUS | ✅ | ❌ | wheelchair, AC |
| [PKS Gdańsk](https://pksgdansk.pl) | Pomorskie (regional) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [Albatros](https://albatros.kiedyprzyjedzie.pl) | Pomorskie (regional) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [GRYF](https://gryf.kiedyprzyjedzie.pl) | Pomorskie (regional) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [Nord Express](https://nordexpress.kiedyprzyjedzie.pl) | Słupsk region | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [PKS Gdynia](https://pksgdynia.pl) | Gdynia region | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [MZK Malbork](https://malbork.kiedyprzyjedzie.pl) | Malbork (city) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [PKS Słupsk](https://pksslupsk.pl) | Słupsk region | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [MZK Starogard Gd.](https://starogard.kiedyprzyjedzie.pl) | Starogard (city) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [PKS Starogard Gd.](https://pksstarogard.kiedyprzyjedzie.pl) | Starogard region | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [Komunikacja Bytów](https://time4bus.com) | Bytów (city) | Time4BUS | ✅ | ❌ | wheelchair, AC |
| [MZK Bielsko-Biała](https://bielsko.kiedyprzyjedzie.pl) | Bielsko-Biała (city) | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [Powiat Człuchowski](https://czluchow.kiedyprzyjedzie.pl) | Człuchów region | kiedyPrzyjedzie | ✅ | ❌ | bike, wheelchair, AC |
| [PKP / SKM / PolRegio / IC](https://portalpasazera.pl) | Railway stations | PLK API | ✅ | ❌ | platform, track, carrier |
| [MPK Łódź](https://mpk.lodz.pl) | Łódź (bus, tram) | GTFS-RT (official) | ✅ | 🗺️ | 120 bus stop groups |
| [ZTM Poznań](https://ztm.poznan.pl) | Poznań (bus, tram) | GTFS-RT (ZTM) | ✅ | 🗺️ | ramp, AC, bike, USB |
| [ZTM GZM](https://metropoliagzm.pl) | Metropolia GZM (bus, tram) | GTFS-RT (CKAN) | ✅ | 🗺️ | low floor |
| [ZTP Kraków](https://ztp.krakow.pl) | Kraków (bus, tram) | zbiorkom.live API | ✅ | 🗺️¹ | vehicle code, delay |
| [ZTM Lublin](https://ztm.lublin.eu) | Lublin (bus, trolley) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MPK Kielce](https://mpk.kielce.pl) | Kielce (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MPK Częstochowa](https://mpk.czest.pl) | Częstochowa (bus, tram) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [ZKM Elbląg](https://zkm.elblag.com.pl) | Elbląg (bus, tram) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MZK Gorzów Wlkp.](https://mzk-gorzow.com.pl) | Gorzów (bus, tram) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [ZTZ Rybnik](https://ztz.rybnik.pl) | Rybnik (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MZDiK Radom](https://mzdik.radom.pl) | Radom (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [PGK Suwałki](https://pgk.suwalki.pl) | Suwałki (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MZK Przemyśl](https://mzk.przemysl.pl) | Przemyśl (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MZK Kutno](https://mzkkutno.pl) | Kutno (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [MPK Legnica](https://mpk.legnica.pl) | Legnica (bus) | GTFS-RT (CDN) | ✅ | 🗺️ | side number |
| [ZDiTM Szczecin](https://zditm.szczecin.pl) | Szczecin (bus, tram) | GTFS-RT (ZDiTM) | ✅ | 🗺️ | side number |
| [ZTM Warszawa](https://ztm.waw.pl) | Warszawa (bus, tram, metro) | GTFS-RT (mkuran.pl) | ✅ | 🗺️ | side number |
| [MZK Ełk](https://mzk.elk.pl) | Ełk (bus) | GTFS-RT (mkuran.pl) | ✅ | 🗺️ | side number |
| [WKD](https://wkd.com.pl) | Warszawa–Grodzisk (rail) | GTFS-RT (mkuran.pl) | ✅ | 🗺️ | — |
| [BKM Białystok](https://bkm.bialystok.pl) | Białystok (bus) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [ZDZiT Olsztyn](https://zdzit.olsztyn.eu) | Olsztyn (bus, tram) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [MZK Opole](https://mzkopole.pl) | Opole (bus) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [ZTM Rzeszów](https://ztm.rzeszow.pl) | Rzeszów (bus) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [MZK Toruń](https://mzk.torun.pl) | Toruń (bus, tram) | GTFS-RT (api6) | ✅ | 🗺️ | side number |
| [MPK Wrocław](https://mpk.wroc.pl) | Wrocław (bus, tram) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Kalisz](https://mzk.kalisz.pl) | Kalisz (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Konin](https://mzk-konin.pl) | Konin (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Koszalin](https://mzk.koszalin.pl) | Koszalin (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MKS Krosno](https://mks.krosno.pl) | Krosno (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Piła](https://mzk.pila.pl) | Piła (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [KM Płock](https://kmplock.eu) | Płock (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MPK Siedlce](https://mpk.siedlce.pl) | Siedlce (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Starachowice](https://mzk.starachowice.pl) | Starachowice (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MPK Tarnów](https://mpk.tarnow.pl) | Tarnów (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [ZKM Wałbrzych](https://zkm.walbrzych.pl) | Wałbrzych (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [KA Świnoujście](https://ka.swinoujscie.pl) | Świnoujście (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Leszno](https://mzk.leszno.pl) | Leszno (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [ZDMiKP Bydgoszcz](https://zdmikp.bydgoszcz.pl) | Bydgoszcz (bus, tram) | Static GTFS | ❌ | ❌ | — |
| [MKS Mielec](https://mks.mielec.pl) | Mielec (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MZK Oświęcim](https://mzk.oswiecim.pl) | Oświęcim (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MPK Radomsko](https://mpk.radomsko.pl) | Radomsko (bus) | GTFS-RT (api6) | ✅ | 🗺️ | — |
| [MKS Dębica](https://mks.debica.pl) | Dębica (bus) | Source unavailable | ❌ | ❌ | — |
| [KM Kołobrzeg](https://km.kolobrzeg.pl) | Kołobrzeg (bus) | Static GTFS | ❌ | ❌ | — |
| [SPGK Sanok](https://spgk.sanok.pl) | Sanok (bus) | Source unavailable | ❌ | ❌ | — |
| [MZK Ostrołęka](https://mzk.ostroleka.pl) | Ostrołęka (bus) | Static GTFS | ❌ | ❌ | — |

¹ Kraków: GPS for buses (matched by route + brigade) and for trams within a few stops of the stop (matched by upcoming stop + scheduled time), via zbiorkom.live api6-open.

### Data Sources

| Source | Cities | RT Format |
|--------|--------|-----------|
| **api.zbiorkom.live (api6)** | Białystok, Częstochowa, Elbląg, Gorzów Wlkp., Kielce, Kutno, Legnica, Leszno, Lublin, Olsztyn, Opole, Przemyśl, Radom, Rybnik, Rzeszów, Suwałki, Toruń, Wrocław + 1.6.0 providers | GTFS-RT protobuf |
| **mkuran.pl** | Bydgoszcz, Ełk, WKD, Warszawa | GTFS-RT protobuf / JSON |
| **City-specific** | Gdańsk, Gdynia, GZM, Kraków, Łódź, Poznań, Szczecin | mixed |
| **kiedyPrzyjedzie.pl** | 11 regional carriers | REST API |
| **PLK OpenData** | PKP / SKM / PolRegio / IC | REST API |
| **Time4BUS** | Bytów, Tczew | REST API |

---

## Live Vehicle Map

When a departure includes GPS coordinates, clicking the row opens a Leaflet map (powered by OpenStreetMap tiles, served through Home Assistant's own tile proxy on 2026.9 and later). The vehicle marker refreshes every 30 seconds while the map is open.

- **All GTFS-RT cities** support the map via multi-strategy position matching: `vehicle_code` → `trip_id` → `route_id`
- Markers show the route number inside a colored circle with a direction arrow
- The map takes precedence over `tap_action`; hold and double-tap actions remain available

> **Note:** A provider marked as 🗺️ may have individual departures without a map when the upstream feed omits a position or vehicle identifier for that specific trip.

---

## What's New in 2.0.0

- **One hub per provider** — existing single-stop entries are merged automatically;
  Gdańsk ZTM stops become one `ZTM Gdańsk` hub, PLK stations one `PLK` hub.
- **New entity names** — `mzkzg_*` entity IDs are migrated, e.g.
  `sensor.mzkzg_plk_258458` → `sensor.gdansk_srodmiescie_odjazdy`.
- **Hub sensors** — multi-stop providers expose a merged sensor such as
  `sensor.ztm_gdansk_odjazdy` alongside per-stop sensors.
- **Add stops later** — a new stop added through the config flow joins the existing
  provider hub instead of creating another entry.
- **Hub options** — open the hub entry options to change settings, add a stop
  (searchable for large providers) or remove a stop together with its device and
  entities. A hub always keeps at least one stop.
- **Offline map library** — Leaflet and its CSS ship with the integration and load
  from `/polish_transport/leaflet/` on demand, without unpkg/CDN access.
- **Lower memory use** — raw GTFS archives are released after the hub stops are
  parsed, tomorrow's fallback schedule is precomputed, and long-lived caches are
  pruned and capped.
- **Technical domain** — `mzkzg_transport` remains only as the hidden integration
  domain required for in-place upgrades; it is not used in entity or device names.
- **Card cleanup** — only `custom:polish-transport-card` is registered; the legacy
  `custom:mzkzg-transport-card` alias was removed.
- **Card UI overhaul** — five presets (`native`, `standard`, `compact`, `minimal`,
  `e_ink`), theme modes, header styles/clock, grouped view, multi-column boards,
  row actions in the GUI editor and per-sensor overrides.
- **Filters** — route, destination, platform, track, vehicle type, provider,
  low-floor, bike, AC and ticket-machine filters, plus departure visibility and
  grace-period controls.
- **Live map polish** — compact vehicle popups, spread-out overlapping markers,
  selected vehicle centred at zoom 16, dark-theme map controls and a local Leaflet
  bundle.
- **Provider coverage** — Kraków on zbiorkom.live api6-open, 11 api6 feeds fixed,
  correct service-day filtering, Bielsko-Biała and Bytów, and automatic migration
  of changed GTFS stop IDs.
- **Reliability** — duplicate schedule/realtime rows merged, recorder-friendly
  attributes, PLK 429 backoff, one shared PLK usage sensor and TLS handling for
  operators with expired certificates.
- **Quality gates** — GitHub Actions CI for lint/build/pytest/Playwright, visual
  snapshots, map tests and a weekly provider-status workflow.

### Upgrading from 1.6.x or a 2.0 pre-release

Update through HACS (or replace the integration files) and restart Home Assistant.
The first start runs the 2.0 migration automatically:

1. entries of the same provider are merged into one hub,
2. per-stop sensors and devices are moved to the hub,
3. `mzkzg_*` entity IDs are renamed,
4. duplicate legacy entities are removed.

Keep a backup of `/config/.storage/` if you have custom automations that reference
old entity IDs. The migration is idempotent and can be retried.

---

## Installation

### HACS

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/toczke/polish-public-transport-card` as **Integration**
3. Install **Polish Public Transport**
4. Restart Home Assistant

### Manual

```bash
cp -r custom_components/mzkzg_transport/ /config/custom_components/
```

Restart Home Assistant.

---

## Setup

1. **Settings → Devices & Services → Add Integration → Polish Public Transport**
2. Choose your provider from the dropdown
3. Search or type a stop ID. Providers with more than 3000 stops (for example
   ZTP Kraków) show a search field first; submit a name or ID, then pick from the
   narrowed list.
4. **Łódź only**: choose between "Single Stop" or "Bus Stop Group" (transfer hub) — the latter expands into one aggregated sensor covering all platforms
5. For PKP/PLK: enter your API key from [dane.plk-sa.pl](https://dane.plk-sa.pl)

**Rail vs bus:** for train departures choose the **Polskie Linie Kolejowe** provider.
PLK station labels end with `PKP` (e.g. `Zabierzów PKP`), so they are not confused with
nearby bus stops from ZTP/KiedyPrzyjedzie.

**Multiple stops:** add the integration once per stop. Entries of the same provider share
the operator device, the GTFS cache, the PLK request budget and the live-vehicle snapshot,
so adding several stops does not multiply upstream requests. A single entry can also hold
several stops (`stops:` in the config entry) and then exposes one aggregated sensor.

If an operator changes its stop identifiers in the GTFS feed, existing entries resolve
the new ID automatically by stop name and platform and expose the mapped value as the
`resolved_stop_id` attribute.

### Full-day timetable (kiedyPrzyjedzie)

For kiedyPrzyjedzie providers, open **Configure** on the entry and set
**Timetable lines** to a comma-separated list (e.g. `854, 870`). The sensor then exposes a
`timetable` attribute with `today` and `tomorrow` arrays, while the normal `departures`
attribute stays short for the card:

```yaml
{{ state_attr('sensor.pks_gdansk_dworzec_odjazdy', 'timetable').today }}
```

The timetable responses are cached for an hour. Times are ISO 8601 strings.

### Offline fallback

Every successfully downloaded GTFS archive is stored under
`/config/.storage/mzkzg_transport/gtfs/`. If the upstream server is unreachable, the
integration keeps serving the last saved schedule (without realtime delays) instead of
showing no departures.

---

## Card Configuration

### Adding the Card

The card registers itself automatically. In the Lovelace UI: **Add Card → Polish Transport Card**.

### YAML Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entities` | list | required | Sensor entity IDs (string or object with per-sensor overrides) |
| `display_preset` | string | `standard` | `standard` / `compact` / `minimal` / `native` (HA look) / `e_ink` |
| `view_mode` | string | `mixed` | `mixed` (merged timeline) / `tabs` (per-stop) / `grouped` (grouped by line) |
| `columns` | int | `1` | Row columns: `1`, `2` or `3` (good for tablets) |
| `header_style` | string | `provider` | `provider`, `theme` (HA primary), `custom` |
| `header_color` | string | — | Custom header color (when `header_style: custom`) |
| `show_header` | bool | `true` | Show the card header |
| `show_clock` | bool | `false` | Show current time in the header |
| `show_refresh` | bool | `false` | Show a manual refresh button in the header |
| `max_departures` | int | `10` | Max rows per stop (1–100) |
| `min_departures` | int | `0` | Minimum rows; shorter lists are padded with empty rows |
| `time_format` | string | `auto` | `auto` / `24h` / `12h` |
| `show_delays` | bool | `true` | Show realtime delays |
| `show_countdown` | bool | `true` | Show minutes-until-departure |
| `show_vehicle` | bool | `true` | Show vehicle number chip |
| `show_platform` | bool | `true` | Show platform / stand / track |
| `show_accessibility` | bool | `true` | Show bike / wheelchair / A/C icons |
| `show_stop_name` | bool | `false` | Show stop name on merged rows |
| `show_footer` | bool | `true` | Show footer |
| `show_last_update` | bool | `true` | Show last update time in the footer |
| `filter_routes` | list | — | Show only these routes |
| `exclude_routes` | list | — | Hide these routes |
| `destination_filter` | list | — | Show only these destinations |
| `exclude_destinations` | list | — | Hide departures whose destination contains any of these strings |
| `filter_vehicle_types` | list | — | Show only `bus`, `tram` or `train` |
| `filter_providers` | list | — | Show only these provider keys |
| `filter_platform` | string | — | Show only this platform |
| `filter_track` | string | — | Show only this track |
| `highlight_mode` | bool | `false` | Dim instead of hide filtered routes |
| `hide_terminus` | bool | `true` | Hide departures ending at this stop |
| `hide_cancelled` | bool | `false` | Hide cancelled departures |
| `realtime_only` | bool | `false` | Show only realtime departures |
| `hide_departed` | bool | `true` | Hide rows after their departure time (+ grace) |
| `departed_grace_minutes` | int | `1` | Minutes a departed row may stay visible |
| `max_minutes` | int | `0` | Show only departures within this many minutes (`0` = no limit) |
| `only_low_floor` | bool | `false` | Show only low-floor vehicles |
| `only_bike` | bool | `false` | Show only vehicles with bike space |
| `only_ac` | bool | `false` | Show only air-conditioned vehicles |
| `only_ticket_machine` | bool | `false` | Show only vehicles with a ticket machine |
| `tap_action` | object | `more-info` | Row tap action |
| `hold_action` | object | `none` | Row hold action |
| `double_tap_action` | object | `none` | Row double-tap action |

All filters and `max_departures` can be overridden per sensor. The visual editor exposes
both a global form and a **per-sensor override** form (including stop-name labels,
override reset and row ordering); the same structure is accepted in YAML. Tap, hold and
double-tap actions are editable with Home Assistant's native action picker. The editor
also shows how many rows remain visible after filtering; providers use a multi-select
of known operators.

### Card presets

- `standard` — full card with provider-coloured header
- `compact` — denser rows, fewer secondary details
- `minimal` — header/footer/accessibility hidden, very compact
- `native` — Home Assistant-native look: transparent header, HA typography, dividers,
  secondary-background hover and neutral chips; follows the active HA theme
- `e_ink` — high-contrast, animation-free layout

`header_style: theme` makes the header use the HA primary colour; `provider` keeps the
operator colour; `custom` uses `header_color`.

### Per-sensor Overrides

```yaml
type: custom:polish-transport-card
entities:
  - entity: sensor.gdansk_main_odjazdy
    filter_routes: ["2", "8"]
    exclude_routes: ["N1"]
    destination_filter: ["Wrzeszcz"]
    exclude_destinations: ["Poznań Główny"]
    filter_vehicle_types: ["tram"]
    max_departures: 40
  - entity: sensor.gdynia_central_odjazdy
    filter_routes: ["147"]
    realtime_only: true
    max_minutes: 30
    only_low_floor: true
filter_routes: ["N1"]
min_departures: 5
header_style: provider
time_format: 24h
show_clock: true
show_refresh: true
columns: 2
tap_action:
  action: more-info
hold_action:
  action: navigate
  navigation_path: /lovelace/transport
```

---

## Testing

```bash
pip install -r requirements_test.txt
PYTHONPATH=custom_components:$PYTHONPATH pytest tests/ -q

npm ci
npm run lint
npm run build
npx playwright test
```

**174 Python tests** cover GTFS-RT parsing, calendar filtering, position matching,
route fallback, speed normalization, deduplication and provider-specific integration.
**21 Playwright tests** cover card config, filters, the editor, the live-map popup,
accessibility and visual snapshots for all five presets. Update visual baselines with
`npx playwright test tests/e2e/visual-presets.spec.ts --update-snapshots`. CI runs
lint, build, Python and Playwright on every push and pull request.

A separate **Provider status** workflow runs every Monday at 04:17 UTC and checks
every configured GTFS/GTFS-RT feed, realtime endpoint and vehicle-position endpoint.
It uploads a Markdown/JSON report and opens (or updates) a GitHub issue when any
provider fails. Run it manually from the Actions tab with **Provider status → Run
workflow**, or locally with:

```bash
python scripts/validate_providers.py --markdown provider-status.md
```

---

## Architecture

```
config_flow → ConfigEntry
     ↓
__init__ → Coordinator(s) → provider_*.fetch()
     ↓
sensor / binary_sensor
     ↓
Lovelace card (reads entity attributes + renders map)
```

- **Providers** (`provider_*.py`): fetch departures from upstream APIs, apply RT delays, enrich with GPS
- **Coordinator** (`coordinator.py`): dispatches to the correct provider, handles sleep mode, deduplicates
- **Sensors** (`sensor.py`, `binary_sensor.py`): expose data to HA; `PolishAggregatedSensor` merges multi-stop entries
- **Card** (`polish-transport-card.js`): Lit-based web component rendering the Lovelace UI and Leaflet map

---

## Contributing

Issues and PRs are welcome. Before submitting, please:

1. Run `python -m pytest tests/ -q` — all 90 tests must pass
2. Run `node --check custom_components/mzkzg_transport/www/polish-transport-card.js`
3. Include test coverage for new features or bug fixes

## License

MIT © 2025–2026 [toczke](https://github.com/toczke)
