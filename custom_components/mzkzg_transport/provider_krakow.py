"""Kraków provider via zbiorkom.live open data API (api6-open)."""

import asyncio
import logging
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)

ZBIORKOM_API = "https://api.zbiorkom.live/api6-open/krakow"
# City-wide box (lon/lat) covering ZTP and agglomeration lines; one shared snapshot serves every stop
KRAKOW_BBOX = "19.6,49.85,20.4,50.25"
STOPS_TTL = 24 * 3600
POSITIONS_TTL = 20
# A brigade's vehicle is only shown for its next pass by the stop, and only if that pass is
# this close; later trips of the same brigade would otherwise show where the bus is now
BRIGADE_MATCH_HORIZON_MS = 90 * 60 * 1000


async def fetch(coord: "MzkzgTransportCoordinator") -> dict:
    """Fetch departures for a Kraków stop."""
    session = await coord._get_session()
    now = dt_util.now()

    stop = await _resolve_stop(coord, session)
    if stop is None:
        _LOGGER.warning("Kraków stop %s not found in zbiorkom.live stop list", coord.stop_id)
        return _empty(coord, now)
    stop_id, stop_name, display_name = stop
    if not coord.stop_name:
        coord.stop_name = display_name

    url = f"{ZBIORKOM_API}/stops/{quote(stop_id, safe='')}?limit=20"
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
        scheduled_dt = datetime.fromtimestamp(scheduled_ms / 1000, tz=now.tzinfo)
        estimated_dt = scheduled_dt + timedelta(milliseconds=delay_ms)
        if estimated_dt < now - timedelta(minutes=1):
            continue

        departures.append({
            "route": str(route_info.get("name") or route_info.get("id") or "?"),
            "headsign": trip.get("headsign") or "—",
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": scheduled_dt.isoformat(),
            "delay_seconds": int(delay_ms / 1000),
            "realtime": bool(d.get("isRealtime")),
            "cancelled": bool(d.get("isCancelled")),
            # GTFS route_type: 0 = tram, 3 = bus
            "vehicle_type": "tram" if route_info.get("type") == 0 else "bus",
            "provider": coord.provider,
            "_brigade": trip.get("brigade") or "",
            "_scheduled_ms": scheduled_ms,
        })

    try:
        positions = await _get_positions(coord, session)
    except Exception as err:
        _LOGGER.debug("Kraków positions fetch failed: %s", err)
        positions = []
    _enrich_positions(departures, positions, stop_name, now.timestamp() * 1000)

    for d in departures:
        d.pop("_brigade", None)
        d.pop("_scheduled_ms", None)

    departures.sort(key=lambda x: x.get("estimated_time") or "")
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


async def _get_stops(coord, session) -> dict:
    """Return the cached api6 stop index, refreshing it daily."""
    cache = coord.hass.data[DOMAIN].setdefault("_krakow_meta", {})
    lock = cache.setdefault("lock", asyncio.Lock())
    async with lock:
        if cache.get("by_id") and time.monotonic() - cache.get("ts", 0) < STOPS_TTL:
            return cache
        try:
            data = await fetch_with_retry(session, f"{ZBIORKOM_API}/stops", timeout=60)
        except Exception:
            if cache.get("by_id"):
                return cache  # keep serving the stale index
            raise
        by_id, by_legacy, ambiguous = {}, {}, set()
        for row in data.get("stops", []) if isinstance(data, dict) else []:
            if not isinstance(row, list) or len(row) < 4 or not row[0]:
                continue
            stop_id, name, code = row[0], row[2] or "", row[3] or ""
            by_id[stop_id] = (name, code)
            key = _legacy_key(stop_id.rsplit("-", 1)[0])
            if key in by_legacy:
                ambiguous.add(key)
            by_legacy[key] = stop_id
        for key in ambiguous:
            by_legacy.pop(key, None)
        if by_id:
            cache.update(by_id=by_id, by_legacy=by_legacy, ts=time.monotonic())
        return cache


async def _resolve_stop(coord, session) -> tuple[str, str, str] | None:
    """Resolve the configured stop id (api6 id or pre-api6 slug) to (api6 id, name, display name)."""
    stops = await _get_stops(coord, session)
    by_id = stops.get("by_id", {})
    by_legacy = stops.get("by_legacy", {})
    stop_id = coord.stop_id
    if stop_id not in by_id:
        # Pre-api6 slug, or an api6 id whose suffix has since changed
        stop_id = by_legacy.get(_legacy_key(stop_id)) or by_legacy.get(
            _legacy_key(stop_id.rsplit("-", 1)[0])
        )
    if not stop_id or stop_id not in by_id:
        return None
    name, code = by_id[stop_id]
    return stop_id, name, f"{name} {code}".strip()


async def _get_positions(coord, session) -> list:
    """Return the shared city-wide vehicle snapshot (refetched at most every POSITIONS_TTL s)."""
    cache = coord.hass.data[DOMAIN].setdefault("_krakow_vehicles", {})
    lock = cache.setdefault("lock", asyncio.Lock())
    async with lock:
        if "positions" in cache and time.monotonic() - cache.get("ts", 0) < POSITIONS_TTL:
            return cache["positions"]
        data = await fetch_with_retry(session, f"{ZBIORKOM_API}/positions/{KRAKOW_BBOX}")
        positions = data.get("positions") if isinstance(data, dict) else None
        cache.update(positions=positions if isinstance(positions, list) else [], ts=time.monotonic())
        return cache["positions"]


def _enrich_positions(departures: list, positions: list, stop_name: str, now_ms: float) -> None:
    """Attach vehicle position/code to departures.

    A vehicle matches a departure when it runs the same route and either lists this
    stop among its upcoming stops at the departure's scheduled time (works for trams,
    which have no brigade, but only within ~3 stops), or has the same brigade (buses).
    Each vehicle is attached to at most one departure: its earliest one at this stop.
    """
    if not positions:
        return
    base_name = (stop_name or "").strip().lower()

    by_stop_time, by_brigade, dup_brigade = {}, {}, set()
    for p in positions:
        if not isinstance(p, dict) or not isinstance(p.get("location"), list) or len(p["location"]) < 2:
            continue
        route = str(p.get("routeName") or "")
        for s in p.get("upcomingStops") or []:
            if (s.get("name") or "").strip().lower() == base_name:
                by_stop_time[(route, s.get("scheduledDeparture"))] = p
        brigade = p.get("brigade")
        if brigade:
            key = (route, brigade)
            if key in by_brigade:
                dup_brigade.add(key)
            by_brigade[key] = p
    for key in dup_brigade:
        by_brigade.pop(key, None)

    used = set()
    for d in sorted(departures, key=lambda x: x["_scheduled_ms"]):
        p = by_stop_time.get((d["route"], d["_scheduled_ms"]))
        if p is None and d["_brigade"] and d["_scheduled_ms"] - now_ms <= BRIGADE_MATCH_HORIZON_MS:
            p = by_brigade.get((d["route"], d["_brigade"]))
        if p is None or id(p) in used:
            continue
        used.add(id(p))
        vehicle = p.get("vehicle") or {}
        d["vehicle_lng"], d["vehicle_lat"] = p["location"][0], p["location"][1]
        if p.get("bearing") is not None:
            d["vehicle_direction"] = p["bearing"]
        if vehicle.get("id"):
            d["vehicle_code"] = vehicle["id"]
        if vehicle.get("model"):
            d["vehicle_model"] = vehicle["model"]
