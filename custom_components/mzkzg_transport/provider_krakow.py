"""Kraków provider via zbiorkom.live open data API (api6-open)."""

import asyncio
import logging
import re
import time
from datetime import datetime
from urllib.parse import quote

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .const import CONF_STOP_ID, CONF_STOPS, DOMAIN
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)

ZBIORKOM_API = "https://api.zbiorkom.live/api6-open/krakow"
# City-wide box (lon/lat) used until the stop list is loaded; afterwards it is derived from
# the stop coordinates. One shared snapshot serves every stop
DEFAULT_BBOX = "19.55,49.88,20.38,50.27"
BBOX_MARGIN = 0.02
STOPS_TTL = 24 * 3600
# A configured id missing from the stop list triggers a refresh once the list is older than this
STOPS_MISS_REFRESH = 3600
STOPS_RETRY_AFTER = 300
POSITIONS_TTL = 20
POSITIONS_RETRY_AFTER = 60
# A brigade's vehicle is only shown for its next pass by the stop, and only if that pass is
# this close; later trips of the same brigade would otherwise show where the bus is now
BRIGADE_MATCH_HORIZON_MS = 90 * 60 * 1000


async def fetch(coord: "MzkzgTransportCoordinator") -> dict:
    """Fetch departures for a Kraków stop."""
    session = await coord._get_session()
    now = dt_util.now()
    now_ms = now.timestamp() * 1000

    stops = await _get_stops(coord.hass, session)
    stop_id = _lookup(stops, coord.stop_id)
    if stop_id is None:
        # Possibly added after the cached list was built
        stops = await _get_stops(coord.hass, session, max_age=STOPS_MISS_REFRESH)
        stop_id = _lookup(stops, coord.stop_id)
    if stop_id is None:
        # Stop list unavailable or without this id: ask for it directly (an unknown id 404s)
        stop_id, stop_name = coord.stop_id, None
    else:
        stop_name, code = stops["by_id"][stop_id]
        if not coord.stop_name:
            coord.stop_name = f"{stop_name} {code}".strip()
        if stop_id != coord.stop_id:
            try:
                _switch_stop_id(coord, stop_id)
            except Exception:  # the old id keeps being resolved on every update
                _LOGGER.warning("Kraków: could not switch stop %s to %s", coord.stop_id, stop_id, exc_info=True)

    url =f"{ZBIORKOM_API}/stops/{quote(stop_id, safe='')}?limit=20"
    try:
        data = await fetch_with_retry(session, url)
    except Exception as err:
        _LOGGER.debug("Kraków zbiorkom fetch failed: %s", err)
        raise

    raw_deps = data.get("departures") if isinstance(data, dict) else None
    if not isinstance(raw_deps, list):
        return _empty(coord, now)

    departures = []
    for d in raw_deps:
        if not isinstance(d, dict):
            continue
        trip = d.get("trip") or {}
        route_info = trip.get("route") or {}
        scheduled_ms = d.get("scheduledDeparture")
        if not isinstance(scheduled_ms, (int, float)):
            continue

        delay_ms = d.get("delay") if isinstance(d.get("delay"), (int, float)) else 0
        estimated_ms = scheduled_ms + delay_ms
        # Epoch math: aware datetime +/- and same-zone comparisons are wall-clock, off by an hour around DST
        if estimated_ms < now_ms - 60_000:
            continue

        departures.append({
            "route": str(route_info.get("name") or route_info.get("id") or "?"),
            "headsign": trip.get("headsign") or "—",
            "estimated_time": datetime.fromtimestamp(estimated_ms / 1000, tz=now.tzinfo).isoformat(),
            "theoretical_time": datetime.fromtimestamp(scheduled_ms / 1000, tz=now.tzinfo).isoformat(),
            "delay_seconds": int(delay_ms / 1000),
            "realtime": bool(d.get("isRealtime")),
            "cancelled": bool(d.get("isCancelled")),
            # GTFS route_type: 0 = tram, 3 = bus
            "vehicle_type": "tram" if route_info.get("type") == 0 else "bus",
            "provider": coord.provider,
            "_brigade": trip.get("brigade") or "",
            "_scheduled_ms": scheduled_ms,
            "_estimated_ms": estimated_ms,
        })

    # Only departures within the brigade horizon can be matched (stop/time matches are nearer still)
    if any(d["_scheduled_ms"] - now_ms <= BRIGADE_MATCH_HORIZON_MS for d in departures):
        positions = await _get_positions(coord.hass, session, stops.get("bbox", DEFAULT_BBOX))
        try:
            _enrich_positions(departures, positions, stop_name, now_ms)
        except Exception as err:  # a malformed snapshot must not cost the departures
            _LOGGER.debug("Kraków vehicle matching failed: %s", err)

    # Sort by epoch, not by ISO string: the UTC offset changes inside the DST fall-back hour
    departures.sort(key=lambda x: x["_estimated_ms"])
    for d in departures:
        for key in ("_brigade", "_scheduled_ms", "_estimated_ms"):
            d.pop(key, None)

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}",
        "provider": coord.provider,
        "departures": departures[:20],
        "last_update": now.isoformat(),
    }


def _empty(coord, now):
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}",
        "provider": coord.provider,
        "departures": [],
        "last_update": now.isoformat(),
    }


def _legacy_key(stop_id: str) -> str:
    """Map an api6 stop id or a pre-api6 slug to a common key.

    api6 ids are "<slug><code>-<suffix>" (e.g. "bonarka-ska02-xruaf"); entries created
    before api6 store "<slug><code>" with every non-alphanumeric run turned into "-"
    (so "czerwone-maki-p+r01-vrfpw" was "czerwone-maki-p-r01").
    """
    return re.sub(r"[^a-z0-9]+", "-", stop_id.lower()).strip("-")


def _parse_stops(data) -> dict | None:
    """Index a /stops payload: api6 id → (name, code), legacy key → api6 id, and a box around all stops."""
    rows = data.get("stops") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return None
    by_id, by_legacy, ambiguous, lons, lats = {}, {}, set(), [], []
    for row in rows:
        if not isinstance(row, list) or len(row) < 4 or not isinstance(row[0], str) or not row[0]:
            continue
        stop_id = row[0]
        by_id[stop_id] = (str(row[2] or ""), str(row[3] or ""))
        key = _legacy_key(stop_id.rsplit("-", 1)[0])
        if key in by_legacy:
            ambiguous.add(key)
        by_legacy[key] = stop_id
        point = row[4] if len(row) > 4 else None
        if isinstance(point, list) and len(point) >= 2 and all(isinstance(c, (int, float)) for c in point[:2]):
            lons.append(point[0])
            lats.append(point[1])
    if not by_id:
        return None
    for key in ambiguous:
        del by_legacy[key]
    bbox = (
        f"{min(lons) - BBOX_MARGIN:.3f},{min(lats) - BBOX_MARGIN:.3f},"
        f"{max(lons) + BBOX_MARGIN:.3f},{max(lats) + BBOX_MARGIN:.3f}"
    ) if lons else DEFAULT_BBOX
    return {"by_id": by_id, "by_legacy": by_legacy, "bbox": bbox}


async def _get_stops(hass, session, max_age: float = STOPS_TTL) -> dict:
    """Return the shared api6 stop index, refreshing it when older than max_age.

    Never raises: when the list can't be loaded the last good index (or none) is returned
    and the download is not retried for STOPS_RETRY_AFTER s, so an outage doesn't hold
    every stop's update behind the lock.
    """
    cache = hass.data[DOMAIN].setdefault("_krakow_meta", {})
    lock = cache.setdefault("lock", asyncio.Lock())
    async with lock:
        now = time.monotonic()
        if ("by_id" in cache and now - cache["ts"] < max_age) or now < cache.get("retry_at", 0):
            return cache
        data = None
        try:
            data = await fetch_with_retry(session, f"{ZBIORKOM_API}/stops", timeout=30)
        except Exception as err:
            reason = err
        else:
            reason = "unexpected payload"
        index = _parse_stops(data)
        if index is None:
            # With a stale index departures still work, so only a missing one is worth a warning
            _LOGGER.log(
                logging.DEBUG if "by_id" in cache else logging.WARNING,
                "Kraków stop list unavailable (%s), retrying in %d s", reason, STOPS_RETRY_AFTER,
            )
            cache["retry_at"] = time.monotonic() + STOPS_RETRY_AFTER
            return cache
        cache.update(index, ts=time.monotonic())
        return cache


def _lookup(stops: dict, stop_id: str) -> str | None:
    """Return the api6 id for a configured id: an api6 id, a pre-api6 slug, or an api6 id whose suffix changed."""
    if stop_id in stops.get("by_id", {}):
        return stop_id
    by_legacy = stops.get("by_legacy", {})
    return by_legacy.get(_legacy_key(stop_id)) or by_legacy.get(_legacy_key(stop_id.rsplit("-", 1)[0]))


def _switch_stop_id(coord, new_id: str) -> None:
    """Store the api6 id in place of a pre-api6 one, carrying the stop's entities and device over.

    Runs on the first update that resolves the old id, normally the setup refresh, before the
    entities are created, so they come up under the new id with their entity ids and history.
    Entities already running keep working until the next restart.
    """
    entry = coord.config_entry
    if entry is None:
        return
    hass, old_id = coord.hass, coord.stop_id
    old_key, new_key = f"{coord.provider}_{old_id}", f"{coord.provider}_{new_id}"
    ent_reg, dev_reg = er.async_get(hass), dr.async_get(hass)
    # Already set up under the api6 id (stop added again from the new picker): leave this one alone
    if any(
        ent_reg.async_get_entity_id(platform, DOMAIN, f"{DOMAIN}_{new_key}{suffix}")
        for platform, suffix in (("sensor", ""), ("binary_sensor", "_delay"))
    ):
        return

    for entity in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        for suffix in ("", "_delay"):
            if entity.unique_id == f"{DOMAIN}_{old_key}{suffix}":
                ent_reg.async_update_entity(entity.entity_id, new_unique_id=f"{DOMAIN}_{new_key}{suffix}")
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, old_key) in device.identifiers:
            dev_reg.async_update_device(
                device.id, new_identifiers=device.identifiers - {(DOMAIN, old_key)} | {(DOMAIN, new_key)}
            )

    data = dict(entry.data)
    if data.get(CONF_STOP_ID) == old_id:
        data[CONF_STOP_ID] = new_id
    if data.get(CONF_STOPS):
        data[CONF_STOPS] = [{**s, "stop_id": new_id} if s.get("stop_id") == old_id else s for s in data[CONF_STOPS]]
    unique_id = entry.unique_id
    if unique_id == old_key and not any(e.unique_id == new_key for e in hass.config_entries.async_entries(DOMAIN)):
        unique_id = new_key
    hass.config_entries.async_update_entry(entry, data=data, unique_id=unique_id)
    coord.stop_id = new_id
    _LOGGER.info("Kraków: stop %s switched to zbiorkom.live api6 id %s", old_id, new_id)


async def _get_positions(hass, session, bbox: str) -> list:
    """Return the shared city-wide vehicle snapshot (refetched at most every POSITIONS_TTL s).

    A failed download yields no positions and is not retried for POSITIONS_RETRY_AFTER s.
    """
    cache = hass.data[DOMAIN].setdefault("_krakow_vehicles", {})
    lock = cache.setdefault("lock", asyncio.Lock())
    async with lock:
        if cache.get("bbox") == bbox and time.monotonic() < cache.get("next_fetch", 0):
            return cache["positions"]
        try:
            data = await fetch_with_retry(session, f"{ZBIORKOM_API}/positions/{bbox}", timeout=10)
        except Exception as err:
            _LOGGER.debug("Kraków positions fetch failed: %s", err)
            cache.update(positions=[], bbox=bbox, next_fetch=time.monotonic() + POSITIONS_RETRY_AFTER)
            return []
        positions = data.get("positions") if isinstance(data, dict) else None
        cache.update(
            positions=positions if isinstance(positions, list) else [],
            bbox=bbox,
            next_fetch=time.monotonic() + POSITIONS_TTL,
        )
        return cache["positions"]


def _norm(text) -> str:
    return text.strip().lower() if isinstance(text, str) else ""


def _unique_index(pairs) -> dict:
    """Index (key, vehicle) pairs, dropping keys claimed by more than one vehicle."""
    index, ambiguous = {}, set()
    for key, p in pairs:
        if index.setdefault(key, p) is not p:
            ambiguous.add(key)
    for key in ambiguous:
        del index[key]
    return index


def _enrich_positions(departures: list, positions: list, stop_name: str | None, now_ms: float) -> None:
    """Attach vehicle position/code to departures.

    A vehicle matches a departure when it runs the same route and either lists this
    stop among its upcoming stops at the departure's scheduled time with the same
    headsign (works for trams, which have no brigade, but only within ~3 stops), or has
    the same brigade (buses). Keys claimed by several vehicles match none of them.
    Each vehicle is attached to at most one departure: its earliest one at this stop.
    """
    if not positions:
        return
    base_name = _norm(stop_name)
    vehicles = [
        p for p in positions
        if isinstance(p, dict) and isinstance(p.get("location"), list) and len(p["location"]) >= 2
    ]
    by_stop_time = _unique_index(
        ((str(p.get("routeName") or ""), _norm(p.get("headsign")), s.get("scheduledDeparture")), p)
        for p in vehicles
        for s in p.get("upcomingStops") or []
        if base_name and isinstance(s, dict) and _norm(s.get("name")) == base_name
    )
    by_brigade = _unique_index(
        ((str(p.get("routeName") or ""), p["brigade"]), p) for p in vehicles if p.get("brigade")
    )

    used = set()
    for d in sorted(departures, key=lambda x: x["_scheduled_ms"]):
        p = by_stop_time.get((d["route"], _norm(d["headsign"]), d["_scheduled_ms"]))
        if p is None and d["_brigade"] and d["_scheduled_ms"] - now_ms <= BRIGADE_MATCH_HORIZON_MS:
            p = by_brigade.get((d["route"], d["_brigade"]))
        if p is None or id(p) in used:
            continue
        used.add(id(p))
        vehicle = p.get("vehicle") if isinstance(p.get("vehicle"), dict) else {}
        d["vehicle_lng"], d["vehicle_lat"] = p["location"][0], p["location"][1]
        if p.get("bearing") is not None:
            d["vehicle_direction"] = p["bearing"]
        if vehicle.get("id"):
            d["vehicle_code"] = vehicle["id"]
        if vehicle.get("model"):
            d["vehicle_model"] = vehicle["model"]
