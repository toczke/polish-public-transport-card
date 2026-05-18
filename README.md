# Polish Public Transport Card

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.4.0-blue.svg)](https://github.com/toczke/mzkzg-transport-card/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-58%20passing-brightgreen.svg)](#testing)

Home Assistant integration + Lovelace card for real-time departures across Poland — Warszawa, Tricity, Kraków, Poznań, Szczecin, Katowice/GZM, Łódź, Lublin, and 30+ more cities.

## Table of Contents

- [Screenshots](#screenshots)
- [Display Presets](#display-presets)
- [Supported Operators](#supported-operators)
- [Features](#features)
- [Installation](#installation)
- [Setup](#setup)
- [Card Configuration](#card-configuration)
- [PLK API Usage Sensor](#plk-api-usage-sensor)
- [API Architecture](#api-architecture)
- [Testing](#testing)
- [Local Preview](#local-preview)
- [Contributing](#contributing)
- [Project Structure](#project-structure)
- [License](#license)

## Screenshots

### Standard (light / dark)

![Standard light](docs/screenshots/standard-light.png)
![Standard dark](docs/screenshots/standard-dark.png)

### PLK Rail

![PLK](docs/screenshots/plk.png)

### Compact

![Compact](docs/screenshots/compact.png)

### E-ink

![E-ink](docs/screenshots/e-ink.png)

### Multi-provider: mixed / tabs

![Mixed](docs/screenshots/mixed.png)
![Tabs](docs/screenshots/tabs.png)

## Display Presets

| Feature | Standard | Compact | E-ink |
|---|:---:|:---:|:---:|
| Delay indicator | ✅ | ✅ | ❌ |
| Live countdown | ✅ | ✅ | ❌ |
| Vehicle icons (bike, wheelchair, AC) | ✅ | ❌ | ❌ |
| Platform / track chips | ✅ | ❌ | ❌ |
| Side number | ✅ | ❌ | ❌ |
| Footer (last update) | ✅ | ❌ | ❌ |
| Animated live dot | ✅ | ✅ | ❌ |
| Stop name subtitle | ✅ | ❌ | ❌ |

## Supported Operators

| Operator | Area | API / Data Source | Realtime | Vehicle Info |
|---|---|---|:---:|---|
| [ZTM Gdańsk](https://ztm.gda.pl) | Gdańsk (bus, tram) | TRISTAR CKAN API (`ckan2.multimediagdansk.pl`) | ✅ | bike, wheelchair, AC, USB, ticket machine, side number |
| [ZKM Gdynia](https://zkmgdynia.pl) | Gdynia (bus, trolleybus) | ZDiZ API (`api.zdiz.gdynia.pl`) | ✅ | side number |
| [MZK Wejherowo](https://mzkwejherowo.pl) | Wejherowo (bus) | Static GTFS (`mkuran.pl/gtfs/wejherowo.zip`) | ❌ | — |
| [MZK Tczew](https://mzk.tczew.pl) | Tczew (bus) | Time4BUS API (`time4bus.com`) | ✅ | wheelchair, AC, ticket machine, side number |
| [PKS Gdańsk](https://pksgdansk.pl) | Pomorskie (regional bus) | kiedyPrzyjedzie API (`pksgdansk.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [Albatros](https://albatros.kiedyprzyjedzie.pl) | Pomorskie (regional bus) | kiedyPrzyjedzie API (`albatros.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [GRYF](https://gryf.kiedyprzyjedzie.pl) | Pomorskie (regional bus) | kiedyPrzyjedzie API (`gryf.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [Nord Express](https://nordexpress.kiedyprzyjedzie.pl) | Słupsk region (bus) | kiedyPrzyjedzie API (`nordexpress.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [PKS Gdynia](https://pksgdynia.pl) | Gdynia region (bus) | kiedyPrzyjedzie API (`pksgdynia.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [MZK Malbork](https://malbork.kiedyprzyjedzie.pl) | Malbork (city bus) | kiedyPrzyjedzie API (`malbork.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [PKS Słupsk](https://pksslupsk.pl) | Słupsk region (bus) | kiedyPrzyjedzie API (`pksslupsk.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [MZK Starogard Gd.](https://starogard.kiedyprzyjedzie.pl) | Starogard (city bus) | kiedyPrzyjedzie API (`starogard.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [PKS Starogard Gd.](https://pksstarogard.kiedyprzyjedzie.pl) | Starogard region (bus) | kiedyPrzyjedzie API (`pksstarogard.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [Komunikacja Bytów](https://bytow.kiedyprzyjedzie.pl) | Bytów (city bus) | kiedyPrzyjedzie API (`bytow.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [Powiat Człuchowski](https://czluchow.kiedyprzyjedzie.pl) | Człuchów region (bus) | kiedyPrzyjedzie API (`czluchow.kiedyprzyjedzie.pl`) | ✅ | bike, wheelchair, AC, ticket machine |
| [PKP / SKM / Polregio / IC](https://portalpasazera.pl) | Railway stations | PLK OpenData API (`pdp-api.plk-sa.pl`) | ✅ | platform, track, carrier, train number, cancellation |
| [MPK Łódź](https://mpk.lodz.pl) | Łódź (bus, tram) | rozklady.lodz.pl XML API | ✅ | bike, wheelchair, AC, ticket machine |
| [ZTM Poznań](https://ztm.poznan.pl) | Poznań (bus, tram) | GTFS + GTFS-RT (`ztm.poznan.pl`) | ✅ | ramp, AC, bike, ticket machine, USB (vehicle dict) |
| [ZTM GZM (Katowice)](https://metropoliagzm.pl) | Metropolia GZM (bus, tram) | GTFS + GTFS-RT (`otwartedane.metropoliagzm.pl`) | ✅ | low floor (from GTFS ext) |
| [ZTP Kraków](https://ztp.krakow.pl) | Kraków (bus, tram) | GTFS + GTFS-RT (`gtfs.ztp.krakow.pl`) + TTSS API (`api.ttss.pl`) | ✅ | wheelchair, AC, vehicle model, side number |
| [ZTM Lublin](https://ztm.lublin.eu) | Lublin (bus, trolleybus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MPK Kielce](https://mpk.kielce.pl) | Kielce (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MPK Częstochowa](https://mpk.czest.pl) | Częstochowa (bus, tram) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [ZKM Elbląg](https://zkm.elblag.com.pl) | Elbląg (bus, tram) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MZK Gorzów Wlkp.](https://mzk-gorzow.com.pl) | Gorzów (bus, tram) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [ZTZ Rybnik](https://ztz.rybnik.pl) | Rybnik (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MZDiK Radom](https://mzdik.radom.pl) | Radom (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [PGK Suwałki](https://pgk.suwalki.pl) | Suwałki (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MZK Przemyśl](https://mzk.przemysl.pl) | Przemyśl (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MZK Kutno](https://mzkkutno.pl) | Kutno (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [MPK Legnica](https://mpk.legnica.pl) | Legnica (bus) | GTFS + GTFS-RT (`cdn.zbiorkom.live`) | ✅ | side number |
| [ZDiTM Szczecin](https://zditm.szczecin.pl) | Szczecin (bus, tram) | GTFS + GTFS-RT (`zditm.szczecin.pl`) | ✅ | side number |
| [ZTM Warszawa](https://ztm.waw.pl) | Warszawa (bus, tram, metro) | GTFS + GTFS-RT (`mkuran.pl`) | ✅ | side number |
| [MZK Ełk](https://mzk.elk.pl) | Ełk (bus) | GTFS + GTFS-RT (`mkuran.pl`) | ✅ | side number |
| [WKD](https://wkd.com.pl) | Warszawa–Grodzisk Maz. (rail) | GTFS + GTFS-RT (`mkuran.pl`) | ✅ | — |
| [BKM Białystok](https://bkm.bialystok.pl) | Białystok (bus) | Static GTFS (`cdn.zbiorkom.live`) | ❌ | — |
| [ZDZiT Olsztyn](https://zdzit.olsztyn.eu) | Olsztyn (bus, tram) | Static GTFS (`cdn.zbiorkom.live`) | ❌ | — |
| [MZK Opole](https://mzkopole.pl) | Opole (bus) | Static GTFS (`cdn.zbiorkom.live`) | ❌ | — |
| [ZTM Rzeszów](https://ztm.rzeszow.pl) | Rzeszów (bus) | Static GTFS (`cdn.zbiorkom.live`) | ❌ | — |
| [MZK Leszno](https://mzk.leszno.pl) | Leszno (bus) | Static GTFS (`cdn.zbiorkom.live`) | ❌ | — |

## Features

- Multi-provider departures (bus, tram, trolleybus, rail)
- Visual editor (no YAML required)
- Three display presets: `standard`, `compact`, `e_ink`
- Two view modes: `mixed` (merged timeline), `tabs` (per-stop tabs)
- Per-sensor filter overrides
- Route, destination, platform and track filtering
- Realtime delay rendering with animated live dot
- Row actions: `tap_action`, `hold_action`, `double_tap_action`
- Accessibility: keyboard focus, ARIA labels, reduced-motion support
- PLK dynamic rate limiting + API usage sensor
- **Sleep mode** — configurable per operator, pauses API polling during night hours (default 00:00–04:30)
- **Health sensor** — per-operator connectivity binary sensor with `healthy_stops` / `total_stops` attributes
- **Next-day fallback** — when no departures remain today, shows tomorrow's schedule (GTFS-RT providers)
- **Retry with backoff** — all providers retry failed requests 3× with exponential backoff (1s, 3s, 7s)
- **Multi-stop per operator** — one integration hub per carrier, stops grouped as child devices

## Installation

### HACS (recommended)

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/toczke/mzkzg-transport-card` as **Integration**
3. Install **Polish Public Transport**
4. Restart Home Assistant

### Manual

```bash
cp -r custom_components/mzkzg_transport/ /config/custom_components/
```

Restart Home Assistant.

## Setup

**Settings → Devices & Services → Add Integration → MZKZG Transport**

For PLK provider, add API key from `https://pdp-api.plk-sa.pl`.

## Card Configuration

**Add Card → MZKZG Transport Card** — the card registers itself automatically.

### Main Options

| Option | Description | Default |
|---|---|---|
| `entities` | Sensor entities (string or object with per-sensor overrides) | required |
| `display_preset` | `standard` / `compact` / `e_ink` | `standard` |
| `view_mode` | `mixed` / `tabs` | `mixed` |
| `max_departures` | Max rows (3–20) | `10` |
| `filter_routes` | Route filter | — |
| `destination_filter` | Destination filter | — |
| `filter_platform` | Platform filter | — |
| `filter_track` | Track filter | — |
| `highlight_mode` | Dim instead of hide for route filter | `false` |
| `hide_terminus` | Hide departures ending at stop | `true` |
| `realtime_only` | Show only realtime | `false` |
| `tap_action` | Row tap action | `more-info` |
| `hold_action` | Row hold/right-click action | `none` |
| `double_tap_action` | Row double-tap action | `none` |

### Per-sensor overrides

```yaml
type: custom:mzkzg-transport-card
view_mode: mixed
entities:
  - entity: sensor.mzkzg_ztm_1327
    filter_routes: ["2", "8"]
    destination_filter: ["Wrzeszcz"]
  - entity: sensor.mzkzg_zkm_35190
    filter_routes: ["147"]
    realtime_only: true
filter_routes: ["N1"]
tap_action:
  action: more-info
```

## PLK API Usage Sensor

`sensor.*_plk_api_usage` exposes:

- `state` / `requests_total`
- `rate_limit_hits`
- `last_success`

Counters are restored after Home Assistant restart.

## API Architecture

### Endpoint Usage

| Provider | Endpoints | Polling Interval |
|---|---|---|
| ZTM Gdańsk | `GET /departures?stopId=X` (realtime) + fleet cache from `baza-pojazdow.json` (weekly) | 30s |
| ZKM Gdynia | `GET /pt/delays?stopId=X` (realtime) + `GET /pt/routes` (route names, cached) | 30s |
| MZK Wejherowo | Static GTFS zip download (`mkuran.pl`), parsed locally | 30s (local lookup) |
| Time4BUS Tczew | `GET /live/schedules/tczew/stops/X/departures` → fallback to `GET /operators/tczew/stops/X/departures?date=Y` | 30s |
| kiedyPrzyjedzie | `GET /api/departures/{stop_id}` per carrier subdomain | 30s |
| GTFS-RT (Poznań, GZM, +10) | Static GTFS zip (daily cache) + GTFS-RT TripUpdates protobuf (per poll) + vehicle dict (cached) | 30s |
| ZTP Kraków | GTFS-RT TripUpdates (per poll) + GTFS metadata daily (stops/routes/trips only, no stop_times) + `api.ttss.pl` vehicles | 30s |
| PLK Rail | `GET /operations` (shared, all stations) + `GET /schedules` (per station, daily cache) | Dynamic (see below) |

### PLK Dynamic Rate Limiting

The PLK API has strict per-tier rate limits. The integration automatically calculates a safe polling interval:

| Tier | Hourly Limit | Daily Limit | Example interval (1 station) | Example interval (3 stations) |
|---|---|---|---|---|
| Basic | 100 req/h | 1,000 req/day | ~45s | ~135s |
| Standard | 500 req/h | 5,000 req/day | ~9s | ~27s |
| Premium | 2,000 req/h | 20,000 req/day | ~5s | ~9s |

How it works:
1. On coordinator init, counts all PLK stations configured
2. Calculates safe refresh rate using 80% of both hourly and daily limits
3. Takes the more conservative (slower) of the two intervals
4. All PLK stations share a single `/operations` request (batched by station IDs) protected by an async lock
5. `/schedules` responses are cached per-station for the entire day
6. On HTTP 429, the cycle is skipped and `rate_limit_hits` counter increments
7. All counters persist across HA restarts via `RestoreEntity`

## Testing

```bash
python -m pytest tests/ -v
```

Windows:

```bash
python -c "import asyncio,sys,pytest; asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()); sys.exit(pytest.main(['-q']))"
```

## Local Preview

```bash
python -m http.server 8125
```

Open `http://localhost:8125/dev/preview.html`

## Contributing

- Open an issue with provider, stop ID, steps, expected vs actual behavior.
- For code changes, include tests where possible.
- The card source lives in `custom_components/mzkzg_transport/www/mzkzg-transport-card.js`.

## Project Structure

```
custom_components/mzkzg_transport/
├── __init__.py              # Integration setup, card registration
├── config_flow.py           # UI-based configuration
├── const.py                 # API URLs, provider IDs, constants
├── coordinator.py           # DataUpdateCoordinator (dispatcher)
├── sensor.py                # Departure + PLK API usage sensors
├── binary_sensor.py         # Connectivity sensor
├── gtfs_provider.py         # MZK Wejherowo GTFS parser
├── provider_ztm.py          # ZTM Gdańsk (TRISTAR API)
├── provider_zkm.py          # ZKM Gdynia (ZDiZ API)
├── provider_mzk.py          # MZK Wejherowo (static GTFS)
├── provider_time4bus.py     # Time4BUS Tczew
├── provider_kiedyprzyjedzie.py  # kiedyPrzyjedzie carriers (11 operators)
├── provider_plk.py          # PLK rail (OpenData API)
├── provider_gtfsrt.py       # GTFS-RT cities (Poznań, GZM, Lublin, +10 more)
├── provider_krakow.py       # Kraków ZTP (GTFS-RT + api.ttss.pl)
├── www/
│   └── mzkzg-transport-card.js  # Lovelace card (vanilla JS)
├── translations/            # UI strings
└── manifest.json
tests/                       # pytest test suite
dev/
└── preview.html             # Standalone card preview (no HA needed)
```


## Data Sources & Licensing

This integration aggregates publicly available transit data. No authentication is required except for PLK (user provides their own API key).

| Source | License | Attribution |
|--------|---------|-------------|
| ZTM Gdańsk (ckan2.multimediagdansk.pl) | CC BY 4.0 | Gdańsk Open Data |
| ZDiTM Szczecin (zditm.szczecin.pl) | CC0 1.0 | — |
| MKuranowski GTFS (mkuran.pl) — Warszawa, Ełk, WKD | CC0 1.0 / ODbL | Miasto Stołeczne Warszawa (positions) |
| PLK OpenData (pdp-api.plk-sa.pl) | PLK Regulamin | Requires user API key |
| ZTP Kraków (gtfs.ztp.krakow.pl) | CC BY 4.0 | ZTP Kraków |
| zbiorkom.live (GTFS-RT for 16 cities + Kraków departures) | No public license | Community data, no auth required |
| kiedyPrzyjedzie, Time4BUS, ZKM Gdynia | No public license | Public APIs, no auth required |

> **Disclaimer:** Some data sources (zbiorkom.live, kiedyPrzyjedzie, Time4BUS) do not publish formal API documentation or licensing terms. These endpoints are publicly accessible without authentication. This project uses them in good faith for personal/home automation use. If you are a data provider and would like your API removed, please open an issue.

## License

[MIT](LICENSE) © Tomasz Toczek
