"""MPK Łódź provider using rozklady.lodz.pl XML API with GTFS-RT enrichment."""

import asyncio
import os
import io
import csv
import logging
import zipfile
from datetime import datetime, timedelta
from xml.etree import ElementTree

import aiohttp

from homeassistant.util import dt as dt_util

from .const import CONF_FALLBACK_MIN, DEFAULT_FALLBACK_MIN, DOMAIN
from .http_utils import fetch_with_retry

_LOGGER = logging.getLogger(__name__)
LODZ_URL = "http://rozklady.lodz.pl/Home/GetTimetableReal"
LODZ_TRIP_UPDATES = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/trip_updates.bin"
LODZ_VEHICLE_POSITIONS = "https://otwarte.miasto.lodz.pl/wp-content/uploads/2025/06/vehicle_positions.bin"
LODZ_GTFS_URL = "https://cdn.zbiorkom.live/gtfs/lodz.zip"
MAX_STOP_NR = 20
_GTFS_MAX_HOURS = 3


def _fallback_min(coord) -> int:
    return coord._options.get(CONF_FALLBACK_MIN, DEFAULT_FALLBACK_MIN) if hasattr(coord, "_options") else DEFAULT_FALLBACK_MIN


async def fetch(coord: "MzkzgTransportCoordinator") -> dict:
    """Fetch realtime departures from MPK Łódź.

    stop_id formats:
      - "busStopId:stopNr" e.g. "205:4" — single stop board
      - "busStopId"         e.g. "205"   — group stop (all boards merged)
    """
    session = await coord._get_session()
    now = dt_util.now()
    fb_min = _fallback_min(coord)

    parts = str(coord.stop_id).split(":")
    stop_id = parts[0]
    stop_nr = parts[1] if len(parts) > 1 else None

    if stop_nr is not None:
        stop_nrs = [stop_nr]
    else:
        stop_nrs = [str(n) for n in range(1, MAX_STOP_NR + 1)]

    all_departures = []
    all_departures_from_api = False
    stop_name = None

    tasks = [_fetch_stop_board(session, stop_id, nr) for nr in stop_nrs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for nr, result in zip(stop_nrs, results):
        if isinstance(result, Exception):
            _LOGGER.debug("Łódź stop board %s:%s failed: %s", stop_id, nr, result)
            continue
        if result is None:
            continue
        board_text, board_stop_name = result
        if board_stop_name and not stop_name:
            stop_name = board_stop_name
        if not stop_name:
            stop_name = board_stop_name or f"Przystanek {stop_id}"
        deps = _parse_board_xml(board_text, now, coord)
        if deps:
            all_departures_from_api = True
        for d in deps:
            d["stop_board"] = nr
        all_departures.extend(deps)

    if not stop_name:
        stop_name = f"Przystanek {stop_id}"

    if not coord.stop_name:
        coord.stop_name = stop_name or f"Przystanek {coord.stop_id}"

    gtfs_data = None
    try:
        gtfs_data = await _load_gtfs(coord, session)
        delays = await _fetch_delays(session)
        if delays and gtfs_data and "stop_mapping" in gtfs_data:
            _enrich_with_delays(all_departures, delays, gtfs_data["stop_mapping"], stop_id)
    except Exception as exc:
        _LOGGER.debug("Łódź GTFS-RT enrichment failed: %s", exc)

    await _enrich_lodz_vehicle_positions(session, all_departures)

    all_departures = _deduplicate_prefer_rt(all_departures)
    _LOGGER.debug("Łódź fallback check: %d departures (min %d)", len(all_departures), fb_min)
    if len(all_departures) < fb_min:
        try:
            if gtfs_data is None:
                gtfs_data = await _load_gtfs(coord, session)
            if gtfs_data and "gtfs" in gtfs_data:
                gtfs = gtfs_data["gtfs"]
                gtfs_stop_ids = gtfs_data.get("stop_mapping", {}).get(str(stop_id), [str(stop_id)])
                _LOGGER.debug("Łódź GTFS stop_ids for fallback: %s", gtfs_stop_ids)
                seen = set()
                seen_rt = set()
                for d in all_departures:
                    key_time = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
                    h = (d.get("headsign") or "").strip()
                    seen.add((d.get("route"), h, key_time))
                    seen_rt.add((d.get("route"), key_time))
                for gtfs_sid in gtfs_stop_ids:
                    gtfs_deps = _get_gtfs_stop_departures(gtfs, gtfs_sid, now, coord)
                    _LOGGER.debug("Łódź GTFS stop %s produced %d deps", gtfs_sid, len(gtfs_deps))
                    for d in gtfs_deps:
                        key_time = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
                        h = (d.get("headsign") or "").strip()
                        key = (d.get("route"), h, key_time)
                        if key in seen:
                            continue
                        if not h and (d.get("route"), key_time) in seen_rt:
                            continue
                        seen.add(key)
                        all_departures.append(d)
        except Exception as exc:
            _LOGGER.debug("Łódź GTFS schedule fallback failed: %s", exc)
    _LOGGER.debug("Łódź after fallback: %d departures", len(all_departures))

    # Merge old RT departures not yet expired when API returned 0
    if not all_departures_from_api and coord.data:
        old_deps = coord.data.get("departures", [])
        now_ts = now.timestamp()
        merged_rt = 0
        for d in old_deps:
            if d.get("realtime"):
                et = d.get("estimated_time")
                if et:
                    try:
                        et_ts = datetime.fromisoformat(et).timestamp()
                    except (ValueError, TypeError):
                        continue
                    if et_ts > now_ts - 120:
                        merged_rt += 1
                        all_departures.append(d)
        if merged_rt:
            _LOGGER.debug("Łódź preserved %d old RT departures", merged_rt)

    all_departures.sort(key=lambda x: x.get("estimated_time") or "")
    return_count = len(all_departures[:30])
    _LOGGER.debug("Łódź returning %d departures (capped from %d)", return_count, len(all_departures))
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": all_departures[:30],
        "last_update": now.isoformat(),
    }


def _deduplicate_prefer_rt(departures: list) -> list:
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


async def _fetch_stop_board(session, stop_id: str, stop_nr: str):
    """Fetch XML for a single stop board."""
    url = f"{LODZ_URL}?busStopId={stop_id}&busStopNr={stop_nr}"
    text = await fetch_with_retry(session, url, as_text=True)
    if not text or not text.strip():
        return None
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return None
    stop_el = root.find("Stop")
    stop_name = stop_el.get("name") if stop_el is not None else None
    return text, stop_name


def _parse_board_xml(text: str, now, coord) -> list:
    """Parse departures from a single stop board XML."""
    root = ElementTree.fromstring(text)
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

                estimated_dt = None
                if "min" in tm:
                    try:
                        minutes = int(tm.replace("min", "").strip())
                    except ValueError:
                        minutes = 0
                    estimated_dt = now + timedelta(minutes=minutes)
                else:
                    try:
                        th = s.get("th", "0") or "0"
                        h, m = int(th), int(tm)
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
    return departures


async def _load_gtfs(coord, session=None) -> dict | None:
    """Load Łódź GTFS data with persistent file-based caching + HTTP HEAD freshness check.

    Returns {"stop_mapping": {...}, "gtfs": {...}} or None on failure.
    Cached in memory per day; persisted to disk zip across restarts.
    """
    cache = coord.hass.data[DOMAIN].setdefault("_lodz_gtfs_data", {})
    today = dt_util.now().strftime("%Y%m%d")
    if cache.get("_date") == today and "stop_mapping" in cache and "gtfs" in cache:
        return cache

    zip_bytes = await _get_gtfs_zip(coord, session)
    if zip_bytes is None:
        if cache.get("gtfs"):
            _LOGGER.debug("Łódź GTFS download failed, using stale cache")
            return cache
        return None

    try:
        z = zipfile.ZipFile(io.BytesIO(zip_bytes))

        # Build stop mapping from stops.txt
        mapping: dict[str, list[str]] = {}
        with z.open("stops.txt") as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
            for row in reader:
                stop_code = row.get("stop_code", "").strip()
                stop_id = row.get("stop_id", "").strip()
                if stop_code and stop_id:
                    mapping.setdefault(stop_code, []).append(stop_id)
                if stop_id:
                    mapping.setdefault(stop_id, []).append(stop_id)

        # Parse full GTFS schedule
        from .provider_gtfsrt import _parse_gtfs_zip
        gtfs = await coord.hass.async_add_executor_job(_parse_gtfs_zip, zip_bytes)

        result = {"stop_mapping": mapping, "gtfs": gtfs, "_date": today}
        cache.clear()
        cache.update(result)
        _LOGGER.debug("Łódź GTFS data loaded: %d stops mapped", len(mapping))
        return result
    except Exception as exc:
        _LOGGER.debug("Łódź GTFS data parse failed: %s", exc)
        return cache if cache.get("gtfs") else None


async def _get_gtfs_zip(coord, session=None) -> bytes | None:
    """Get GTFS zip bytes from disk cache or download, with HTTP HEAD freshness check."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    config_dir = coord.hass.config.path()
    cache_dir = os.path.join(config_dir, DOMAIN)
    loop = coord.hass.loop

    def _ensure_dir():
        os.makedirs(cache_dir, exist_ok=True)
    await loop.run_in_executor(None, _ensure_dir)
    
    zip_path = os.path.join(cache_dir, "lodz_gtfs.zip")
    meta_path = os.path.join(cache_dir, "lodz_gtfs_meta.txt")

    # Check if disk cache is fresh (skip download if same-day HEAD already passed)
    today = dt_util.now().strftime("%Y%m%d")
    disk_date = ""

    def _read_meta():
        try:
            return open(meta_path).read().strip()
        except (OSError, IOError):
            return ""
    
    def _meta_exists():
        return os.path.exists(meta_path)
    
    if await loop.run_in_executor(None, _meta_exists):
        disk_date = await loop.run_in_executor(None, _read_meta)

    http_session = session or async_get_clientsession(coord.hass)

    def _zip_exists():
        return os.path.exists(zip_path)

    def _read_zip():
        try:
            with open(zip_path, "rb") as f:
                return f.read()
        except (OSError, IOError):
            return None

    if disk_date == today and await loop.run_in_executor(None, _zip_exists):
        data = await loop.run_in_executor(None, _read_zip)
        if data:
            _LOGGER.debug("Łódź GTFS loaded from disk cache (%d bytes)", len(data))
            return data

    # Check freshness with HEAD request
    need_download = True
    if await loop.run_in_executor(None, _zip_exists):
        try:
            async with http_session.head(
                LODZ_GTFS_URL, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    remote_etag = resp.headers.get("ETag", "")
                    remote_last_modified = resp.headers.get("Last-Modified", "")
                    local_meta = ""

                    def _read_meta_val():
                        try:
                            with open(meta_path) as f:
                                content = f.read().strip()
                                return content.split("|")[-1] if "|" in content else ""
                        except Exception:
                            return ""
                    
                    if await loop.run_in_executor(None, _meta_exists):
                        local_meta = await loop.run_in_executor(None, _read_meta_val)
                    
                    if (remote_etag and local_meta == remote_etag) or \
                       (not remote_etag and remote_last_modified and local_meta == remote_last_modified):
                        need_download = False
        except Exception:
            pass

    if need_download:
        try:
            async with http_session.get(
                LODZ_GTFS_URL, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Łódź GTFS download failed: HTTP %d", resp.status)
                    return None
                data = await resp.read()
        except Exception as exc:
            _LOGGER.debug("Łódź GTFS download error: %s", exc)
            return None

        def _write_cache():
            try:
                with open(zip_path, "wb") as f:
                    f.write(data)
                return True
            except Exception:
                return False

        await loop.run_in_executor(None, _write_cache)
        
        remote_etag = resp.headers.get("ETag", "")
        remote_last_modified = resp.headers.get("Last-Modified", "")
        meta_value = f"{today}|{remote_etag or remote_last_modified}"
        
        def _write_meta():
            try:
                with open(meta_path, "w") as f:
                    f.write(meta_value)
            except Exception:
                pass
        
        await loop.run_in_executor(None, _write_meta)

        _LOGGER.debug("Łódź GTFS downloaded: %d bytes", len(data))
        return data

    # Disk cache is fresh enough
    data = await loop.run_in_executor(None, _read_zip)
    if data:
        _LOGGER.debug("Łódź GTFS loaded from disk cache (fresh, %d bytes)", len(data))
        return data
    return None


def _get_gtfs_stop_departures(gtfs: dict, gtfs_stop_id: str, now, coord) -> list:
    """Get scheduled departures from GTFS for a specific stop (within _GTFS_MAX_HOURS)."""
    from .provider_gtfsrt import _parse_stop_times_for

    stop_id_key = str(gtfs_stop_id)
    if stop_id_key not in gtfs.get("stop_times", {}):
        _parse_stop_times_for(gtfs, stop_id_key)

    stop_times = gtfs.get("stop_times", {}).get(stop_id_key, [])
    departures = []
    cutoff = now + timedelta(hours=_GTFS_MAX_HOURS)

    for st in stop_times:
        trip_id = st["trip_id"]
        route_id = st["route_id"]
        route_name = gtfs.get("routes", {}).get(route_id, {}).get("short_name", route_id)
        headsign = st.get("headsign") or gtfs.get("trips", {}).get(trip_id, {}).get("headsign", "")

        h, m, s = st["departure_time"]
        dep_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h, minutes=m, seconds=s)
        if dep_dt < now - timedelta(minutes=1):
            continue
        if dep_dt > cutoff:
            continue

        departures.append({
            "route": route_name,
            "headsign": headsign,
            "estimated_time": dep_dt.isoformat(),
            "theoretical_time": dep_dt.isoformat(),
            "delay_seconds": 0,
            "realtime": False,
            "vehicle_type": gtfs.get("routes", {}).get(route_id, {}).get("type", "bus"),
            "provider": coord.provider,
        })

    return departures


async def _fetch_delays(session) -> dict:
    """Fetch GTFS-RT trip updates and return {(route_id, gtfs_stop_id): delay_seconds}."""
    try:
        from google.transit import gtfs_realtime_pb2

        async with session.get(
            LODZ_TRIP_UPDATES, timeout=10
        ) as resp:
            if resp.status != 200:
                return {}
            data = await resp.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(data)

        delays = {}
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            tu = entity.trip_update
            route_id = tu.trip.route_id
            for stu in tu.stop_time_update:
                delay = (
                    stu.departure.delay if stu.HasField("departure") else
                    stu.arrival.delay if stu.HasField("arrival") else 0
                )
                key = (route_id, stu.stop_id)
                delays[key] = delay
        return delays
    except Exception:
        return {}


async def _enrich_lodz_vehicle_positions(session, departures: list) -> None:
    """Fetch GTFS-RT vehicle positions and add vehicle_lat/lng to departures."""
    if not any(d.get("vehicle_code") for d in departures):
        return

    positions = {}
    try:
        from google.transit import gtfs_realtime_pb2

        async with session.get(LODZ_VEHICLE_POSITIONS, timeout=10) as resp:
            if resp.status != 200:
                return
            raw = await resp.read()

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(raw)
        for entity in feed.entity:
            if not entity.HasField("vehicle"):
                continue
            v = entity.vehicle
            vid = v.vehicle.id or v.vehicle.label or ""
            vid = vid.split("/")[-1] if "/" in vid else vid
            if not vid or not v.HasField("position"):
                continue
            positions[vid] = {
                "lat": v.position.latitude,
                "lng": v.position.longitude,
            }
            try:
                positions[vid]["bearing"] = v.position.bearing if v.position.HasField("bearing") else None
            except (ValueError, AttributeError):
                pass
            try:
                positions[vid]["speed"] = v.position.speed if v.position.HasField("speed") else None
            except (ValueError, AttributeError):
                pass

        for d in departures:
            vc = d.get("vehicle_code", "")
            if vc and vc in positions:
                p = positions[vc]
                d["vehicle_lat"] = p["lat"]
                d["vehicle_lng"] = p["lng"]
                if p.get("bearing") is not None:
                    d["vehicle_direction"] = p["bearing"]
                if p.get("speed") is not None:
                    d["vehicle_speed"] = round(p["speed"] * 3.6)
    except Exception as e:
        _LOGGER.debug("Łódź vehicle positions failed: %s", e)


def _enrich_with_delays(departures: list, delays: dict, stop_mapping: dict, stop_id: str) -> None:
    """Apply GTFS-RT delay data by matching (route_id, GTFS_stop_id).

    Uses stop_mapping {rozklady_stop_id: [gtfs_stop_id, ...]} built from GTFS static data.
    """
    gtfs_stop_ids = stop_mapping.get(stop_id, [])
    if not gtfs_stop_ids:
        return

    for d in departures:
        route = d.get("route", "")
        for gtfs_sid in gtfs_stop_ids:
            delay = delays.get((route, gtfs_sid))
            if delay is not None:
                d["delay_seconds"] = delay
                d["realtime"] = True
                if delay and d.get("theoretical_time"):
                    try:
                        theo = datetime.fromisoformat(
                            d["theoretical_time"].replace("Z", "+00:00")
                        )
                        d["estimated_time"] = (
                            theo + timedelta(seconds=delay)
                        ).isoformat()
                    except (ValueError, AttributeError):
                        pass
                break
