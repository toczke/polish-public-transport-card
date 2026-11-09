# AGENTS.md

Instructions for AI coding agents and contributors working on **Polish Public Transport Card**.

## Project snapshot

- Home Assistant custom integration plus a Lit/Lovelace card.
- The integration domain is intentionally `mzkzg_transport` for backwards compatibility. User-facing entity IDs and devices use the `polish_transport` prefix.
- One config entry is a **provider hub**; every configured stop gets its own coordinator and sensor.
- Current provider families: dedicated city/rail integrations, GTFS/GTFS-RT cities, static GTFS, `kiedyPrzyjedzie` carriers and Time4BUS.
- Current version: read `custom_components/mzkzg_transport/manifest.json`. It must match `INTEGRATION_VERSION` in `const.py`, `CARD_VERSION` in `src/utils.js`, the README version badge and the git tag.

## Non-negotiables

1. **Never rename the integration domain** `mzkzg_transport` or the entity unique prefix `polish_transport`. Both are required for migration and history.
2. **Do not edit `custom_components/mzkzg_transport/www/polish-transport-card.js` by hand.** Edit `src/*.js`, run `npm run build`, and commit the generated file.
3. **Keep the built card in sync.** CI fails when the committed bundle differs from a fresh build.
4. **Never commit secrets, long-lived HA tokens, `.storage` data or downloaded GTFS archives.**
5. **Keep existing entries working.** `migration.py` is idempotent and must keep healing interrupted 2.0 migrations.
6. **Add tests with behavior changes.** The pytest coverage gate is 60%; do not lower it.
7. **Do not add live-network tests to the default suite.** Mock feeds and protobuf payloads. Network probes belong in `scripts/validate_providers.py`.
8. **Keep the provider capability table generated.** `scripts/provider_capabilities.py` is the source; `tests/test_provider_capabilities.py` checks README.

## Setup

Use Python 3.12 and Node 24 (same as CI).

```bash
python3.12 -m venv .venv312
. .venv312/bin/activate            # Windows: .\.venv312\Scripts\Activate.ps1
pip install -r requirements_test.txt

npm ci
npx playwright install chromium
```

`requirements_test.txt` pins Home Assistant for the test environment. On Windows the interpreter is usually `.\.venv312\Scripts\python.exe`.

## Commands

```bash
# Python tests (includes --cov and the 60% gate)
pytest -q

# Focused tests
pytest tests/test_provider_gtfsrt.py -q
pytest tests/test_offline.py tests/test_coordinator_update.py -q

# Syntax check, as in CI
python -m compileall -q custom_components tests

# Frontend
npm run lint
npm run build          # always commit the rebuilt www/polish-transport-card.js
npx playwright test
npx playwright test tests/e2e/alerts.spec.ts --reporter=line
```

Optional maintenance:

```bash
python scripts/provider_capabilities.py   # regenerate the README matrix
python scripts/validate_providers.py      # live provider probe, not part of pytest
```

## Repository map

| Path | Responsibility |
|---|---|
| `custom_components/mzkzg_transport/__init__.py` | Config-entry setup, coordinator creation, shared caches, card resource registration |
| `coordinator.py` | One coordinator per stop: provider dispatch, sleep mode, offline snapshots/fallback, walking distance, errors |
| `const.py` | Provider IDs, URLs, base URL maps, labels, colours, option keys |
| `config_flow.py` | Hub setup/options flow, stop picker, PLK API key, Łódź groups, offline toggle |
| `config_flow_stops.py` | Provider stop-list loaders (streamed GTFS, PLK pagination, Kraków, Time4BUS… ) |
| `sensor.py` | Per-stop and merged hub sensors; recorder exclusions |
| `binary_sensor.py` | PLK delay/usage sensors |
| `provider_*.py` | Provider-specific fetch implementations |
| `gtfsrt_cities.py` | GTFS-RT city catalogue (URLs, labels, optional alerts/positions/vehicles) |
| `gtfsrt_parser.py` | Shared GTFS/GTFS-RT parsing, stop-time extraction, positions |
| `gtfsrt_alerts.py` | Shared GTFS-RT service-alert fetch/filter/cache |
| `ztm_alerts.py` | ZTM Gdańsk ticker + RSS alerts |
| `offline.py` | Per-stop offline schedule snapshots and replay |
| `migration.py` | 2.0 hub/entity migration and repair |
| `src/` | Card, editor, styles, map and utilities (build source) |
| `custom_components/mzkzg_transport/www/` | Built card and bundled Leaflet (generated) |
| `tests/` | Unit/integration pytest suite |
| `tests/e2e/` | Playwright card/editor/map tests |
| `scripts/` | Provider status, capability matrix, Leaflet copy |
| `docs/performance.md` | Memory/performance methodology and measurements |

## Provider contract

Every `provider_*.fetch(coord)` returns:

```python
{
    "stop_id": coord.stop_id,
    "stop_name": coord.stop_name,
    "provider": coord.provider,
    "departures": [...],
    "last_update": now.isoformat(),
    # optional:
    "alerts": [...],
    "alerts_city": [...],
    "resolved_stop_id": "...",
}
```

Departure rows use fields such as:

```python
{
    "route": "6",
    "headsign": "Jelitkowo",
    "theoretical_time": "...",
    "estimated_time": "...",
    "delay_seconds": 120,
    "realtime": True,
    "vehicle_type": "tram",
    "vehicle_code": "1026",
    "vehicle_lat": 54.1,
    "vehicle_lng": 18.2,
    "bike_allowed": True,
    "wheelchair_accessible": True,
    "air_conditioning": True,
    "provider": coord.provider,
}
```

Rules:

- Always return `theoretical_time` for scheduled fallback rows.
- Set `realtime=False` when the row is schedule-only.
- Use ISO local datetimes consistent with the provider board.
- Optional data (alerts, GPS, amenities) must fail soft; do not break departures for it.
- Use shared helpers (`http_utils.fetch_with_retry`, `gtfsrt_alerts`, `ztm_alerts`, `offline`) instead of duplicating retry/cache logic.
- Do not perform blocking file or archive I/O in the event loop; use `hass.async_add_executor_job` or `asyncio.to_thread`.
- Cache long-lived data in `hass.data[DOMAIN]` and prune it. The coordinator already stores offline snapshots; providers should not create their own parallel snapshot format.

## Adding a provider

1. Add the provider ID and URL in `const.py`.
2. Register it in `PROVIDER_OPTIONS` and `PROVIDER_OPTIONS_SORTED` in `config_flow.py`.
3. Add the stop loader in `config_flow_stops.py` if the provider is not handled by an existing family.
4. Add labels/header colours/badge colours to `const.py` and `src/utils.js`.
5. Add the provider to `README.md` counts and the operator list.
6. Regenerate the provider capability matrix with `python scripts/provider_capabilities.py`.
7. Add tests: URL/catalogue, fetch/parser, and config-flow stop loading.
8. For a `kiedyPrzyjedzie` carrier this is usually const + config flow + utils + README + tests only.
9. For a GTFS-RT city add one `GTFSRT_CITIES` entry and a catalogue test; do not create a new provider module.
10. For alerts use `gtfsrt_alerts.py` or `ztm_alerts.py`; never fetch alert feeds inline in the card.

## Offline mode

- `offline_only` is a **hub-level** option stored in entry options/data and shown in the stop, add-stop and settings forms.
- It must not be enabled without a saved snapshot; the form returns `offline_cache_missing`.
- The coordinator saves the last successful timetable per stop; providers still return normal schedule rows.
- Replayed rows must be shifted to today, `realtime=False`, and expose `offline`, `offline_saved_at`, `offline_missing`.
- Do not add per-provider offline storage; extend `offline.py` instead.

## Frontend/card rules

- Lit components in `src/`; all styles live in `src/styles.js`.
- The card must tolerate older sensors without `alerts_city`, `offline`, `resolved_stop_id`, etc.
- Preserve theme/dark-mode contrast; use CSS variables and `contrastTextColor()` for badges.
- Leaflet and its CSS are bundled under `www/leaflet/` and loaded lazily; never switch back to a CDN.
- If a visual change affects snapshots, update them deliberately and mention it in the PR.

## Testing expectations

- Test the edge case, not only the happy path: empty feeds, stale caches, missing ids, time zones, duplicate trips, off-by-one stop sequences.
- Parser tests should use realistic GTFS CSV/protobuf fixtures.
- Config/options flow tests use `SimpleNamespace` fakes; see `tests/test_config_flow_user.py` and `tests/test_options_flow.py`.
- Offline tests use a temporary config path; see `tests/test_offline.py`.
- E2E tests load the built bundle from `custom_components/mzkzg_transport/www/polish-transport-card.js`.
- Do not make tests depend on live operator APIs or exact current departure counts.
- Run the focused test first, then the full suite before committing.

## Versioning and release

1. Bump `manifest.json`, `INTEGRATION_VERSION` in `const.py`, `CARD_VERSION` in `src/utils.js` and the README version badge together.
2. Move `[Unreleased]` to a dated `## [x.y.z] - YYYY-MM-DD` section in `CHANGELOG.md`.
3. Run `pytest -q`, `npm run lint`, `npm run build`, `npx playwright test`, and verify the rebuilt card is committed.
4. Commit as `chore(release): x.y.z`.
5. Tag `vx.y.z` and push the tag. The release workflow validates the tag against the manifest and publishes `polish-public-transport-card.zip`.
6. Never tag a commit with a stale card bundle or mismatched version.
7. Pull-request CI runs the same checks and builds the HACS archive as an artifact, but never publishes a release; only a pushed `v*` tag does that.
8. A patch release is appropriate for fixes and small features; ask the maintainer before a minor/major jump.

## Pull requests

- Reference the issue and include the provider, stop ID/entity ID, time and a raw feed sample for data bugs.
- Keep changes focused; avoid unrelated refactors.
- Update `CHANGELOG.md` and README when behavior or provider counts change.
- Include tests and state which commands were run.
- Code/comments are English; user-facing strings belong in `strings.json` and both `translations/en.json` and `translations/pl.json`.
- Do not merge with failing CI, a missing screenshot update, or a stale built card.

## Known traps

- `mzkzg_transport` is the technical domain; `polish_transport` is the visible prefix. Do not “clean up” either.
- The provider picker must not render thousands of options; large lists use search-first and a capped selector.
- `departures`, `last_update`, `timetable`, `alerts`, `alerts_city` and offline markers are excluded from recorder history.
- GTFS trip IDs repeat daily; when comparing realtime absolute times, respect `start_date`.
- Release assets are built from tags; changing files after tagging does not update an existing HACS zip.
- `provider-status` deliberately skips GZM from GitHub Actions because port 5443 is blocked there.
- `.zip`, `.storage`, caches, `.venv*` and `node_modules/` are ignored; do not force-add them.
