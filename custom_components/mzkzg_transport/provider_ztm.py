"""ZTM Gdańsk provider."""

from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN, PROVIDER_ZTM, ZTM_GDANSK_DEPARTURES_URL

_LOGGER = logging.getLogger(__name__)


async def fetch(coord) -> dict:
    """Fetch departures from ZTM Gdańsk TRISTAR API."""
    session = await coord._get_session()
    url = f"{ZTM_GDANSK_DEPARTURES_URL}?stopId={coord.stop_id}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        data = await resp.json()

    fleet = await _get_fleet(coord, session)

    departures = []
    now = dt_util.now()
    for d in data.get("departures", []):
        estimated = d.get("estimatedTime") or d.get("theoreticalTime")
        if not estimated:
            continue
        dep_time = None
        if "T" in estimated:
            dep_time = datetime.fromisoformat(estimated.replace("Z", "+00:00"))
        elif ":" in estimated:
            parts = estimated.split(":")
            h, m = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            if h >= 24:
                h -= 24
            dep_time = now.replace(hour=h, minute=m, second=s, microsecond=0)
            if (dep_time - now).total_seconds() < -3600:
                dep_time += timedelta(days=1)
        if dep_time and dep_time.timestamp() < now.timestamp() - 30:
            continue

        delay_sec = d.get("delayInSeconds") or d.get("delay") or 0
        status = d.get("status", "SCHEDULED")
        vcode = str(d.get("vehicleCode") or "")
        vinfo = fleet.get(vcode, {})
        departures.append({
            "route": str(d.get("routeShortName") or d.get("routeId") or "?"),
            "headsign": d.get("headsign") or d.get("tripHeadsign") or "—",
            "estimated_time": estimated,
            "theoretical_time": d.get("theoreticalTime"),
            "delay_seconds": delay_sec,
            "realtime": status == "REALTIME",
            "vehicle_type": _vehicle_type(d.get("routeShortName") or d.get("routeId")),
            "bike_allowed": vinfo.get("bikeHolders", 0) > 0 if vinfo else d.get("bikeAllowed"),
            "wheelchair_accessible": vinfo.get("wheelchairsRamp") if vinfo else d.get("wheelchairAccessible"),
            "air_conditioning": vinfo.get("airConditioning") if vinfo else d.get("airConditioning"),
            "usb": vinfo.get("usb", False),
            "ticket_machine": vinfo.get("ticketMachine", False),
            "vehicle_code": vcode,
            "provider": PROVIDER_ZTM,
        })

    departures.sort(key=lambda x: x.get("estimated_time") or "")

    # Fallback: if fewer than 10 realtime departures, fill from schedule
    if len(departures) < 10:
        schedule_deps = await _get_schedule_fallback(coord, session, now, departures)
        departures.extend(schedule_deps)
        departures.sort(key=lambda x: x.get("estimated_time") or "")

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": PROVIDER_ZTM,
        "departures": departures,
        "last_update": now.isoformat(),
    }


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


def _vehicle_type(route_id) -> str:
    """Determine vehicle type for ZTM Gdańsk."""
    s = str(route_id or "")
    n = int(s) if s.isdigit() else None
    if n is not None and n < 100:
        return "tram"
    return "bus"


ZTM_STOP_TIMES_URL = "https://ckan2.multimediagdansk.pl/stopTimes"


async def _get_schedule_fallback(coord, session, now, existing_deps) -> list[dict]:
    """Fetch scheduled departures to fill gaps when realtime data is sparse."""
    cache = coord.hass.data[DOMAIN].setdefault("_ztm_schedule", {})
    today = now.strftime("%Y-%m-%d")
    cache_key = f"{coord.stop_id}_{today}"

    # Use cached schedule data for today
    if cache.get(cache_key):
        all_times = cache[cache_key]
    else:
        # Get routes from existing realtime data
        routes = {d["route"] for d in existing_deps}
        if not routes:
            return []

        all_times = []
        for route_id in routes:
            try:
                url = f"{ZTM_STOP_TIMES_URL}?date={today}&routeId={route_id}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

                for st in data.get("stopTimes", []):
                    if str(st.get("stopId")) != str(coord.stop_id):
                        continue
                    dep_str = st.get("departureTime")
                    if not dep_str:
                        continue
                    # Parse "1899-12-30THH:MM:SS" -> extract time
                    try:
                        parts = dep_str.split("T")[1].split(":")
                        h, m = int(parts[0]), int(parts[1])
                        s = int(parts[2]) if len(parts) > 2 else 0
                    except (IndexError, ValueError):
                        continue
                    dep_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                    if dep_dt < now:
                        continue
                    all_times.append({
                        "route": str(route_id),
                        "headsign": st.get("stopHeadsign") or "—",
                        "estimated_time": dep_dt.isoformat(),
                        "theoretical_time": dep_dt.isoformat(),
                        "delay_seconds": 0,
                        "realtime": False,
                        "vehicle_type": _vehicle_type(route_id),
                        "provider": PROVIDER_ZTM,
                    })
            except Exception:
                _LOGGER.debug("ZTM schedule fallback failed for route %s", route_id)

        all_times.sort(key=lambda x: x.get("estimated_time") or "")
        cache[cache_key] = all_times

    # Filter out times already covered by realtime data (same route+time within 2min)
    existing_keys = set()
    for d in existing_deps:
        existing_keys.add(f"{d['route']}_{d.get('estimated_time', '')[:16]}")

    result = []
    for s in all_times:
        if s["estimated_time"] <= now.isoformat():
            continue
        key = f"{s['route']}_{s['estimated_time'][:16]}"
        if key not in existing_keys:
            result.append(s)
        if len(existing_deps) + len(result) >= 10:
            break

    return result
