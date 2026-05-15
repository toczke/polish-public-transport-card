"""Kraków ZTP provider - uses GTFS-RT TripUpdates directly (no stop_times parsing)."""

import csv
import logging
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO, StringIO

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

GTFS_BUS_URL = "https://gtfs.ztp.krakow.pl/GTFS_KRK_A.zip"
GTFS_TRAM_URL = "https://gtfs.ztp.krakow.pl/GTFS_KRK_T.zip"
RT_BUS_URL = "https://gtfs.ztp.krakow.pl/TripUpdates_A.pb"
RT_TRAM_URL = "https://gtfs.ztp.krakow.pl/TripUpdates_T.pb"
VEHICLES_BUS_URL = "https://api.ttss.pl/positions/?type=b&last=0"
VEHICLES_TRAM_URL = "https://api.ttss.pl/positions/?type=t&last=0"


async def fetch(coord) -> dict:
    """Fetch departures for a Kraków stop using GTFS-RT TripUpdates."""
    session = await coord._get_session()
    now = dt_util.now()
    stop_id = coord.stop_id

    # Load lightweight GTFS metadata (stops, routes, trips - no stop_times)
    meta = await _get_metadata(coord, session, now)
    if not meta:
        return _empty(coord, now)

    # Resolve ttss.pl stop_id (e.g. "b2608") to GTFS stop_ids via name matching
    gtfs_stop_ids = _resolve_stop_ids(stop_id, meta, coord.stop_name or "")

    # Resolve stop name
    if not coord.stop_name:
        if gtfs_stop_ids:
            coord.stop_name = meta["stops"].get(gtfs_stop_ids[0], {}).get("name", f"Przystanek {stop_id}")
        else:
            coord.stop_name = f"Przystanek {stop_id}"

    if not gtfs_stop_ids:
        _LOGGER.warning("Kraków: could not resolve stop_id %s to GTFS IDs", stop_id)
        return _empty(coord, now)

    # Fetch TripUpdates from both bus and tram feeds
    departures = []
    for rt_url in (RT_BUS_URL, RT_TRAM_URL):
        for gsid in gtfs_stop_ids:
            deps = await _get_departures_from_rt(session, rt_url, gsid, meta, now)
            departures.extend(deps)

    # Enrich with vehicle capabilities
    veh_dict = await _get_vehicles(coord, session)
    for d in departures:
        vc = d.get("vehicle_code", "")
        if not vc:
            continue
        v = veh_dict.get(vc)
        if not v:
            for prefix in ("HW", "RW", "HZ", "RZ", "HL", "RL", "HK", "RK", "HG", "RG", "HY", "RY", "RP", "RF"):
                v = veh_dict.get(prefix + vc)
                if v:
                    break
        if v:
            d["wheelchair_accessible"] = v.get("ramp") or v.get("hf_lf_le")
            d["air_conditioning"] = v.get("ac")
            if v.get("model"):
                d["vehicle_model"] = v["model"]

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    # Deduplicate
    seen = set()
    unique = []
    for d in departures:
        key = (d.get("route"), d.get("headsign"), (d.get("estimated_time") or "")[:16])
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return {
        "stop_id": stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": unique[:20],
        "last_update": now.isoformat(),
    }


async def _get_departures_from_rt(session, rt_url, stop_id, meta, now) -> list:
    """Parse GTFS-RT TripUpdates and extract departures for given stop_id."""
    try:
        from google.transit import gtfs_realtime_pb2

        async with session.get(rt_url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
            if resp.status != 200:
                return []
            data = await resp.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(data)

        departures = []
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            tu = entity.trip_update
            trip_id = tu.trip.trip_id
            route_id = tu.trip.route_id

            # Get vehicle code
            vehicle_code = ""
            if tu.HasField("vehicle"):
                v = tu.vehicle
                vehicle_code = v.id or v.label or ""

            # Find our stop in stop_time_updates
            for stu in tu.stop_time_update:
                if stu.stop_id != stop_id:
                    continue

                # Get departure time (absolute timestamp)
                dep_time = None
                delay = 0
                if stu.HasField("departure") and stu.departure.time:
                    dep_time = stu.departure.time
                    delay = stu.departure.delay
                elif stu.HasField("arrival") and stu.arrival.time:
                    dep_time = stu.arrival.time
                    delay = stu.arrival.delay

                if not dep_time:
                    continue

                dep_dt = datetime.fromtimestamp(dep_time, tz=now.tzinfo)
                # Skip past departures
                if dep_dt < now - timedelta(minutes=1):
                    continue

                # Scheduled time = actual - delay
                scheduled_dt = dep_dt - timedelta(seconds=delay)

                # Resolve route name and headsign
                route_name = route_id
                headsign = ""
                vehicle_type = "bus"
                if route_id and route_id in meta["routes"]:
                    route_name = meta["routes"][route_id].get("short_name", route_id)
                    vehicle_type = meta["routes"][route_id].get("type", "bus")
                if trip_id in meta["trips"]:
                    headsign = meta["trips"][trip_id].get("headsign", "")
                    if not route_id:
                        rid = meta["trips"][trip_id].get("route_id", "")
                        if rid in meta["routes"]:
                            route_name = meta["routes"][rid].get("short_name", rid)
                            vehicle_type = meta["routes"][rid].get("type", "bus")

                departures.append({
                    "route": route_name,
                    "headsign": headsign,
                    "estimated_time": dep_dt.isoformat(),
                    "theoretical_time": scheduled_dt.isoformat(),
                    "delay_seconds": delay,
                    "realtime": True,
                    "vehicle_type": vehicle_type,
                    "vehicle_code": vehicle_code,
                    "provider": "gtfsrt_krakow",
                })
                break  # Only first match per trip

        return departures
    except Exception as e:
        _LOGGER.debug("Kraków RT fetch failed from %s: %s", rt_url, e)
        return []


async def _get_metadata(coord, session, now):
    """Load and cache lightweight GTFS metadata (stops, routes, trips - NO stop_times)."""
    cache = coord.hass.data[DOMAIN].setdefault("_krakow_meta", {})
    today = now.strftime("%Y%m%d")
    cache_key = f"krakow_{today}"

    if cache.get(cache_key):
        return cache[cache_key]

    try:
        meta = {"stops": {}, "routes": {}, "trips": {}}
        for url in (GTFS_BUS_URL, GTFS_TRAM_URL):
            _LOGGER.debug("Kraków: downloading GTFS from %s", url)
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=180), ssl=False) as resp:
                if resp.status != 200:
                    continue
                data = await resp.read()

            _LOGGER.debug("Kraków: parsing metadata from %s (%d bytes)", url, len(data))
            _parse_metadata(data, meta)

        if meta["stops"]:
            cache[cache_key] = meta
            _LOGGER.debug("Kraków: loaded %d stops, %d routes, %d trips",
                         len(meta["stops"]), len(meta["routes"]), len(meta["trips"]))
            return meta
        return None
    except Exception as e:
        _LOGGER.warning("Kraków: failed to load GTFS metadata: %s", e)
        return cache.get(cache_key)


def _parse_metadata(data: bytes, meta: dict):
    """Parse stops.txt, routes.txt, trips.txt from GTFS zip (skip stop_times/shapes)."""
    with zipfile.ZipFile(BytesIO(data)) as zf:
        # stops.txt
        if "stops.txt" in zf.namelist():
            text = zf.read("stops.txt").decode("utf-8-sig")
            reader = csv.reader(StringIO(text))
            header = next(reader)
            id_idx = header.index("stop_id")
            name_idx = header.index("stop_name")
            for parts in reader:
                if len(parts) > max(id_idx, name_idx):
                    meta["stops"][parts[id_idx]] = {"name": parts[name_idx]}

        # routes.txt
        if "routes.txt" in zf.namelist():
            text = zf.read("routes.txt").decode("utf-8-sig")
            reader = csv.reader(StringIO(text))
            header = next(reader)
            id_idx = header.index("route_id")
            sn_idx = header.index("route_short_name") if "route_short_name" in header else -1
            rt_idx = header.index("route_type") if "route_type" in header else -1
            for parts in reader:
                if len(parts) > id_idx:
                    rid = parts[id_idx]
                    short = parts[sn_idx] if sn_idx >= 0 and len(parts) > sn_idx else rid
                    rtype = "tram" if rt_idx >= 0 and len(parts) > rt_idx and parts[rt_idx] == "0" else "bus"
                    meta["routes"][rid] = {"short_name": short, "type": rtype}

        # trips.txt (skip stop_times!)
        if "trips.txt" in zf.namelist():
            text = zf.read("trips.txt").decode("utf-8-sig")
            reader = csv.reader(StringIO(text))
            header = next(reader)
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            for parts in reader:
                if len(parts) > max(tid_idx, rid_idx):
                    meta["trips"][parts[tid_idx]] = {
                        "route_id": parts[rid_idx],
                        "headsign": parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else "",
                    }


async def _get_vehicles(coord, session) -> dict:
    """Load and cache vehicle info from api.ttss.pl."""
    cache = coord.hass.data[DOMAIN].setdefault("_krakow_vehicles", {})
    if cache.get("data"):
        return cache["data"]

    result = {}
    try:
        for url in (VEHICLES_BUS_URL, VEHICLES_TRAM_URL):
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
                if resp.status != 200:
                    continue
                import json
                raw = json.loads(await resp.text())
                for _vid, v in raw.get("pos", {}).items():
                    vtype = v.get("type", {})
                    num = vtype.get("num", "")
                    if not num or num.startswith("??"):
                        continue
                    result[num] = {
                        "hf_lf_le": vtype.get("low") == 2,
                        "ramp": vtype.get("low") in (1, 2),
                        "ac": vtype.get("ac") in (1, 2),
                        "model": vtype.get("type", ""),
                    }
        cache["data"] = result
    except Exception as e:
        _LOGGER.debug("Kraków: failed to load vehicles: %s", e)
    return result


def _empty(coord, now):
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}",
        "provider": coord.provider,
        "departures": [],
        "last_update": now.isoformat(),
    }


def _resolve_stop_ids(stop_id: str, meta: dict, stop_name: str = "") -> list:
    """Resolve a stop_id to GTFS stop_ids.

    If stop_id is already a GTFS numeric ID, return it directly.
    If it's a ttss.pl ID (e.g. "b2608"), resolve via name matching.
    """
    # If it's already a numeric GTFS stop_id
    if stop_id.isdigit() and stop_id in meta["stops"]:
        return [stop_id]

    # Build name->ids mapping from GTFS
    if "_name_to_ids" not in meta:
        name_map = {}
        for sid, info in meta["stops"].items():
            name = info.get("name", "").strip()
            if name:
                name_map.setdefault(name, []).append(sid)
        meta["_name_to_ids"] = name_map

    # Match by stop name (set during config flow)
    if stop_name and stop_name in meta["_name_to_ids"]:
        return meta["_name_to_ids"][stop_name]

    # Fallback: strip prefix and search
    numeric_part = stop_id.lstrip("bt")
    if numeric_part.isdigit():
        # Try common patterns
        candidates = [sid for sid in meta["stops"] if sid.endswith(numeric_part) or numeric_part in sid]
        if candidates:
            return candidates[:10]

    return []
