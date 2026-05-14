# MZKZG Transport Card

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.2.4-blue.svg)](https://github.com/toczke/mzkzg-transport-card/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-34%20passing-brightgreen.svg)](#testing)

A custom Home Assistant integration and Lovelace card providing real-time departure boards for Tricity (Gdańsk, Gdynia, Sopot) and surrounding area public transport. Includes a visual editor for easy configuration.

![Preview](docs/screenshots/ztm-standard.png)

---

## Table of Contents

- [Features](#features)
- [Supported Operators](#supported-operators)
- [Installation](#installation)
- [Integration Setup](#integration-setup)
- [Card Configuration](#card-configuration)
- [Display Presets](#display-presets)
- [Provider Architecture](#provider-architecture)
- [Vehicle Capabilities](#vehicle-capabilities-ztm-gdańsk)
- [PLK Rate Limiting](#plk-rate-limiting)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Gallery](#gallery)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- Real-time departure data with delay information
- Multi-provider support (urban buses, trams, trolleybuses, trains)
- Visual card editor — no YAML required
- Three display presets: Standard, Compact, E-ink
- Route and destination filtering with highlight mode
- Vehicle capability icons (bike rack, wheelchair, AC, USB, ticket machine)
- Dynamic rate limiting for railway API
- Fully localized (Polish & English)

---

## Supported Operators

| Operator | Coverage | Realtime |
|----------|----------|----------|
| **ZTM Gdańsk** | Buses and trams in Gdańsk and surrounding municipalities | ✅ |
| **ZKM Gdynia** | Buses and trolleybuses in Gdynia | ✅ |
| **MZK Wejherowo** | Buses in Wejherowo area | ❌ (schedule only) |
| **Tczew (Time4BUS)** | Bus departures with live fallback to schedule | âœ… |
| **PKS Gdańsk Sp. z o.o.** | Intercity and regional bus departures on kiedyprzyjedzie.pl | ✅ |
| **Albatros** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **Przewozy Autobusowe GRYF** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **Nord Express** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **PKS Gdynia S.A.** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **Miejski Zakład Komunikacji w Malborku** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **PKS Słupsk S.A.** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **MZK Starogard Gdański** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **PKS Starogard Gdański S.A.** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **Bytów** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **Powiat Człuchowski** | Bus departures on kiedyprzyjedzie.pl | ✅ |
| **PKP / SKM / Polregio / IC** | Railway stations across Poland (via PLK) | ✅ |

| **Supported capabilities** | ZTM: bike/wheelchair/AC/USB/ticket machine + side number; ZKM: side number (+ bike/wheelchair/AC if API provides); Time4BUS: side number + wheelchair/AC/ticket machine if available; kiedyPrzyjedzie carriers: bike/wheelchair/AC/ticket machine from vehicle attributes; PLK: platform/track/train metadata | - |

Note: Time4BUS supports realtime departures with schedule fallback.

---

## Installation

### HACS (Recommended)

1. Open **HACS → Integrations → ⋮ → Custom repositories**
2. Add URL: `https://github.com/toczke/mzkzg-transport-card` (type: **Integration**)
3. Search for and install **MZKZG Transport**
4. Restart Home Assistant

### Manual

Copy the integration to your config directory:

```bash
cp -r custom_components/mzkzg_transport/ /config/custom_components/
```

Restart Home Assistant.

---

## Integration Setup

**Settings → Devices & Services → Add Integration → MZKZG Transport**

1. Select provider (ZTM / ZKM / MZK / Tczew / PKS Gda?sk / Albatros / GRYF / Nord Express / PKS Gdynia / ZKM Gdynia / MZK Malbork / PKS S?upsk / MZK Starogard / PKS Starogard / Byt?w / Powiat Cz?uchowski / PLK)
2. For PLK: enter your API key (see below)
3. Select a stop from the list
4. Done — sensor and binary sensor are created automatically

### PKP/PLK API Key

Railway data requires a free API key from PLK:

1. Go to [https://pdp-api.plk-sa.pl](https://pdp-api.plk-sa.pl)
2. Register a free account
3. Navigate to **API → API Keys**
4. Generate a new key (tier "basic" = 100 requests/hour)
5. Paste the key during integration setup

The integration dynamically manages rate limits based on your tier and number of configured stations.

---

## Card Configuration

Add the card via: **Add Card → MZKZG Transport Card**

All options are available in the visual editor:

![Editor](docs/screenshots/editor.png)

### Manual Card Registration

If the card does not appear in the card picker after installation, add the resource manually:

1. **Edit Dashboard** → **⋮** (top-right) → **Manage resources**
2. Add resource:
   - **URL:** `/mzkzg_transport/mzkzg-transport-card.js`
   - **Type:** JavaScript module

See [#1](https://github.com/toczke/mzkzg-transport-card/issues/1) for details.

### Options Reference

| Option | Description | Default |
|--------|-------------|---------|
| `entities` | Sensor entity list | *required* |
| `title` | Card title | Auto (stop name) |
| `icon` | Header icon (MDI) | Auto (bus-stop/train) |
| `display_preset` | `standard` / `compact` / `e_ink` | `standard` |
| `view_mode` | `mixed` / `tabs` (multi-entity) | `mixed` |
| `max_departures` | Max departures shown (3–20) | `10` |
| `header_color` | Header color (hex) | Auto (provider) |
| `filter_routes` | Show only specified routes | — |
| `destination_filter` | Filter by destination name | — |
| `filter_platform` | Filter by platform number | — |
| `filter_track` | Filter by track number | — |
| `highlight_mode` | Dim non-matching instead of hiding | `false` |
| `hide_terminus` | Hide departures ending at this stop | `true` |
| `realtime_only` | Show only realtime departures | `false` |
| `show_delays` | Show delay information | `true` |
| `show_footer` | Show "Odświeżono: HH:MM:SS" | `true` |
| `show_bike` | Show bike rack icon | `true` |
| `show_wheelchair` | Show wheelchair ramp icon | `true` |
| `show_ac` | Show air conditioning icon | `true` |
| `show_ticket_machine` | Show ticket machine icon | `true` |
| `refresh_interval` | Countdown refresh (seconds) | `60` |

### YAML Example

```yaml
type: custom:mzkzg-transport-card
entities:
  - sensor.mzkzg_ztm_1327
  - sensor.mzkzg_zkm_35190
title: "Mój przystanek"
icon: mdi:tram
display_preset: standard
view_mode: tabs
max_departures: 8
filter_routes:
  - "154"
  - "289"
show_delays: true
show_footer: true
```

---

## Display Presets

| Preset | Use Case | Description |
|--------|----------|-------------|
| **Standard** | Daily use | Full info: delays, icons, capabilities, footer |
| **Compact** | Small widgets | Minimal: route + headsign + time only |
| **E-ink** | E-ink displays | Static times, no animations, high contrast |

---

## Provider Architecture

Each provider uses different APIs and data strategies. Below is a detailed breakdown of how the integration communicates with each data source.

### ZTM Gdańsk (TRISTAR)

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `GET https://ckan2.multimediagdansk.pl/departures?stopId={id}` | Real-time departures with delays | Every 30s |
| `GET https://mapa.ztm.gda.pl/d/otwarte-dane/ztm/baza-pojazdow.json?v=2` | Vehicle fleet database (capabilities) | Cached 7 days |
| `GET https://mapa.ztm.gda.pl/.../stops.json` | Stop list for config flow | On setup |

**Data flow:**
1. Departures endpoint returns scheduled and estimated times, delay in seconds, vehicle code, and route info.
2. Vehicle code is matched against the fleet database to resolve capabilities (bike rack, wheelchair ramp, AC, USB, ticket machine).
3. Route numbers below 100 are classified as trams, the rest as buses.

---

### ZKM Gdynia (ZDiZ)

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `GET https://api.zdiz.gdynia.pl/pt/delays?stopId={id}` | Real-time departures with delays | Every 30s |
| `GET https://api.zdiz.gdynia.pl/pt/routes` | Route ID → short name mapping | Cached until failure (retry after 1h) |
| `GET https://api.zdiz.gdynia.pl/pt/stops` | Stop list for config flow | On setup |

**Data flow:**
1. Delays endpoint returns departures with route IDs, estimated/theoretical times, and delay values.
2. Route IDs are resolved to human-readable short names via the routes endpoint.
3. Routes 20–29 are classified as trolleybuses, the rest as buses.

---

### MZK Wejherowo (Static GTFS)

| Resource | Purpose | Refresh |
|----------|---------|---------|
| `GET https://mkuran.pl/gtfs/wejherowo.zip` | Complete GTFS dataset (stops, routes, trips, stop_times) | Cached on disk, refreshed daily |

**Data flow:**
1. GTFS ZIP is downloaded and parsed into memory (singleton with `asyncio.Lock` for thread safety).
2. Every 30 seconds, the current time is compared against `stop_times.txt` to compute upcoming departures.
3. Supports night services with times exceeding 24:00 (e.g., `25:15:00` = 01:15 next day).
4. No real-time data — all times are from the static schedule.

---

### Tczew (Time4BUS)

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `GET https://time4bus.com/t4b/operators/tczew/stops?limit=1000&offset=0` | Stop list for config flow | On setup |
| `GET https://time4bus.com/t4b/live/schedules/tczew/stops/{stopId}/departures` | Live departures | Every 30s |
| `GET https://time4bus.com/t4b/operators/tczew/stops/{stopId}/departures?date=YYYY-MM-DD` | Schedule fallback | On live failure / empty live |

**Data flow:**
1. The integration uses `fullcode` as the stop ID.
2. It tries live departures first.
3. If live data is unavailable or empty, it falls back to the schedule endpoint for the same stop and date.

---

### kiedyPrzyjedzie.pl carriers

| Carrier | Endpoint | Purpose | Refresh |
|---------|----------|---------|---------|
| **PKS Gdańsk Sp. z o.o.** | `GET https://pksgdansk.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **PKS Gdańsk Sp. z o.o.** | `GET https://pksgdansk.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Albatros** | `GET https://albatros.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Albatros** | `GET https://albatros.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Przewozy Autobusowe GRYF** | `GET https://gryf.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Przewozy Autobusowe GRYF** | `GET https://gryf.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Nord Express** | `GET https://nordexpress.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Nord Express** | `GET https://nordexpress.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **PKS Gdynia S.A.** | `GET https://pksgdynia.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **PKS Gdynia S.A.** | `GET https://pksgdynia.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Miejski Zakład Komunikacji w Malborku** | `GET https://malbork.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Miejski Zakład Komunikacji w Malborku** | `GET https://malbork.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **PKS Słupsk S.A.** | `GET https://pksslupsk.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **PKS Słupsk S.A.** | `GET https://pksslupsk.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **MZK Starogard Gdański** | `GET https://starogard.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **MZK Starogard Gdański** | `GET https://starogard.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **PKS Starogard Gdański S.A.** | `GET https://pksstarogard.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **PKS Starogard Gdański S.A.** | `GET https://pksstarogard.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Bytów** | `GET https://bytow.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Bytów** | `GET https://bytow.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |
| **Powiat Człuchowski** | `GET https://czluchow.kiedyprzyjedzie.pl/stops` | Stop list for config flow | On setup |
| **Powiat Człuchowski** | `GET https://czluchow.kiedyprzyjedzie.pl/api/departures/{stopId}` | Departure board with normalized timestamps | Every 30s |

**Data flow:**
1. `stops` returns a flat list of all stops, each with a composite stop ID like `1564032:1635414`.
2. `departures/{stopId}` returns rows with relative or clock-based times plus a server timestamp.
3. The integration converts those values into ISO timestamps so the existing card and sensors can reuse the same rendering logic.

---

### PKP/PLK Railway (OpenData API)

| Endpoint | Purpose | Refresh |
|----------|---------|---------|
| `GET https://pdp-api.plk-sa.pl/api/v1/schedules?stations={id}&dateFrom=...&dateTo=...` | Planned timetable for a station | Cached for the entire day (1 req/station/day) |
| `GET https://pdp-api.plk-sa.pl/api/v1/operations?stations={ids}&withPlanned=true` | Real-time train positions and delays | Dynamic interval (see [Rate Limiting](#plk-rate-limiting)) |

**Authentication:** All requests require an `X-API-Key` header (free registration at [pdp-api.plk-sa.pl](https://pdp-api.plk-sa.pl)).

**Data flow:**
1. Schedule data provides the base timetable: train numbers, categories (IC/SKM/R/TLK), carriers, platforms, tracks, and full routes.
2. Operations data is fetched for **all configured PLK stations at once** (shared cache with `asyncio.Lock`) to minimize API calls.
3. Realtime delays are calculated by comparing `actualDeparture` vs `plannedDeparture` from operations data.
4. On HTTP 429 (rate limit): the integration returns cached or empty data instead of failing.

**Exposed data per departure:** delay, platform, track, carrier name, train number, category, cancellation status.

---

## Vehicle Capabilities (ZTM Gdańsk)

The card fetches the ZTM vehicle fleet database and displays icons for the actual vehicle serving each departure:

| Icon | Meaning |
|------|---------|
| 🚲 | Bike rack |
| ♿ | Wheelchair ramp |
| ❄️ | Air conditioning |
| 🔌 | USB charging |
| 🎫 | Ticket machine |

Vehicle number (*numer boczny*) is shown as a chip next to the headsign. Fleet data is refreshed every 7 days (~330 KB).

---

## PLK Rate Limiting

The integration dynamically calculates refresh intervals to stay within API limits:

```
interval = 3600 / ((hourly_limit × 0.8) / num_stations)
```

| Tier | Limit | 1 station | 4 stations |
|------|-------|-----------|------------|
| Basic | 100/h | 60s | 180s |
| Standard | 500/h | 60s | 60s |
| Premium | 2000/h | 60s | 60s |

**Behavior:**
- Schedule data is cached for the entire day (1 request per station per day)
- Operations (realtime) cache is shared across all PLK stations
- On HTTP 429: returns cached/empty data instead of failing

### API Usage Sensor

`sensor.*_plk_api_usage` exposes:

| Attribute | Description |
|-----------|-------------|
| `state` | Total requests since HA start |
| `rate_limit_hits` | Number of 429 responses |
| `last_success` | Timestamp of last successful request |

---

## Project Structure

```
custom_components/mzkzg_transport/
├── __init__.py          # Entry setup, card registration, unload
├── config_flow.py       # Multi-step config flow (provider → API key → stop)
├── coordinator.py       # Data fetching (ZTM, ZKM, MZK, PLK)
├── sensor.py            # Departure sensor + PLK API usage sensor
├── binary_sensor.py     # Delay alert binary sensor
├── const.py             # Constants, URLs, tier limits
├── gtfs_provider.py     # GTFS parser for MZK Wejherowo
├── strings.json         # UI strings
├── translations/        # en.json, pl.json
├── manifest.json        # Integration metadata
└── brand/               # Icon for HA UI

mzkzg-transport-card.js  # Lovelace card source
tests/
├── test_integration.py  # ZTM, ZKM, coordinator tests
└── test_extended.py     # PLK, GTFS, binary sensor tests
```

---

## Testing

```bash
python -m pytest tests/ -v
```

On Windows, run tests with selector loop policy:

```bash
python -c "import asyncio,sys,pytest; asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()); sys.exit(pytest.main(['-q']))"
```

**34 tests passing, 1 skipped** — covering ZTM fetch, ZKM fetch, Time4BUS, kiedyPrzyjedzie carriers, PLK schedules/rate limiting, GTFS parsing, and binary sensor logic.

Tests use `aioresponses` for HTTP mocking and `MagicMock` for Home Assistant core.

---

## Gallery

### ZTM Gdańsk — Standard view with vehicle capabilities

![ZTM Standard](docs/screenshots/ztm-standard.png)

---

## Changelog

### 1.2.4

- Bus providers no longer display platform/track chips in the card (PLK rail only).
- Vehicle side number (*numer boczny*) displayed inline right after headsign for non-PLK providers.
- Added side-number mapping for ZKM Gdynia (`vehicleCode` / `vehicleId`).
- Added ticket machine capability mapping for Time4BUS (`vehicleInfo.ticketMachine`).
- Added ticket machine capability mapping for kiedyPrzyjedzie carriers (from `vehicle_attributes`).
- Added subtle live-dot pulse animation with reduced-motion fallback.
- Updated tests and README (Windows test command, capabilities summary, current test count).

### 1.2.1

- Responsive layout with CSS container queries
- Custom header icon (MDI) with auto-detection (train/bus-stop)
- Compact mode hides capabilities, vehicle number, and footer
- PLK API usage sensor (requests count, rate limit hits)
- PLK graceful degradation — no crash on rate limit, shows empty data
- Slimmer header, friendlier rate limit message
- Icons wrap below headsign when space is limited
- E-ink icon color fix (black on white)
- Footer displays "Odświeżono: HH:MM:SS"

### 1.1.0

- Vehicle capabilities from ZTM fleet database (bike, wheelchair, AC, USB, ticket machine)
- Vehicle number display
- PLK: platform and track as chips, carrier name shortening
- Filter by platform/track
- Dynamic PLK rate limiting (limit ÷ stations)
- Visual editor: all options available
- Fix: editor focus loss (stopPropagation + debounce)
- Fix: e-ink preset no longer resets settings
- Fix: PLK entry loads even on rate limit (no crash)
- HA 2026.3+ compliance (brand/, device_info, async_unload)

### 1.0.0

- Initial release
- ZTM, ZKM, MZK, PLK providers
- Presets: standard, compact, e-ink
- Filtering, highlight, tabs
- Binary sensor for delay alerts

---

## License

[MIT](LICENSE) © Tomasz Toczek
