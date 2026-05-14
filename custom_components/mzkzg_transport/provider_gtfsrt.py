"""GTFS-RT provider for cities with protobuf realtime feeds (Kraków, Poznań, Białystok)."""

import logging
import zipfile
from datetime import datetime, timedelta
from io import BytesIO

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# GTFS-RT city configs: static GTFS zip + realtime TripUpdates URL
GTFSRT_CITIES = {
    "gtfsrt_krakow": {
        "gtfs_url": "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip",
        "rt_url": "https://gtfs.ztp.krakow.pl/TripUpdates.pb",
        "label": "ZTP Krak\u00f3w",
    },
    "gtfsrt_poznan": {
        "gtfs_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=feeds.zip",
        "rt_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=trip_updates.pb",
        "label": "ZTM Pozna\u0144",
    },
    "gtfsrt_bialystok": {
        "gtfs_url": "http://komunikacja.bialystok.pl/cms/File/download/gtfs/google_transit.zip",
        "rt_url": "http://komunikacja.bialystok.pl/cms/File/download/gtfs-rt/trip_updates.pb",
        "label": "BKM Bia\u0142ystok",
    },
}


async def fetch(coord) -> dict:
    """Fetch departures using static GTFS + GTFS-RT TripUpdates."""
    session = await coord._get_session()
    now = dt_util.now()
    city_cfg = GTFSRT_CITIES.get(coord.provider)
    if not city_cfg:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name, "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Load static GTFS (cached daily)
    gtfs = await _get_gtfs_data(coord, session, city_cfg, now)
    if not gtfs:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}", "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Get stop name
    if not coord.stop_name:
        coord.stop_name = gtfs["stops"].get(coord.stop_id, {}).get("name", f"Przystanek {coord.stop_id}")

    # Get scheduled departures for this stop
    stop_times = gtfs["stop_times"].get(coord.stop_id, [])
    today = now.strftime("%Y%m%d")

    # Load RT delays
    delays = await _get_rt_delays(session, city_cfg["rt_url"])

    departures = []
    for st in stop_times:
        trip_id = st["trip_id"]
        route_id = st["route_id"]
        route_name = gtfs["routes"].get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or gtfs["trips"].get(trip_id, {}).get("headsign", "")

        # Parse departure time
        h, m, s = st["departure_time"]
        dep_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
        if dep_dt < now - timedelta(minutes=1):
            continue

        # Apply RT delay
        delay_sec = 0
        is_realtime = False
        rt_key = f"{trip_id}_{coord.stop_id}"
        if rt_key in delays:
            delay_sec = delays[rt_key]
            is_realtime = True

        estimated_dt = dep_dt + timedelta(seconds=delay_sec)

        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": delay_sec,
            "realtime": is_realtime,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "provider": coord.provider,
        })

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": departures[:20],
        "last_update": now.isoformat(),
    }


async def _get_gtfs_data(coord, session, city_cfg, now):
    """Load and cache parsed GTFS data (daily)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_cache", {})
    today = now.strftime("%Y%m%d")
    cache_key = f"{coord.provider}_{today}"

    if cache.get(cache_key):
        return cache[cache_key]

    try:
        async with session.get(city_cfg["gtfs_url"], timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()

        gtfs = _parse_gtfs_zip(data, coord.stop_id)
        cache[cache_key] = gtfs
        return gtfs
    except Exception as e:
        _LOGGER.warning("GTFS-RT: failed to load GTFS for %s: %s", coord.provider, e)
        return cache.get(cache_key)


def _parse_gtfs_zip(data: bytes, stop_id: str) -> dict:
    """Parse relevant GTFS files from zip."""
    stops = {}
    routes = {}
    trips = {}
    stop_times = {}  # stop_id -> list of {trip_id, route_id, departure_time, headsign}

    with zipfile.ZipFile(BytesIO(data)) as zf:
        # stops.txt
        if "stops.txt" in zf.namelist():
            lines = zf.read("stops.txt").decode("utf-8-sig").splitlines()
            header = lines[0].split(",")
            id_idx = header.index("stop_id")
            name_idx = header.index("stop_name")
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) > max(id_idx, name_idx):
                    sid = parts[id_idx].strip().strip('"')
                    stops[sid] = {"name": parts[name_idx].strip().strip('"')}

        # routes.txt
        if "routes.txt" in zf.namelist():
            lines = zf.read("routes.txt").decode("utf-8-sig").splitlines()
            header = lines[0].split(",")
            id_idx = header.index("route_id")
            sn_idx = header.index("route_short_name") if "route_short_name" in header else -1
            rt_idx = header.index("route_type") if "route_type" in header else -1
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) > id_idx:
                    rid = parts[id_idx].strip().strip('"')
                    short = parts[sn_idx].strip().strip('"') if sn_idx >= 0 and len(parts) > sn_idx else rid
                    rtype = "tram" if rt_idx >= 0 and len(parts) > rt_idx and parts[rt_idx].strip().strip('"') == "0" else "bus"
                    routes[rid] = {"short_name": short, "type": rtype}

        # trips.txt
        if "trips.txt" in zf.namelist():
            lines = zf.read("trips.txt").decode("utf-8-sig").splitlines()
            header = lines[0].split(",")
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) > max(tid_idx, rid_idx):
                    tid = parts[tid_idx].strip().strip('"')
                    rid = parts[rid_idx].strip().strip('"')
                    hs = parts[hs_idx].strip().strip('"') if hs_idx >= 0 and len(parts) > hs_idx else ""
                    trips[tid] = {"route_id": rid, "headsign": hs}

        # stop_times.txt - only for our stop
        if "stop_times.txt" in zf.namelist():
            lines = zf.read("stop_times.txt").decode("utf-8-sig").splitlines()
            header = lines[0].split(",")
            tid_idx = header.index("trip_id")
            sid_idx = header.index("stop_id")
            dep_idx = header.index("departure_time")
            hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                    continue
                sid = parts[sid_idx].strip().strip('"')
                if sid != stop_id:
                    continue
                tid = parts[tid_idx].strip().strip('"')
                dep_str = parts[dep_idx].strip().strip('"')
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                trip_info = trips.get(tid, {})
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx].strip().strip('"')
                stop_times.setdefault(sid, []).append({
                    "trip_id": tid,
                    "route_id": trip_info.get("route_id", ""),
                    "departure_time": (h, m, s),
                    "headsign": hs or trip_info.get("headsign", ""),
                })

    return {"stops": stops, "routes": routes, "trips": trips, "stop_times": stop_times}


async def _get_rt_delays(session, rt_url: str) -> dict:
    """Fetch GTFS-RT TripUpdates and return {trip_id_stop_id: delay_seconds}."""
    try:
        from google.transit import gtfs_realtime_pb2

        async with session.get(rt_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return {}
            data = await resp.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(data)

        delays = {}
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            trip_id = entity.trip_update.trip.trip_id
            for stu in entity.trip_update.stop_time_update:
                stop_id = stu.stop_id
                delay = stu.departure.delay if stu.HasField("departure") else (stu.arrival.delay if stu.HasField("arrival") else 0)
                delays[f"{trip_id}_{stop_id}"] = delay

        return delays
    except Exception as e:
        _LOGGER.debug("GTFS-RT: failed to fetch RT data from %s: %s", rt_url, e)
        return {}
