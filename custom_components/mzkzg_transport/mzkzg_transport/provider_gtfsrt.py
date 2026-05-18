"""GTFS-RT provider for cities with protobuf realtime feeds (Kraków, Poznań, Białystok)."""

import asyncio
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
    "gtfsrt_szczecin": {
        "gtfs_url": "https://www.zditm.szczecin.pl/storage/gtfs/gtfs.zip",
        "rt_url": "https://www.zditm.szczecin.pl/storage/gtfs/gtfs-rt-trips.pb",
        "label": "ZDiTM Szczecin",
    },
    "gtfsrt_warszawa": {
        "gtfs_url": "https://mkuran.pl/gtfs/warsaw.zip",
        "rt_url": "https://mkuran.pl/gtfs/warsaw/vehicles.pb",
        "label": "ZTM Warszawa",
    },
    "gtfsrt_elk": {
        "gtfs_url": "https://mkuran.pl/gtfs/elk.zip",
        "rt_url": "https://mkuran.pl/gtfs/elk.pb",
        "label": "MZK Ełk",
    },
    "gtfsrt_wkd": {
        "gtfs_url": "https://mkuran.pl/gtfs/wkd.zip",
        "rt_url": "https://mkuran.pl/gtfs/wkd.pb",
        "label": "WKD",
    },
    "gtfs_bialystok": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/bialystok.zip",
        "rt_url": None,
        "label": "BKM Białystok",
    },
    "gtfs_olsztyn": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/olsztyn.zip",
        "rt_url": None,
        "label": "ZDZiT Olsztyn",
    },
    "gtfs_opole": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/opole.zip",
        "rt_url": None,
        "label": "MZK Opole",
    },
    "gtfs_rzeszow": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/rzeszow.zip",
        "rt_url": None,
        "label": "ZTM Rzeszów",
    },
    "gtfs_leszno": {
        "gtfs_url": "https://cdn.zbiorkom.live/gtfs/leszno.zip",
        "rt_url": None,
        "label": "MZK Leszno",
    },
    "gtfsrt_gzm": {
        "gtfs_url": None,  # Dynamic - fetched from CKAN API
        "gtfs_package_id": "317435cc-0075-4d10-b8ef-6e9b0010e90a",
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
    delays = {}
    if city_cfg.get("rt_url"):
        delays = await _get_rt_delays(session, city_cfg["rt_url"])
    if city_cfg.get("rt_url_tram"):
            tram_delays = await _get_rt_delays(session, city_cfg["rt_url_tram"])
            delays.update(tram_delays)

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

        trip_data = gtfs["trips"].get(trip_id, {})
        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": estimated_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": delay_sec,
            "realtime": is_realtime,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "vehicle_code": vehicle_code if is_realtime else None,
            "wheelchair_accessible": trip_data.get("wheelchair"),
            "bike_allowed": trip_data.get("bike"),
            "provider": coord.provider,
        })

    # Enrich with vehicle capabilities if available
    if city_cfg.get("vehicles_url") and any(d.get("vehicle_code") for d in departures):
        veh_dict = await _get_vehicle_dict(coord, session, city_cfg)
        for d in departures:
            vc = d.get("vehicle_code", "")
            if not vc:
                continue
            # Try direct match, then common prefixed variants (for Kraków trams: 121 -> HW121, etc.)
            v = veh_dict.get(vc)
            if not v:
                for prefix in ("HW", "RW", "HZ", "RZ", "HL", "RL", "HK", "RK", "HG", "RG", "HY", "RY", "RP", "RF"):
                    v = veh_dict.get(prefix + vc)
                    if v:
                        break
            if v:
                d["wheelchair_accessible"] = v.get("ramp") or v.get("hf_lf_le")
                d["air_conditioning"] = v.get("air_conditioner")
                d["bike_allowed"] = v.get("place_for_transp_bicycles")
                d["ticket_machine"] = v.get("ticket_machine")
                d["usb"] = v.get("usb_charger")
                if v.get("vehicle_model"):
                    d["vehicle_model"] = v["vehicle_model"]

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

    # If fewer than 5 departures, load tomorrow's schedule
    if len(unique) < 5 and gtfs.get("_raw"):
        tomorrow = now + timedelta(days=1)
        tomorrow_deps = _get_tomorrow_departures(gtfs, coord.stop_id, tomorrow, now)
        for d in tomorrow_deps:
            est = (d.get("estimated_time") or "")[:16]
            key = (d.get("route"), d.get("headsign"), est)
            if key not in seen:
                seen.add(key)
                unique.append(d)
                if len(unique) >= 20:
                    break

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": unique[:20],
        "last_update": now.isoformat(),
    }


def _get_tomorrow_departures(gtfs, stop_id, tomorrow, now):
    """Get scheduled departures for tomorrow from raw GTFS zip."""
    from datetime import date as dt_date
    
    raw = gtfs.get("_raw")
    if not raw:
        return []
    
    tomorrow_str = tomorrow.strftime("%Y%m%d")
    day_name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][tomorrow.weekday()]
    
    # Parse calendar for tomorrow's active services
    active_services = set()
    with zipfile.ZipFile(BytesIO(raw)) as zf:
        header, rows = _read_csv(zf, "calendar.txt")
        if header:
            sid_idx = header.index("service_id")
            day_idx = header.index(day_name) if day_name in header else -1
            start_idx = header.index("start_date") if "start_date" in header else -1
            end_idx = header.index("end_date") if "end_date" in header else -1
            for parts in rows:
                if len(parts) <= sid_idx:
                    continue
                active = day_idx >= 0 and len(parts) > day_idx and parts[day_idx] == "1"
                if active and start_idx >= 0 and end_idx >= 0 and len(parts) > max(start_idx, end_idx):
                    if parts[start_idx] > tomorrow_str or parts[end_idx] < tomorrow_str:
                        active = False
                if active:
                    active_services.add(parts[sid_idx])

        header, rows = _read_csv(zf, "calendar_dates.txt")
        if header:
            sid_idx = header.index("service_id")
            date_idx = header.index("date")
            etype_idx = header.index("exception_type")
            for parts in rows:
                if len(parts) <= max(sid_idx, date_idx, etype_idx):
                    continue
                if parts[date_idx] != tomorrow_str:
                    continue
                if parts[etype_idx] == "1":
                    active_services.add(parts[sid_idx])
                elif parts[etype_idx] == "2":
                    active_services.discard(parts[sid_idx])

    if not active_services:
        return []

    # Filter trips for tomorrow's services
    tomorrow_trips = {tid: t for tid, t in gtfs["trips"].items() if t.get("service_id", tid) in active_services}
    
    # Get stop_times for this stop, filtered by tomorrow's trips
    stop_times = gtfs["stop_times"].get(stop_id, [])
    departures = []
    
    for st in stop_times:
        trip_id = st["trip_id"]
        if trip_id not in tomorrow_trips and trip_id not in gtfs["trips"]:
            continue
        # Check if trip runs tomorrow
        trip = gtfs["trips"].get(trip_id, {})
        # For trips without service_id tracking, include all
        
        route_id = st["route_id"]
        route_name = gtfs["routes"].get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or trip.get("headsign", "")
        
        h, m, s = st["departure_time"]
        dep_dt = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
        
        if dep_dt < now:
            continue

        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": dep_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": 0,
            "realtime": False,
            "vehicle_type": gtfs["routes"].get(route_id, {}).get("type", "bus"),
            "provider": "schedule",
        })

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    return departures[:15]


async def _get_gzm_gtfs_url(session, package_id: str) -> str | None:
    """Fetch latest GTFS URL from GZM CKAN API."""
    try:
        ckan_url = f"https://otwartedane.metropoliagzm.pl/api/3/action/package_show?id={package_id}"
        async with session.get(ckan_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
        
        import json
        resources = data.get("result", {}).get("resources", [])
        # Find the first schedule_ZTM zip
        for r in resources:
            name = r.get("name", "").lower()
            if "schedule" in name and r.get("format", "").lower() == "zip":
                return r.get("url")
        return None
    except Exception as e:
        _LOGGER.debug("GZM CKAN lookup failed: %s", e)
        return None


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

    # Clean old cache entries for this provider (memory leak fix)
    prefix = f"{coord.provider}_"
    for old_key in list(cache.keys()):
        if old_key.startswith(prefix) and old_key != cache_key:
            old_gtfs = cache.pop(old_key, None)
            if old_gtfs:
                # Free raw zip memory
                old_gtfs.pop("_raw", None)
                old_gtfs.pop("_raw_tram", None)
            _LOGGER.debug("Cleaned old GTFS cache: %s", old_key)

    try:
        gtfs_url = city_cfg.get("gtfs_url")
        
        # Dynamic URL for GZM
        if not gtfs_url and city_cfg.get("gtfs_package_id"):
            gtfs_url = await _get_gzm_gtfs_url(session, city_cfg["gtfs_package_id"])
            if not gtfs_url:
                _LOGGER.warning("GTFS-RT: could not get dynamic URL for GZM")
                return None

        async with session.get(gtfs_url, timeout=aiohttp.ClientTimeout(total=120), ssl=False) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()

        gtfs = _parse_gtfs_zip(data)

        # Merge secondary GTFS zip (e.g. Kraków tram)
        if city_cfg.get("gtfs_url_tram"):
            try:
                async with session.get(city_cfg["gtfs_url_tram"], timeout=aiohttp.ClientTimeout(total=120), ssl=False) as resp2:
                    if resp2.status == 200:
                        data2 = await resp2.read()
                        gtfs2 = _parse_gtfs_zip(data2)
                        gtfs["stops"].update(gtfs2["stops"])
                        gtfs["routes"].update(gtfs2["routes"])
                        gtfs["trips"].update(gtfs2["trips"])
                        # Store secondary raw zip for stop_times parsing
                        gtfs["_raw_tram"] = data2
            except Exception as e:
                _LOGGER.debug("GTFS-RT: failed to load tram GTFS for %s: %s", coord.provider, e)

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
            wc_idx = header.index("wheelchair_accessible") if "wheelchair_accessible" in header else -1
            bike_idx = header.index("bikes_allowed") if "bikes_allowed" in header else -1
            filter_by_service = has_calendar
            for parts in rows:
                if len(parts) > max(tid_idx, rid_idx):
                    tid = parts[tid_idx]
                    if filter_by_service and svc_idx >= 0 and len(parts) > svc_idx:
                        if parts[svc_idx] not in active_services:
                            continue
                    rid = parts[rid_idx]
                    hs = parts[hs_idx] if hs_idx >= 0 and len(parts) > hs_idx else ""
                    trip = {"route_id": rid, "headsign": hs}
                    if wc_idx >= 0 and len(parts) > wc_idx and parts[wc_idx] == "1":
                        trip["wheelchair"] = True
                    if bike_idx >= 0 and len(parts) > bike_idx and parts[bike_idx] == "1":
                        trip["bike"] = True
                    trips[tid] = trip

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

    # Also parse from secondary (tram) zip if present
    if gtfs.get("_raw_tram"):
        _parse_stop_times_from_raw(gtfs, stop_id, gtfs["_raw_tram"])


def _parse_stop_times_from_raw(gtfs, stop_id, raw_data):
    """Parse stop_times from a raw GTFS zip and append to gtfs['stop_times'][stop_id]."""
    trips = gtfs["trips"]
    stops = gtfs["stops"]
    with zipfile.ZipFile(BytesIO(raw_data)) as zf:
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

        our_entries = []
        last_seq_per_trip = {}
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

            if tid in need_headsign or (sid == stop_id and not trips[tid].get("headsign")):
                prev = last_seq_per_trip.get(tid, (-1, ""))
                if seq > prev[0]:
                    last_seq_per_trip[tid] = (seq, sid)

        if need_headsign and last_seq_per_trip:
            for entry in our_entries:
                if not entry["headsign"] and entry["trip_id"] in last_seq_per_trip:
                    last_sid = last_seq_per_trip[entry["trip_id"]][1]
                    entry["headsign"] = stops.get(last_sid, {}).get("name", "")

        gtfs["stop_times"].setdefault(stop_id, []).extend(our_entries)


async def _get_vehicle_dict(coord, session, city_cfg) -> dict:
    """Load and cache vehicle capabilities dictionary (CSV or JSON)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_vehicles", {})
    cache_key = coord.provider
    
    # TTL check (1 hour)
    cached = cache.get(cache_key)
    if cached and isinstance(cached, dict):
        ts = cached.get("_ts", 0)
        if ts and (dt_util.now().timestamp() - ts < 3600):
            return cached.get("data", {})
    
    try:
        async with session.get(city_cfg["vehicles_url"], timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
            if resp.status != 200:
                return {}
            text = await resp.text()

        if city_cfg.get("vehicles_format") == "json":
            import json
            raw = json.loads(text)
            result = {}
            for _key, v in raw.items():
                num = v.get("num", "")
                if not num or num.startswith("??"):
                    continue
                low = v.get("low")
                result[num] = {
                    "hf_lf_le": low == 2,
                    "ramp": low in (1, 2),
                    "vehicle_model": v.get("type", ""),
                }
            cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
            return result

        if city_cfg.get("vehicles_format") == "ttss_positions":
            import json
            raw = json.loads(text)
            pos = raw.get("pos", {})
            result = {}
            # Also fetch tram positions if configured
            urls = [city_cfg["vehicles_url"]]
            if city_cfg.get("vehicles_url_tram"):
                urls.append(city_cfg["vehicles_url_tram"])
            # Parse first response (already fetched)
            for _vid, v in pos.items():
                vtype = v.get("type", {})
                num = vtype.get("num", "")
                if not num or num.startswith("??"):
                    continue
                low = vtype.get("low")
                ac = vtype.get("ac")
                result[num] = {
                    "hf_lf_le": low == 2,
                    "ramp": low in (1, 2),
                    "air_conditioner": ac in (1, 2),
                    "vehicle_model": vtype.get("type", ""),
                }
            # Fetch tram positions if separate URL
            if city_cfg.get("vehicles_url_tram"):
                try:
                    async with session.get(city_cfg["vehicles_url_tram"], timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp2:
                        if resp2.status == 200:
                            text2 = await resp2.text()
                            raw2 = json.loads(text2)
                            for _vid, v in raw2.get("pos", {}).items():
                                vtype = v.get("type", {})
                                num = vtype.get("num", "")
                                if not num or num.startswith("??"):
                                    continue
                                low = vtype.get("low")
                                ac = vtype.get("ac")
                                result[num] = {
                                    "hf_lf_le": low == 2,
                                    "ramp": low in (1, 2),
                                    "air_conditioner": ac in (1, 2),
                                    "vehicle_model": vtype.get("type", ""),
                                }
                except Exception:
                    pass
            cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
            return result

        # Default: CSV format (Poznań)
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
        cache[cache_key] = {"data": result, "_ts": dt_util.now().timestamp()}
        return result
    except Exception:
        return {}


async def _get_rt_delays(session, rt_url: str) -> dict:
    """Fetch GTFS-RT TripUpdates and return {trip_id_stop_id: delay_seconds}."""
    from google.transit import gtfs_realtime_pb2
    
    last_err = None
    for attempt in range(3):
        try:
            async with session.get(rt_url, timeout=aiohttp.ClientTimeout(total=15), ssl=False) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.read()

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(data)
            return _parse_rt_feed(feed)
        except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as e:
            last_err = e
            if attempt < 2:
                _LOGGER.debug("GTFS-RT attempt %d failed: %s, retrying...", attempt + 1, e)
                await asyncio.sleep((1, 3)[attempt])
        except Exception as e:
            _LOGGER.debug("GTFS-RT: failed to fetch RT data from %s: %s", rt_url, e)
            return {}
    
    if last_err:
        _LOGGER.debug("GTFS-RT: all retries failed for %s: %s", rt_url, last_err)
    return {}


def _parse_rt_feed(feed) -> dict:
    """Parse a GTFS-RT FeedMessage into {trip_id_stop_id: (delay, vehicle_label)}."""
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
