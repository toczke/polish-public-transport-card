"""GTFS-RT provider for cities with protobuf realtime feeds (Kraków, Poznań, Białystok)."""

import csv
import logging
import zipfile
from datetime import timedelta
from io import BytesIO, StringIO

import aiohttp

from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _read_csv(zf, filename):
    """Read a GTFS CSV file from zip, return (header, rows) using proper CSV parsing."""
    if filename not in zf.namelist():
        return None, []
    text = zf.read(filename).decode("utf-8-sig")
    reader = csv.reader(StringIO(text))
    header = next(reader)
    return header, list(reader)

# GTFS-RT city configs: static GTFS zip + realtime TripUpdates URL
GTFSRT_CITIES = {
    "gtfsrt_poznan": {
        "gtfs_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGTFSFile",
        "rt_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=trip_updates.pb",
        "vehicles_url": "https://www.ztm.poznan.pl/pl/dla-deweloperow/getGtfsRtFile?file=vehicle_dictionary.csv",
        "label": "ZTM Pozna\u0144",
    },
    "gtfsrt_lublin": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/lublin.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/lublin.pb",
        "label": "ZTM Lublin",
    },
    "gtfsrt_kielce": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/kielce.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/kielce.pb",
        "label": "MPK Kielce",
    },
    "gtfsrt_radom": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/radom.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/radom.pb",
        "label": "MZDiK Radom",
    },
    "gtfsrt_czestochowa": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/czestochowa.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/czestochowa.pb",
        "label": "MPK Cz\u0119stochowa",
    },
    "gtfsrt_elblag": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/elblag.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/elblag.pb",
        "label": "ZKM Elbl\u0105g",
    },
    "gtfsrt_gorzow": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/gorzow.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/gorzow.pb",
        "label": "MZK Gorz\u00f3w Wlkp.",
    },
    "gtfsrt_suwalki": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/suwalki.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/suwalki.pb",
        "label": "PGK Suwa\u0142ki",
    },
    "gtfsrt_przemysl": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/przemysl.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/przemysl.pb",
        "label": "MZK Przemy\u015bl",
    },
    "gtfsrt_rybnik": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/rybnik.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/rybnik.pb",
        "label": "ZTZ Rybnik",
    },
    "gtfsrt_kutno": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/kutno.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/kutno.pb",
        "label": "MZK Kutno",
    },
    "gtfsrt_legnica": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/legnica.zip",
        "rt_url": "https://cdn.zbiorkom.live/gtfs-rt/legnica.pb",
        "label": "MPK Legnica",
    },
    "gtfsrt_gzm": {
        "gtfs_url": "https://otwartedane.metropoliagzm.pl/dataset/317435cc-0075-4d10-b8ef-6e9b0010e90a/resource/f93b4ad0-8573-434f-9174-a4c90bee066d/download/schedule_ztm_2026.05.14_9690_0542.zip",
        "rt_url": "https://gtfsrt.transportgzm.pl:5443/gtfsrt/gzm/tripUpdates",
        "label": "ZTM GZM (Katowice)",
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
        vehicle_code = ""
        rt_key = f"{trip_id}_{coord.stop_id}"
        rt_key_seq = f"{trip_id}_seq{st.get('stop_sequence', '')}"
        for key in (rt_key, rt_key_seq, trip_id):
            if key in delays:
                delay_sec, vehicle_code = delays[key]
                is_realtime = True
                break

        estimated_dt = dep_dt + timedelta(seconds=delay_sec)

        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": delay_sec,
            "realtime": is_realtime,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "vehicle_code": vehicle_code if is_realtime else None,
            "provider": coord.provider,
        })

    # Enrich with vehicle capabilities if available
    if city_cfg.get("vehicles_url") and any(d.get("vehicle_code") for d in departures):
        veh_dict = await _get_vehicle_dict(coord, session, city_cfg)
        for d in departures:
            vc = d.get("vehicle_code", "")
            if vc and vc in veh_dict:
                v = veh_dict[vc]
                d["wheelchair_accessible"] = v.get("ramp") or v.get("hf_lf_le")
                d["air_conditioning"] = v.get("air_conditioner")
                d["bike_allowed"] = v.get("place_for_transp_bicycles")
                d["ticket_machine"] = v.get("ticket_machine")
                d["usb"] = v.get("usb_charger")

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    # Deduplicate: same route + headsign + theoretical_time = same departure
    seen = set()
    unique = []
    for d in departures:
        est = (d.get("estimated_time") or "")[:16]
        key = (d.get("route"), d.get("headsign"), est)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": unique[:20],
        "last_update": now.isoformat(),
    }


async def _get_gtfs_data(coord, session, city_cfg, now):
    """Load and cache parsed GTFS data (daily)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_cache", {})
    today = now.strftime("%Y%m%d")
    cache_key = f"{coord.provider}_{today}"

    if cache.get(cache_key):
        gtfs = cache[cache_key]
        # Parse stop_times for this specific stop if not already done
        if coord.stop_id not in gtfs["stop_times"] and gtfs.get("_raw"):
            _parse_stop_times_for(gtfs, coord.stop_id)
        return gtfs

    try:
        async with session.get(city_cfg["gtfs_url"], timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()

        gtfs = _parse_gtfs_zip(data)
        cache[cache_key] = gtfs
        # Parse stop_times for current stop
        if coord.stop_id not in gtfs["stop_times"]:
            _parse_stop_times_for(gtfs, coord.stop_id)
        return gtfs
    except Exception as e:
        _LOGGER.warning("GTFS-RT: failed to load GTFS for %s: %s", coord.provider, e)
        return cache.get(cache_key)


def _parse_gtfs_zip(data: bytes) -> dict:
    """Parse relevant GTFS files from zip."""
    from datetime import date as dt_date

    stops = {}
    routes = {}
    trips = {}
    stop_times = {}  # stop_id -> list of {trip_id, route_id, departure_time, headsign}
    raw_zip = data
    today = dt_date.today()
    today_str = today.strftime("%Y%m%d")
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][today.weekday()]

    with zipfile.ZipFile(BytesIO(data)) as zf:
        # calendar.txt — active services
        active_services = set()
        has_calendar = False
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                svc = parts[sid_idx]
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > today_str or parts[end_idx] < today_str:
                        active = False
                if active:
                    active_services.add(svc)

        # calendar_dates.txt — exceptions
        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            has_calendar = True
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != today_str:
                    continue
                svc = parts[sid_idx]
                if parts[etype_idx] == "1":
                    active_services.add(svc)
                elif parts[etype_idx] == "2":
                    active_services.discard(svc)

        # stops.txt
        header, rows = _read_csv(zf, "stops.txt")
        if header:
            id_idx = header.index("stop_id")
            name_idx = header.index("stop_name")
            for parts in rows:
                if len(parts) > max(id_idx, name_idx):
                    stops[parts[id_idx]] = {"name": parts[name_idx]}

        # routes.txt
        header, rows = _read_csv(zf, "routes.txt")
        if header:
            id_idx = header.index("route_id")
            sn_idx = header.index("route_short_name") if "route_short_name" in header else -1
            rt_idx = header.index("route_type") if "route_type" in header else -1
            for parts in rows:
                if len(parts) > id_idx:
                    rid = parts[id_idx]
                    short = parts[sn_idx] if sn_idx >= 0 and len(parts) > sn_idx else rid
                    rtype = "tram" if rt_idx >= 0 and len(parts) > rt_idx and parts[rt_idx] == "0" else "bus"
                    routes[rid] = {"short_name": short, "type": rtype}

        # trips.txt
        header, rows = _read_csv(zf, "trips.txt")
        if header:
            tid_idx = header.index("trip_id")
            rid_idx = header.index("route_id")
            hs_idx = header.index("trip_headsign") if "trip_headsign" in header else -1
            svc_idx = header.index("service_id") if "service_id" in header else -1
            # If calendar was parsed but no services active, skip filtering
            # (GTFS may cover future dates only)
            filter_by_service = has_calendar and bool(active_services)
            for parts in rows:
                if len(parts) > max(tid_idx, rid_idx):
                    tid = parts[tid_idx]
                    if filter_by_service and svc_idx >= 0 and len(parts) > svc_idx:
                        if parts[svc_idx] not in active_services:
                            continue
                    rid = parts[rid_idx]
                    hs = parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else ""
                    trips[tid] = {"route_id": rid, "headsign": hs}

        # Store raw zip for on-demand stop_times parsing
        raw_zip = data

    return {"stops": stops, "routes": routes, "trips": trips, "stop_times": stop_times, "_raw": raw_zip}


def _parse_stop_times_for(gtfs, stop_id):
    """Parse stop_times from cached raw zip for a specific stop."""
    raw = gtfs.get("_raw")
    if not raw:
        return
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        if "stop_times.txt" not in zf.namelist():
            return
        text = zf.read("stop_times.txt").decode("utf-8-sig")
        reader = csv.reader(StringIO(text))
        header = next(reader)
        tid_idx = header.index("trip_id")
        sid_idx = header.index("stop_id")
        dep_idx = header.index("departure_time")
        hs_idx = header.index("stop_headsign") if "stop_headsign" in header else -1
        seq_idx = header.index("stop_sequence") if "stop_sequence" in header else -1

        # First pass: collect our stop's entries + track last stop per trip (for headsign)
        our_entries = []
        last_seq_per_trip = {}  # trip_id -> (max_seq, stop_id)
        need_headsign = set()

        for parts in reader:
            if len(parts) <= max(tid_idx, sid_idx, dep_idx):
                continue
            tid = parts[tid_idx]
            if tid not in trips:
                continue
            sid = parts[sid_idx]
            seq = int(parts[seq_idx]) if seq_idx >= 0 and len(parts) > seq_idx and parts[seq_idx].isdigit() else 0

            if sid == stop_id:
                dep_str = parts[dep_idx]
                try:
                    h, m, s = [int(x) for x in dep_str.split(":")]
                except (ValueError, IndexError):
                    continue
                hs = ""
                if hs_idx >= 0 and len(parts) > hs_idx:
                    hs = parts[hs_idx]
                hs = hs or trips[tid].get("headsign", "")
                our_entries.append({"trip_id": tid, "route_id": trips[tid].get("route_id", ""), "departure_time": (h, m, s), "headsign": hs, "stop_sequence": str(seq)})
                if not hs:
                    need_headsign.add(tid)

            # Track last stop for trips needing headsign
            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        # Fill in headsigns from last stop name
        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"][stop_id] = our_entries


async def _get_vehicle_dict(coord, session, city_cfg) -> dict:
    """Load and cache vehicle capabilities dictionary (CSV)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_vehicles", {})
    cache_key = coord.provider
    if cache.get(cache_key):
        return cache[cache_key]
    try:
        async with session.get(city_cfg["vehicles_url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return {}
            text = await resp.text()
        lines = text.strip().splitlines()
        header = lines[0].split(",")
        veh_idx = header.index("vehicle") if "vehicle" in header else 0
        result = {}
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) <= veh_idx:
                continue
            vid = parts[veh_idx].strip()
            row = {}
            for i, col in enumerate(header):
                if i != veh_idx and i < len(parts):
                    row[col.strip()] = parts[i].strip() == "1"
            result[vid] = row
        cache[cache_key] = result
        return result
    except Exception:
        return {}


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
            vehicle_label = ""
            if entity.trip_update.HasField("vehicle"):
                v = entity.trip_update.vehicle
                vid = v.id or v.label or ""
                # Strip prefix like "3/" or "undefined/"
                vehicle_label = vid.split("/")[-1] if "/" in vid else vid
            for stu in entity.trip_update.stop_time_update:
                delay = stu.departure.delay if stu.HasField("departure") else (stu.arrival.delay if stu.HasField("arrival") else 0)
                if stu.stop_id:
                    delays[f"{trip_id}_{stu.stop_id}"] = (delay, vehicle_label)
                if stu.stop_sequence:
                    delays[f"{trip_id}_seq{stu.stop_sequence}"] = (delay, vehicle_label)
                # Also store by trip_id only (best estimate for any stop on this trip)
                delays[trip_id] = (delay, vehicle_label)

        return delays
    except Exception as e:
        _LOGGER.debug("GTFS-RT: failed to fetch RT data from %s: %s", rt_url, e)
        return {}
