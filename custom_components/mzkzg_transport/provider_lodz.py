"""MPK Łódź provider."""

import logging
from xml.etree import ElementTree

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
LODZ_URL = "http://rozklady.lodz.pl/Home/GetTimetableReal"


async def fetch(coord) -> dict:
    """Fetch realtime departures from MPK Łódź."""
    session = await coord._get_session()
    now = dt_util.now()

    # stop_id format: "stopId:stopNr" e.g. "205:4"
    parts = str(coord.stop_id).split(":")
    stop_id = parts[0]
    stop_nr = parts[1] if len(parts) > 1 else "1"

    url = f"{LODZ_URL}?busStopId={stop_id}&busStopNr={stop_nr}"
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        text = await resp.text()

    root = ElementTree.fromstring(text)
    stop_el = root.find("Stop")
    if not coord.stop_name and stop_el is not None:
        coord.stop_name = stop_el.get("name", f"Przystanek {coord.stop_id}")

    departures = []
    for day in root.iter("Day"):
        for route_el in day.iter("R"):
            route = route_el.get("nr", "?")
            headsign = route_el.get("dir", "—")
            vuw = route_el.get("vuw", "")

            for s in route_el.iter("S"):
                tm = s.get("tm", "")
                is_realtime = s.get("veh") == "T"
                nb = s.get("nb", "")

                # Parse time
                estimated_dt = None
                if "min" in tm:
                    try:
                        minutes = int(tm.replace("min", "").strip())
                    except ValueError:
                        minutes = 0
                    estimated_dt = now + __import__("datetime").timedelta(minutes=minutes)
                else:
                    try:
                        h, m = int(s.get("th", "0")), int(tm)
                        estimated_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                        if (estimated_dt - now).total_seconds() < -60:
                            continue
                    except (ValueError, TypeError):
                        continue

                if estimated_dt is None:
                    continue

                departures.append({
                    "route": route,
                    "headsign": headsign,
                    "estimated_time": estimated_dt.isoformat(),
                    "theoretical_time": estimated_dt.isoformat(),
                    "delay_seconds": 0,
                    "realtime": is_realtime,
                    "vehicle_type": "tram" if route_el.get("vt") == "T" else "bus",
                    "bike_allowed": "R" in vuw,
                    "wheelchair_accessible": "N" in vuw,
                    "air_conditioning": "K" in vuw,
                    "ticket_machine": "B" in vuw,
                    "vehicle_code": nb if nb and nb != "0" else None,
                    "provider": coord.provider,
                })

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}",
        "provider": coord.provider,
        "departures": departures,
        "last_update": now.isoformat(),
    }
