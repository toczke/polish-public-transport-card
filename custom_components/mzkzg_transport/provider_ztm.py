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

    # Deduplicate: same route + estimated time (to minute)
    seen = set()
    unique = []
    for d in departures:
        est = (d.get("estimated_time") or "")[:16]  # trim to minute
        key = (d.get("route"), est)
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": PROVIDER_ZTM,
        "departures": unique,
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


