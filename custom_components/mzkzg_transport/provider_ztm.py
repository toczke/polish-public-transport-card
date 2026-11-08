"""ZTM Gdańsk provider with GTFS schedule fallback."""

import logging
from datetime import datetime, timedelta, timezone

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN, PROVIDER_ZTM, ZTM_GDANSK_DEPARTURES_URL
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)

ZTM_GDANSK_GPS_URL = "https://ckan2.multimediagdansk.pl/gpsPositions?v=2"

ZTM_GDANSK_GTFS_URL = (
    "https://ckan.multimediagdansk.pl/dataset/"
    "c24aa637-3619-4dc2-a171-a23eec8f2172/resource/"
    "30e783e4-2bec-4a7d-bb22-ee3e3b26ca96/download/gtfsgoogle.zip"
)


async def fetch(coord: "PolishTransportCoordinator") -> dict:
    """Fetch departures from ZTM Gdańsk TRISTAR API with GTFS fallback."""
    session = await coord._get_session()
    url = f"{ZTM_GDANSK_DEPARTURES_URL}?stopId={coord.stop_id}"

    api_deps = []
    now = dt_util.now()
    try:
        data = await fetch_with_retry(session, url)
        fleet = await _get_fleet(coord, session)
        api_deps = _parse_api_departures(data, fleet, now)
    except Exception as exc:
        _LOGGER.debug("ZTM API fetch failed for stop %s: %s", coord.stop_id, exc)

    # Enrich RT departures with vehicle GPS positions
    try:
        positions = await _get_vehicle_positions(coord, session)
        _enrich_with_positions(api_deps, positions)
    except Exception as exc:
        _LOGGER.debug("ZTM GPS positions failed: %s", exc)

    unique = _deduplicate(api_deps)

    try:
        gtfs = await _load_gtfs(coord, session, now)
        if gtfs:
            gtfs_deps = await _get_gtfs_departures(coord, gtfs, coord.stop_id, now)
            seen = set()
            seen_rt = set()
            for d in unique:
                key_time = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
                h = (d.get("headsign") or "").strip()
                seen.add((d.get("route"), h, key_time))
                seen_rt.add((d.get("route"), key_time))
            for d in gtfs_deps:
                key_time = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
                h = (d.get("headsign") or "").strip()
                key = (d.get("route"), h, key_time)
                if key in seen:
                    continue
                if not h and (d.get("route"), key_time) in seen_rt:
                    continue
                seen.add(key)
                unique.append(d)
    except Exception as exc:
        _LOGGER.debug("ZTM GTFS fallback failed: %s", exc)

    unique = _deduplicate(unique)

    unique.sort(key=lambda x: x.get("estimated_time") or "")

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": PROVIDER_ZTM,
        "departures": unique,
        "last_update": now.isoformat(),
    }


def _parse_api_departures(data: dict, fleet: dict, now) -> list:
    """Parse departures from the ZTM API response.

    The ZTM API returns times in UTC without timezone marker.
    We convert them to local time so they match GTFS schedule times.
    """
    def _parse_time(raw: str) -> datetime | None:
        if not raw:
            return None
        if "T" in raw:
            t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return t.astimezone(local_tz)
        if ":" in raw:
            parts = raw.split(":")
            h, m = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            if h >= 24:
                h -= 24
            t = now.replace(hour=h, minute=m, second=s, microsecond=0)
            if (t - now).total_seconds() < -3600:
                t += timedelta(days=1)
            return t
        return None

    departures = []
    local_tz = now.tzinfo or dt_util.DEFAULT_TIME_ZONE
    for d in data.get("departures", []):
        theo = d.get("theoreticalTime")
        est = d.get("estimatedTime")
        if not est and not theo:
            continue

        theo_time = _parse_time(theo)
        est_time = _parse_time(est or theo)

        if est_time and est_time.timestamp() < now.timestamp() - 30:
            continue

        delay_sec = d.get("delayInSeconds") or d.get("delay") or 0
        status = d.get("status", "SCHEDULED")
        vcode = str(d.get("vehicleCode") or "")
        vinfo = fleet.get(vcode, {})
        characteristics = str(vinfo.get("vehicleCharacteristics", "")).lower()
        departures.append({
            "trip_id": d.get("tripId"),
            "route_id_int": d.get("routeId"),
            "route": str(d.get("routeShortName") or d.get("routeId") or "?"),
            "headsign": d.get("headsign") or d.get("tripHeadsign") or "—",
            "estimated_time": est_time.isoformat() if est_time else "",
            "theoretical_time": theo_time.isoformat() if theo_time else (est_time.isoformat() if est_time else ""),
            "delay_seconds": delay_sec,
            "realtime": status == "REALTIME",
            "vehicle_type": _vehicle_type(d.get("routeShortName") or d.get("routeId")),
            "bike_allowed": vinfo.get("bikeHolders", 0) > 0 if vinfo else d.get("bikeAllowed"),
            "wheelchair_accessible": vinfo.get("wheelchairsRamp") if vinfo else d.get("wheelchairAccessible"),
            "air_conditioning": vinfo.get("airConditioning") if vinfo else d.get("airConditioning"),
            "usb": vinfo.get("usb", False),
            "ticket_machine": vinfo.get("ticketMachine", False),
            "vehicle_code": vcode,
            "vehicle_model": vinfo.get("model", ""),
            "vehicle_brand": vinfo.get("brand", ""),
            "vehicle_year": vinfo.get("productionYear"),
            "vehicle_length": vinfo.get("length"),
            "floor_height": vinfo.get("floorHeight", ""),
            "drive_type": vinfo.get("driveType", ""),
            "historic": vinfo.get("historicVehicle", False),
            "articulated": characteristics == "przegubowy",
            "bike_holders": vinfo.get("bikeHolders", 0),
            "seats": vinfo.get("seats"),
            "standing": vinfo.get("standingPlaces"),
            "monitoring": vinfo.get("monitoring", False),
            "voice_announcements": vinfo.get("voiceAnnouncements", False),
            "aed": vinfo.get("aed", False),
            "provider": PROVIDER_ZTM,
        })
    return departures


def _deduplicate(departures: list) -> list:
    """Deduplicate by (route, theoretical_time to minute, headsign), prefer RT.

    Using theoretical_time ensures RT entries with delay still match
    the corresponding schedule entry instead of appearing as separate.
    Entries with empty headsign match any headsign at the same route+time
    (e.g. GTFS data often lacks headsign while API has it).
    Entries with non-empty headsign only match each other.
    """
    seen: dict[tuple, dict] = {}
    seen_rt: dict[tuple, dict] = {}
    for d in departures:
        t = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
        h = (d.get("headsign") or "").strip()
        key = (d.get("route"), t, h)
        key_rt = (d.get("route"), t)

        existing = seen.get(key)
        if existing:
            if d.get("realtime") and not existing.get("realtime"):
                seen[key] = d
            continue

        if not h and key_rt in seen_rt:
            existing_no_hs = seen_rt[key_rt]
            if d.get("realtime") and not existing_no_hs.get("realtime"):
                seen_rt[key_rt] = d
                seen[key] = d
            continue

        seen[key] = d
        seen_rt[key_rt] = d

    return list(seen.values())


async def _load_gtfs(coord, session, now) -> dict | None:
    """Load Gdańsk GTFS data (cached daily in hass.data)."""
    cache = coord.hass.data[DOMAIN].setdefault("_ztm_gtfs_cache", {})
    today = now.strftime("%Y%m%d")
    if cache.get(today):
        return cache[today]

    try:
        async with session.get(
            ZTM_GDANSK_GTFS_URL, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()

        from .gtfsrt_parser import _parse_gtfs_zip
        gtfs = await coord.hass.async_add_executor_job(_parse_gtfs_zip, data)
        cache[today] = gtfs

        for old_key in list(cache.keys()):
            if old_key != today:
                cache.pop(old_key, None)

        return gtfs
    except Exception as exc:
        _LOGGER.debug("ZTM GTFS load failed: %s", exc)
        return None


async def _get_gtfs_departures(coord, gtfs: dict, stop_id: str, now) -> list:
    """Get scheduled departures from GTFS for a given stop."""
    from .gtfsrt_parser import _parse_stop_times_for

    if stop_id not in gtfs.get("stop_times", {}):
        await coord.hass.async_add_executor_job(_parse_stop_times_for, gtfs, stop_id)

    stop_times = gtfs.get("stop_times", {}).get(stop_id, [])
    departures = []

    for st in stop_times:
        trip_id = st["trip_id"]
        route_id = st["route_id"]
        route_name = gtfs.get("routes", {}).get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or gtfs.get("trips", {}).get(trip_id, {}).get("headsign", "")

        h, m, s = st["departure_time"]
        dep_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
        if dep_dt < now - timedelta(minutes=1):
            continue

        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": dep_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": 0,
            "realtime": False,
            "vehicle_type": _vehicle_type(route_name),
            "provider": PROVIDER_ZTM,
        })

    return departures


async def _get_fleet(coord, session: aiohttp.ClientSession) -> dict:
    """Get ZTM vehicle fleet data (cached weekly in hass.data)."""
    cache = coord.hass.data[DOMAIN].setdefault("_ztm_fleet", {})
    ts = cache.get("ts")
    if cache.get("data") and ts and (dt_util.now().timestamp() - ts < 604800):
        return cache["data"]
    try:
        async with session.get(
            "https://mapa.ztm.gda.pl/d/otwarte-dane/ztm/baza-pojazdow.json?v=2",
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status == 200:
                raw = await resp.json()
                fleet = {str(v["vehicleCode"]): v for v in raw.get("results", []) if v.get("vehicleCode")}
                cache["data"] = fleet
                cache["ts"] = dt_util.now().timestamp()
                return fleet
    except Exception:
        _LOGGER.debug("Could not load ZTM fleet data")
    return cache.get("data", {})


async def _get_vehicle_positions(coord, session: aiohttp.ClientSession) -> dict:
    """Get GPS positions of all ZTM vehicles (cached ~30s)."""
    cache = coord.hass.data[DOMAIN].setdefault("_ztm_gps", {})
    ts = cache.get("ts")
    if cache.get("data") and ts and (dt_util.now().timestamp() - ts < 30):
        return cache["data"]
    try:
        async with session.get(
            ZTM_GDANSK_GPS_URL, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                raw = await resp.json()
                vehicles = raw.get("vehicles", [])
                by_code = {}
                for v in vehicles:
                    vc = str(v.get("vehicleCode") or "")
                    if vc:
                        by_code[vc] = {
                            "lat": v.get("lat"),
                            "lng": v.get("lon"),
                            "speed": v.get("speed"),
                            "direction": v.get("direction"),
                            "generated": v.get("generated"),
                        }
                cache["data"] = by_code
                cache["ts"] = dt_util.now().timestamp()
                return by_code
    except Exception:
        _LOGGER.debug("Could not load ZTM GPS positions")
    return cache.get("data", {})


def _enrich_with_positions(departures: list, positions: dict) -> None:
    """Add vehicle_lat/vehicle_lng to departures with matching vehicle_code."""
    for d in departures:
        vc = d.get("vehicle_code")
        if vc and vc in positions:
            pos = positions[vc]
            d["vehicle_lat"] = pos["lat"]
            d["vehicle_lng"] = pos["lng"]
            d["vehicle_speed"] = pos["speed"]
            d["vehicle_direction"] = pos["direction"]


def _vehicle_type(route_id) -> str:
    """Determine vehicle type for ZTM Gdańsk."""
    s = str(route_id or "")
    n = int(s) if s.isdigit() else None
    if n is not None and n < 100:
        return "tram"
    return "bus"
