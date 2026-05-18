"""ZKM Gdynia provider."""

from datetime import timedelta
import logging

import aiohttp

from homeassistant.util import dt as dt_util

from .const import PROVIDER_ZKM, ZKM_GDYNIA_DELAYS_URL, ZKM_GDYNIA_ROUTES_URL
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)


async def fetch(coord) -> dict:
    """Fetch departures from ZKM Gdynia ZDiZ API."""
    session = await coord._get_session()

    if not coord._routes_map and (dt_util.now().timestamp() - coord._routes_load_failed_at > 3600):
        await _load_routes(coord, session)

    url = f"{ZKM_GDYNIA_DELAYS_URL}?stopId={coord.stop_id}"
    data = await fetch_with_retry(session, url)

    departures = []
    now = dt_util.now()
    for d in data.get("delay", []):
        route_id = d.get("routeId") or d.get("routeShortName")
        route_name = coord._routes_map.get(str(route_id), str(route_id))
        time_str = d.get("estimatedTime") or d.get("theoreticalTime") or d.get("time")
        if not time_str:
            continue

        estimated_iso = time_str
        if len(time_str) <= 8 and ":" in time_str:
            parts = time_str.split(":")
            h, m = int(parts[0]), int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            day_add = 0
            if h >= 24:
                h -= 24
                day_add = 1
            dep_dt = now.replace(hour=h, minute=m, second=s, microsecond=0) + timedelta(days=day_add)
            if (dep_dt - now).total_seconds() < -3600:
                dep_dt += timedelta(days=1)
            if (dep_dt - now).total_seconds() < -30:
                continue
            estimated_iso = dep_dt.isoformat()

        delay_sec = d.get("delayInSeconds") or d.get("delay") or 0
        status = d.get("status", "")
        is_realtime = bool(
            status == "REALTIME"
            or d.get("estimatedTime")
            or d.get("realTime")
            or d.get("predictedTime")
        )

        departures.append({
            "route": route_name,
            "headsign": d.get("headsign") or d.get("direction") or d.get("directionName") or "—",
            "estimated_time": estimated_iso,
            "theoretical_time": d.get("theoreticalTime") or time_str,
            "delay_seconds": delay_sec,
            "realtime": is_realtime,
            "vehicle_type": _vehicle_type(route_name),
            "bike_allowed": d.get("bikeAllowed", None),
            "wheelchair_accessible": d.get("wheelchairAccessible", None),
            "air_conditioning": d.get("airConditioning", None),
            "vehicle_code": str(d.get("vehicleCode") or d.get("vehicleId") or "") or None,
            "provider": PROVIDER_ZKM,
        })

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": PROVIDER_ZKM,
        "departures": departures,
        "last_update": now.isoformat(),
    }


async def _load_routes(coord, session: aiohttp.ClientSession) -> None:
    """Load ZKM route short names."""
    try:
        async with session.get(
            ZKM_GDYNIA_ROUTES_URL, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                routes = data if isinstance(data, list) else data.get("value", [])
                for r in routes:
                    if r.get("routeId") and r.get("routeShortName"):
                        coord._routes_map[str(r["routeId"])] = str(r["routeShortName"])
            else:
                coord._routes_load_failed_at = dt_util.now().timestamp()
    except Exception:
        _LOGGER.warning("Could not load ZKM routes")
        coord._routes_load_failed_at = dt_util.now().timestamp()


def _vehicle_type(route_name) -> str:
    """Determine vehicle type for ZKM Gdynia."""
    s = str(route_name or "")
    n = int(s) if s.isdigit() else None
    if n is not None and 20 <= n <= 29:
        return "trolleybus"
    return "bus"
