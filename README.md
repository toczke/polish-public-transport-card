# Polish Public Transport Card

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-2.0.3-blue.svg)](https://github.com/toczke/polish-public-transport-card/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/toczke/polish-public-transport-card?style=social)](https://github.com/toczke/polish-public-transport-card/stargazers)

Home Assistant integration + Lovelace card for real-time public transport departures in Poland. The integration groups all stops of one operator into a single hub, exposes per-stop and merged hub sensors, and ships its own Leaflet bundle for the live vehicle map.

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

### Development model

From 2.0.0 onward development is driven by **GitHub issues and pull requests only**:

- bugs and provider changes → issue tracker,
- code changes → pull request against `main`.

---

## Star history

<p align="center">
  <a href="https://star-history.com/#toczke/polish-public-transport-card&Date">
    <img src="https://api.star-history.com/svg?repos=toczke/polish-public-transport-card&type=Date" alt="GitHub star history" width="680">
  </a>
</p>

---

## Features

### Integration

- **One hub per provider** — all configured stops of an operator live in one config entry and one parent device, with one child device per stop.
- **Automatic 2.0 migration** — existing entries, devices and entity IDs are migrated in place; interrupted migrations self-heal on the next start.
- **Per-stop and hub sensors** — every stop keeps its own departures sensor; multi-stop hubs additionally expose one merged sensor.
- **Stable entity names** — `sensor.<stop>_odjazdy`, no `mzkzg` prefix in entity IDs or device names.
- **Hub options** — change settings, add a stop (searchable for large providers) or remove a stop together with its device and entities.
- **Automatic stop-ID resolution** — when an operator replaces GTFS stop IDs, entries resolve the new ID by stop name/platform and expose `resolved_stop_id`.
- **Sleep mode** — pause polling at night, configurable per hub.
- **Offline schedules** - every successful refresh saves a compact schedule per stop. If the provider is unreachable, the last timetable is replayed instead of losing all departures. A hub can also be switched to **100% offline** mode and never call the network.

### Card

- Five presets: `native`, `standard`, `compact`, `minimal`, `e_ink`.
- `mixed`, `tabs` and `grouped` views, 1–3 columns.
- Filters for routes, destinations, platforms, tracks, vehicle types, providers and accessibility features.
- Live countdown, delay indicators, vehicle chips, platform/track chips and accessibility icons.
- Tap / hold / double-tap actions editable in the GUI.
- Per-sensor overrides in the visual editor.
- Service alerts above the departures where the provider publishes them,
  filtered by line/stop or city-wide (`alerts_scope: matching|city`).
- Offline Leaflet bundle loaded only when the vehicle map opens.
- Optional header clock, refresh button and last-update footer.

### Data and map

- GTFS and GTFS-RT parsing for 38 realtime providers, 3 static GTFS providers, 12 `kiedyPrzyjedzie` carriers, 2 Time4BUS operators and 6 dedicated city/rail integrations.
- Schedule fallback when realtime coverage is incomplete, including tomorrow's first departures.
- Live GPS vehicle map with positions matched by `vehicle_code`, `trip_id`, then a bounded `route_id` fallback.
- PLK delay binary sensor and a shared PLK API usage sensor with rate limiting.
- Recorder-friendly: large `departures`, `last_update`, `timetable` and `alerts` attributes are marked as unrecorded.

---

## Requirements

- Home Assistant **2025.1.0** or newer (see `hacs.json`).
- HACS only to install updates; manual installation works too.
- Internet access to the selected operator feeds for online mode. Once a stop has been refreshed, its schedule can be replayed offline; map tiles still require network / Home Assistant `map_tiles` (only the Leaflet library is bundled).

---

## Installation

### HACS

1. HACS → Integrations → Custom repositories.
2. Add `https://github.com/toczke/polish-public-transport-card` as **Integration**.
3. Install **Polish Public Transport Card**.
4. Restart Home Assistant.

### Manual

```bash
cp -r custom_components/mzkzg_transport/ /config/custom_components/
```

Restart Home Assistant after copying the files.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration → Polish Public Transport**.
2. Pick a provider.
3. For small providers, choose a stop from the dropdown or type its ID. For providers with more than 3000 stops, first submit a name/ID search and then pick from the narrowed list.
4. For **PKP/PLK**, enter the API key from [dane.plk-sa.pl](https://dane.plk-sa.pl).
5. Repeat only if you need a **different provider**. Adding another stop of the same provider appends it to the existing hub instead of creating a second config entry.

### Hubs and stops

A hub is created per provider, globally. A second ZTM Gdańsk stop joins the existing `ZTM Gdańsk` hub, and a second PLK station joins the existing PLK hub. The hub entry exposes:

- one **operator device** (the hub),
- one **child device per stop**,
- one **per-stop departures sensor** per stop,
- one **merged sensor** when the hub has more than one stop (e.g. `sensor.ztm_gdansk_odjazdy`),
- PLK delay binary sensors per station and a shared `sensor.plk_api_usage` for PLK.

### Options

Open the hub entry → **Configure**. The menu contains:

- **Settings** — destination/route filters, highlight mode, hide-terminus, realtime-only, sleep mode, 100% offline mode, Łódź fallback minimum and kiedyPrzyjedzie timetable lines where applicable.
- **Add stop** — searchable stop picker; for providers above 50 stops the form searches first and then shows a select.
- **Remove stop** — removes the stop, its device and its entities. The last stop of a hub cannot be removed.

### 100% offline mode

The stop form and the hub settings include a **100% offline** toggle. Once a stop has been refreshed online at least once, its schedule is stored under `.storage/mzkzg_transport/offline/`; after that the coordinator can replay it without any network call.

- The first successful refresh saves the snapshot automatically.
- Enable the toggle only after that first refresh; the form refuses to enable offline mode when no snapshot exists yet.
- Offline departures are shifted to today, marked `realtime: false`, and expose `offline: true` plus `offline_saved_at` on the sensor.
- If the saved schedule is missing, the sensor stays at `brak` with `offline_missing: true` instead of failing the integration.

### Changed stop IDs

If a feed replaces numeric stop IDs (Lublin did this in November 2026), an old ID cannot be typed in by hand. Add the stop from the searchable picker; the integration stores the current feed ID and keeps working.

### Full-day timetable (kiedyPrzyjedzie)

Set **Timetable lines** in the hub settings to a comma-separated list (e.g. `854, 870`). The per-stop sensor then exposes a `timetable` attribute with `today` and `tomorrow` arrays while the regular `departures` attribute stays short:

```yaml
{{ state_attr('sensor.pks_gdansk_dworzec_odjazdy', 'timetable').today }}
```

Timetable responses are cached for one hour; the cache is capped at 500 entries.

---

## Entities and attributes

| Entity | Example | Notes |
|---|---|---|
| Per-stop departures | `sensor.gdansk_srodmiescie_odjazdy` | State is the next departure ISO timestamp or `brak`. |
| Merged hub departures | `sensor.ztm_gdansk_odjazdy`, `sensor.plk_odjazdy` | Only when the hub has more than one stop. |
| PLK delay | `binary_sensor.gdansk_srodmiescie_opoznienie` | On when any train at the station is delayed. |
| PLK API usage | `sensor.plk_api_usage` | Shared across all PLK stations. |

Common sensor attributes:

- `departures` — list of departure objects for the card,
- `stop_id`, `stop_name`, `provider`, `last_update`,
- `resolved_stop_id` when an old GTFS stop ID was mapped to a new one,
- `alerts` for providers with service alerts (messages matching the stop's lines/name or stop id),
- `alerts_city` for providers with service alerts (all current messages),
- `walking_distance_m` / `walking_time_min` when Home Assistant has a home location and the stop has coordinates,
- `timetable` for kiedyPrzyjedzie providers when configured.

The card consumes the `departures` attribute directly; you normally do not need to template it.

---

## Card configuration

### Adding the card

The card registers itself automatically. In Lovelace: **Add Card → Polish Transport Card**. For YAML mode, add the module resource manually; the integration logs the exact URL on startup (`/polish_transport/polish-transport-card.js?...`).

### YAML options

| Option | Type | Default | Description |
|---|---|---|---|
| `entities` | list | required | Sensor entity IDs (string or object with per-sensor overrides) |
| `display_preset` | string | `standard` | `standard` / `compact` / `minimal` / `native` / `e_ink` |
| `view_mode` | string | `mixed` | `mixed` (merged timeline) / `tabs` (per-stop) / `grouped` (by line) |
| `columns` | int | `1` | `1`, `2` or `3` |
| `refresh_interval` | int | `60` | Card refresh interval in seconds (5–600) |
| `header_style` | string | `provider` | `provider`, `theme` or `custom` |
| `header_color` | string | — | Header colour for `header_style: custom` |
| `show_header` | bool | `true` | Show the header |
| `show_clock` | bool | `false` | Show the current time in the header |
| `show_refresh` | bool | `false` | Show a manual refresh button |
| `max_departures` | int | `10` | Maximum rows per sensor (1–100) |
| `min_departures` | int | `0` | Skeleton rows used before data arrives |
| `time_format` | string | `auto` | `auto` / `24h` / `12h` |
| `show_delays` | bool | `true` | Show realtime delay badges |
| `show_countdown` | bool | `true` | Show minutes until departure |
| `show_vehicle` | bool | `true` | Show vehicle number chips |
| `show_platform` | bool | `true` | Show platform/stand/track |
| `show_accessibility` | bool | `true` | Show accessibility icons |
| `show_alerts` | bool | `true` | Show provider service alerts above the rows |
| `alerts_scope` | string | `matching` | `matching` (line/stop) or `city` (all provider alerts) |
| `show_bike` | bool | `true` | Show the bike icon when allowed |
| `show_wheelchair` | bool | `true` | Show the wheelchair icon |
| `show_ac` | bool | `true` | Show the air-conditioning icon |
| `show_ticket_machine` | bool | `true` | Show the ticket-machine icon |
| `show_stop_name` | bool | `false` | Show the stop name on merged rows |
| `show_footer` | bool | `true` | Show the footer |
| `show_last_update` | bool | `true` | Show last update time in the footer |
| `filter_routes` | list | — | Include only these routes |
| `exclude_routes` | list | — | Hide these routes |
| `destination_filter` | list | — | Include destinations containing these strings |
| `exclude_destinations` | list | — | Hide destinations containing these strings |
| `filter_vehicle_types` | list | — | `bus`, `tram`, `train` |
| `filter_providers` | list | — | Include only these provider keys |
| `filter_platform` | string | — | Include only this platform |
| `filter_track` | string | — | Include only this track |
| `highlight_mode` | bool | `false` | Dim filtered routes instead of hiding them |
| `hide_terminus` | bool | `true` | Hide departures ending at this stop |
| `hide_cancelled` | bool | `false` | Hide cancelled departures |
| `realtime_only` | bool | `false` | Show only realtime departures |
| `hide_departed` | bool | `true` | Hide rows after departure time + grace |
| `departed_grace_minutes` | int | `1` | Minutes a departed row stays visible |
| `max_minutes` | int | `0` | Limit to departures within N minutes (`0` = no limit) |
| `only_low_floor` | bool | `false` | Only low-floor vehicles |
| `only_bike` | bool | `false` | Only vehicles with bike space |
| `only_ac` | bool | `false` | Only air-conditioned vehicles |
| `only_ticket_machine` | bool | `false` | Only vehicles with a ticket machine |
| `tap_action` | object | `more-info` | Row tap action |
| `hold_action` | object | `none` | Row hold action |
| `double_tap_action` | object | `none` | Row double-tap action |

Filters and `max_departures` can be overridden per sensor. The editor exposes a global form and a per-sensor override form (stop-name labels, override reset and row ordering included).

### Per-sensor overrides

```yaml
type: custom:polish-transport-card
entities:
  - entity: sensor.gdansk_srodmiescie_odjazdy
    filter_routes: ["2", "8"]
    exclude_routes: ["N1"]
    destination_filter: ["Wrzeszcz"]
    max_departures: 40
  - entity: sensor.ztm_gdansk_odjazdy
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

### Presets

- `standard` — full card with provider-coloured header.
- `compact` — denser rows, fewer secondary details.
- `minimal` — minimal header/footer and metadata.
- `native` — Home Assistant-native look and typography.
- `e_ink` — high-contrast, animation-free layout for e-paper.

---

## Supported operators

The provider picker is generated from code; the current list contains **61 entries**:

### Dedicated city / rail integrations (6)

ZTM Gdańsk, ZKM Gdynia, MZK Wejherowo, MPK Łódź, ZTP Kraków, Polskie Linie Kolejowe (PKP, SKM, PR, IC).

### GTFS / GTFS-RT (38)

ZTM Poznań, ZTM Lublin, MPK Kielce, MZDiK Radom, MPK Częstochowa, ZKM Elbląg, MZK Gorzów Wlkp., PGK Suwałki, MZK Przemyśl, ZTZ Rybnik, MZK Kutno, MPK Legnica, ZTM GZM (Katowice), ZDiTM Szczecin, ZTM Warszawa, MZK Ełk, WKD, BKM Białystok, ZDZiT Olsztyn, MZK Opole, ZTM Rzeszów, MZK Toruń, MPK Wrocław, MKS Mielec, MZK Oświęcim, MPK Radomsko, MZK Leszno, KA Świnoujście, ZKM Wałbrzych, MPK Tarnów, MZK Starachowice, MPK Siedlce, KM Płock, MZK Piła, MKS Krosno, MZK Koszalin, MZK Konin, MZK Kalisz.

### Static GTFS only (3)

ZDMiKP Bydgoszcz, KM Kołobrzeg, MZK Ostrołęka.

### kiedyPrzyjedzie (12)

PKS Gdańsk, Albatros, Przewozy Autobusowe GRYF, Nord Express, PKS Gdynia, Miejski Zakład Komunikacji w Malborku, PKS Słupsk, MZK Starogard Gdański, PKS Starogard Gdański, MZK Bielsko-Biała, Powiat Człuchowski, Gmina Czernica.

### Time4BUS (2)

Bytów, Tczew.

Realtime delays, vehicle positions and map availability depend on the upstream feed. A row without a position simply has no map action.

### Provider capabilities

Legend: **RT** realtime departures · **GPS** live vehicle positions/map · **Alerts** provider service alerts · **Wheelchair/Bike/AC** vehicle amenities. ✅ available · — not exposed · `✅*` depends on the upstream feed data.

<!-- provider-capabilities:start -->
| Provider | Alerts | RT | GPS | Wheelchair | Bike | AC |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| ZTM Gdańsk | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ZKM Gdynia | — | ✅ | — | ✅ | ✅ | ✅ |
| MZK Wejherowo | — | — | — | — | — | — |
| Polskie Linie Kolejowe (PKP, SKM, PR, IC) | — | ✅ | — | — | — | — |
| PKS Gdańsk Sp. z o.o. | — | ✅ | — | ✅* | ✅* | ✅* |
| Albatros | — | ✅ | — | ✅* | ✅* | ✅* |
| Przewozy Autobusowe GRYF | — | ✅ | — | ✅* | ✅* | ✅* |
| Nord Express | — | ✅ | — | ✅* | ✅* | ✅* |
| PKS Gdynia S.A. | — | ✅ | — | ✅* | ✅* | ✅* |
| Miejski Zakład Komunikacji w Malborku | — | ✅ | — | ✅* | ✅* | ✅* |
| PKS Słupsk S.A. | — | ✅ | — | ✅* | ✅* | ✅* |
| MZK Starogard Gdański | — | ✅ | — | ✅* | ✅* | ✅* |
| PKS Starogard Gdański S.A. | — | ✅ | — | ✅* | ✅* | ✅* |
| MZK Bielsko-Biała | — | ✅ | — | ✅* | ✅* | ✅* |
| Bytów | — | ✅ | — | ✅* | — | ✅* |
| Powiat Człuchowski | — | ✅ | — | ✅* | ✅* | ✅* |
| Gmina Czernica | — | ✅ | — | ✅* | ✅* | ✅* |
| Tczew (Time4BUS) | — | ✅ | — | ✅* | — | ✅* |
| MPK Łódź | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ZTM Poznań | — | ✅ | ✅ | ✅* | ✅* | ✅* |
| ZTM Lublin | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Kielce | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZDiK Radom | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Częstochowa | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZKM Elbląg | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Gorzów Wlkp. | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| PGK Suwałki | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Przemyśl | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZTZ Rybnik | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Kutno | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Legnica | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZTM GZM (Katowice) | — | ✅ | ✅ | ✅* | ✅* | — |
| ZTP Kraków | ✅ | ✅ | ✅ | — | — | — |
| ZDiTM Szczecin | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZTM Warszawa | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Ełk | — | ✅ | ✅ | ✅* | ✅* | — |
| WKD | — | ✅ | — | ✅* | ✅* | — |
| BKM Białystok | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZDZiT Olsztyn | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Opole | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZTM Rzeszów | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Toruń | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Wrocław | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZDMiKP Bydgoszcz | — | — | — | — | — | — |
| MKS Mielec | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Oświęcim | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Radomsko | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| KM Kołobrzeg | — | — | — | — | — | — |
| MZK Ostrołęka | — | — | — | — | — | — |
| MZK Leszno | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| KA Świnoujście | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| ZKM Wałbrzych | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Tarnów | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Starachowice | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MPK Siedlce | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| KM Płock | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Piła | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MKS Krosno | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Koszalin | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Konin | ✅ | ✅ | ✅ | ✅* | ✅* | — |
| MZK Kalisz | ✅ | ✅ | ✅ | ✅* | ✅* | — |
<!-- provider-capabilities:end -->

---

## Data sources and caching

| Source | Used by |
|---|---|
| Official city APIs / GTFS-RT | Gdańsk, Gdynia, Łódź, Poznań, GZM, Szczecin, Warszawa, Ełk, WKD, Kraków |
| `api.zbiorkom.live` api6-open | Lublin, Kielce, Radom, Częstochowa, Elbląg, Gorzów, Suwałki, Przemyśl, Rybnik, Kutno, Legnica, Białystok, Olsztyn, Opole, Rzeszów, Toruń, Wrocław, Mielec, Oświęcim, Radomsko, Leszno, Świnoujście, Wałbrzych, Tarnów, Starachowice, Siedlce, Płock, Piła, Krosno, Koszalin, Konin, Kalisz |
| `mkuran.pl` | Warszawa, Ełk, WKD, Bydgoszcz |
| `kiedyPrzyjedzie.pl` | 12 regional carriers |
| Time4BUS | Bytów, Tczew |
| PLK OpenData | PKP / SKM / PolRegio / IC |
| Static GTFS | Wejherowo, Bydgoszcz, Kołobrzeg, Ostrołęka |

Caching and memory behaviour:

- Parsed GTFS is kept in memory per provider/day; the raw zip is released once all stops of the hub have been extracted.
- GTFS-RT archives are cached on disk as `polish_transport_gtfs_<provider>.zip` in the Home Assistant config directory; Wejherowo uses `.gtfs_cache/wejherowo.zip`, Łódź uses `<config>/mzkzg_transport/lodz_gtfs.zip`.
- Vehicle positions are cached for 30 seconds; vehicle dictionaries for one hour; ZTM Gdańsk fleet data for one week.
- `kiedyPrzyjedzie` timetables are cached for one hour and capped at 500 entries.
- `departures`, `last_update`, `timetable` and `alerts` are excluded from recorder history.

### Service alerts

Alerts are fetched from the best source each provider exposes:

- **ZTM Gdańsk** — the `ztm.gda.pl/komunikaty` alert ticker plus `bsk_rss.xml`
  (line and stop-name matching). The ticker is needed because the RSS feed can
  lag behind fresh emergency messages.
- **api6-open cities** — GTFS-RT `serviceAlerts` (e.g. Lublin, Poznań, GZM, Kraków, Wrocław, Białystok and the other api6 feeds),
- **Warszawa** — `mkuran.pl/gtfs/warsaw/alerts.pb`,
- **Szczecin** — `gtfs-rt-alerts.pb`,
- **Łódź** — official `alerts.bin`.

GTFS-RT alerts are matched by informed route id, informed stop id or general
operator scope. Feeds without an alert endpoint (for example PLK or ZKM Gdynia)
simply expose no alerts.

- `alerts_scope: matching` (default) shows only messages for this stop/line,
- `alerts_scope: city` shows every current alert on the card,
- `show_alerts: false` hides the header alert icon and popup entirely.

When alerts exist, the header shows a warning triangle with the message count.
Clicking it opens a popup with the full messages; clicking the backdrop or the
close button dismisses it. No icon is rendered when the list is empty.

The source is cached for two minutes and the `alerts` / `alerts_city` attributes
are excluded from recorder history.

`refresh_gtfs` service forces a GTFS cache refresh:

```yaml
service: mzkzg_transport.refresh_gtfs
data:
  provider: gtfsrt_poznan
```

Leave `provider` empty to clear all providers.

---

## Live vehicle map

When a departure has GPS coordinates, clicking the row opens a modal Leaflet map. The vehicle marker refreshes every 30 seconds while the map is open.

- Leaflet 1.9.4 and its CSS are bundled under `custom_components/mzkzg_transport/www/leaflet/` and loaded lazily from `/polish_transport/leaflet/`.
- Tiles use OpenStreetMap, through Home Assistant's `map_tiles` proxy on HA 2026.9+ (direct OSM otherwise).
- Positions are matched by `vehicle_code`, then `trip_id`, then a bounded `route_id` fallback (one departure per vehicle).
- The map takes precedence over `tap_action`; hold and double-tap actions remain available.
- Pressing Escape, clicking the backdrop or the close button restores focus to the page.

The map needs network access for tiles. Only the Leaflet library itself is offline.

---

## Performance and memory

The 2.0.x line includes memory-focused changes:

- raw GTFS archives are released after the hub stops are parsed,
- tomorrow's fallback schedule is precomputed in one pass before the archive is released,
- route-position fallback assigns at most one departure per vehicle,
- long-lived caches are pruned and capped,
- the merged hub sensor caches its sorted departures between coordinator updates,
- repeated card/map lifecycles are covered by a Playwright heap test.

See [docs/performance.md](docs/performance.md) for the test methodology and measured results.

---

## Migration to 2.0

1. Update through HACS or replace the integration files.
2. Restart Home Assistant. The first start merges entries of the same provider into one hub, renames entities/devices and removes duplicates.
3. Update dashboards and automations that still reference old `mzkzg_*` entity IDs.
4. Keep a backup of `/config/.storage/` if you have custom automations.

The migration is idempotent and repairs entities left behind by an interrupted run. The integration domain remains `mzkzg_transport` internally so Home Assistant can load old config entries; it is not used in entity IDs or device names.

---

## Testing and development

```bash
pip install -r requirements_test.txt
pytest -q                 # includes a 60% coverage gate

npm ci
npm run lint
npm run build
npx playwright test
```

The Python suite covers providers, GTFS/GTFS-RT parsing, migration, options flow, sensors, device links, caches and memory bounds. The Playwright suite covers the card, editor, maps and repeated card/map lifecycles.

Development from 2.0.0 onward is driven by **issues and pull requests**. Please include the provider, stop ID/entity ID and a sample of the raw response when reporting data problems.

---

## License

MIT — see [LICENSE](LICENSE).
