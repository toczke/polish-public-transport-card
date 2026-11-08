"""GTFS-RT provider for cities with protobuf realtime feeds (Poznań, Lublin, Białystok, etc.)."""

import asyncio
import csv
import logging
import zipfile
from datetime import timedelta
from io import BytesIO, StringIO, TextIOWrapper

import aiohttp

from homeassistant.util import dt as dt_util

from .const import CONF_STOP_ID, CONF_STOPS, DOMAIN, MAX_DEPARTURES

_LOGGER = logging.getLogger(__name__)

from .gtfsrt_cities import GTFSRT_CITIES
from .gtfsrt_parser import _parse_gtfs_zip, _parse_stop_times_for, _parse_stop_times_from_raw, _parse_gtfsrt_positions, _parse_rt_feed, _get_tomorrow_departures, _release_gtfs_raw, resolve_stop_id
from .gtfsrt_gzm import _get_gzm_gtfs_url


def _configured_stop_ids(coord) -> list[str]:
    """Return every stop configured in the hub entry that owns this coordinator."""
    entry = getattr(coord, "config_entry", None)
    data = getattr(entry, "data", {}) if entry is not None else {}
    ids: list[str] = []
    for stop in data.get(CONF_STOPS) or []:
        stop_id = str(stop.get("stop_id") or stop.get("id") or "").strip()
        if stop_id:
            ids.append(stop_id)
    if not ids:
        stop_id = str(data.get(CONF_STOP_ID) or "").strip()
        if stop_id:
            ids.append(stop_id)
    if not ids:
        ids.append(str(coord.stop_id))
    return ids


async def fetch(coord: "PolishTransportCoordinator") -> dict:
    """Fetch departures using static GTFS + GTFS-RT TripUpdates."""
    session = await coord._get_session()
    now = dt_util.now()
    city_cfg = GTFSRT_CITIES.get(coord.provider)
    if not city_cfg:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name, "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    if city_cfg.get("unavailable"):
        _LOGGER.warning(
            "GTFS-RT: %s has no public GTFS source anymore (%s)",
            coord.provider,
            coord.stop_name or coord.stop_id,
        )
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name, "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Load static GTFS (cached daily)
    gtfs = await _get_gtfs_data(coord, session, city_cfg, now)
    if not gtfs:
        return {"stop_id": coord.stop_id, "stop_name": coord.stop_name or f"Przystanek {coord.stop_id}", "provider": coord.provider, "departures": [], "last_update": now.isoformat()}

    # Get stop name
    stop_id = str(coord.stop_id)
    if stop_id not in gtfs["stops"]:
        resolved = resolve_stop_id(gtfs["stops"], stop_id, coord.stop_name)
        if resolved:
            _LOGGER.info(
                "GTFS-RT %s: stop %s (%s) changed in the feed; using %s (%s)",
                coord.provider,
                stop_id,
                coord.stop_name,
                resolved,
                gtfs["stops"][resolved].get("name", ""),
            )
            stop_id = resolved
        else:
            _LOGGER.warning(
                "GTFS-RT %s: stop %s (%s) is not present in the current GTFS feed",
                coord.provider,
                stop_id,
                coord.stop_name,
            )

    if not coord.stop_name:
        coord.stop_name = gtfs["stops"].get(stop_id, {}).get("name", f"Przystanek {stop_id}")

    # Get scheduled departures for this stop
    if stop_id not in gtfs["stop_times"] and gtfs.get("_raw"):
        await coord.hass.async_add_executor_job(_parse_stop_times_for, gtfs, stop_id)
    stop_times = gtfs["stop_times"].get(stop_id, [])
    if gtfs.get("_raw"):
        await coord.hass.async_add_executor_job(
            _release_gtfs_raw, gtfs, _configured_stop_ids(coord), now
        )
    _LOGGER.debug(
        "GTFS-RT %s: feed has %d stops and %d scheduled rows for stop %s",
        coord.provider,
        len(gtfs["stops"]),
        len(stop_times),
        stop_id,
    )

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

        # Apply RT delay only when this exact trip has its own update. A
        # route-level fallback used to copy one vehicle/delay to every later
        # trip on the route (Poznań issue #52).
        delay_sec = 0
        is_realtime = False
        vehicle_code = ""
        rt_key = f"{trip_id}_{stop_id}"
        rt_key_seq = f"{trip_id}_seq{st.get('stop_sequence', '')}"
        for key in (rt_key, rt_key_seq, trip_id):
            if key in delays:
                delay_sec, vehicle_code = delays[key]
                is_realtime = True
                break

        # A bus waiting at the first stop often reports a large negative delay
        # until it leaves the terminus. Show the scheduled time instead.
        try:
            stop_sequence = int(st.get("stop_sequence") or 0)
        except (TypeError, ValueError):
            stop_sequence = 0
        if is_realtime and delay_sec < 0 and stop_sequence <= 1:
            delay_sec = 0

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
            "route_color": gtfs["routes"].get(route_id, {}).get("color"),
            "vehicle_code": vehicle_code if is_realtime else None,
            "trip_id": trip_id,
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
                if v.get("floor_height"):
                    d["floor_height"] = v["floor_height"]
                if v.get("drive_type"):
                    d["drive_type"] = v["drive_type"]
                if v.get("length"):
                    d["vehicle_length"] = v["length"]

    # Enrich with GPS positions if positions_url is configured
    await _enrich_with_gps_positions(coord, session, city_cfg, departures)

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
    if len(unique) < 5:
        tomorrow = now + timedelta(days=1)
        tomorrow_prefix = f"{tomorrow:%Y%m%d}_"
        tomorrow_key = f"{tomorrow_prefix}{stop_id}"
        tomorrow_cache = gtfs.setdefault("_tomorrow_departures", {})
        for old_key in list(tomorrow_cache):
            if not old_key.startswith(tomorrow_prefix):
                tomorrow_cache.pop(old_key)
        if tomorrow_key not in tomorrow_cache and gtfs.get("_raw"):
            tomorrow_cache[tomorrow_key] = await coord.hass.async_add_executor_job(
                _get_tomorrow_departures, gtfs, stop_id, tomorrow, now
            )
        tomorrow_deps = tomorrow_cache.get(tomorrow_key, [])
        for d in tomorrow_deps:
            est = (d.get("estimated_time") or "")[:16]
            key = (d.get("route"), d.get("headsign"), est)
            if key not in seen:
                seen.add(key)
                unique.append(d)
                if len(unique) >= MAX_DEPARTURES:
                    break

    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name,
        "provider": coord.provider,
        "departures": unique[:MAX_DEPARTURES],
        "last_update": now.isoformat(),
        **({"resolved_stop_id": stop_id} if stop_id != str(coord.stop_id) else {}),
    }


async def _get_gtfs_data(coord, session, city_cfg, now):
    """Load GTFS data once when several stops refresh concurrently."""
    domain_data = coord.hass.data[DOMAIN]
    locks = domain_data.setdefault("_gtfsrt_locks", {})
    lock = locks.setdefault(coord.provider, asyncio.Lock())
    async with lock:
        return await _get_gtfs_data_locked(coord, session, city_cfg, now)


async def _download_zip(coord, session, url, path_suffix):
    import os
    zip_path = coord.hass.config.path(f"polish_transport_gtfs_{coord.provider}{path_suffix}.zip")
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            data = await resp.read()
        def save_zip():
            with open(zip_path, "wb") as f:
                f.write(data)
        await coord.hass.async_add_executor_job(save_zip)
        return data
    except Exception as e:
        def load_zip():
            if os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    return f.read()
            return None
        data = await coord.hass.async_add_executor_job(load_zip)
        if not data:
            _LOGGER.warning("GTFS-RT: failed to fetch GTFS for %s (%s): %s", coord.provider, path_suffix, e)
            return None
        return data

async def _get_gtfs_data_locked(coord, session, city_cfg, now):
    """Load and cache parsed GTFS data (daily)."""
    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_cache", {})
    today = now.strftime("%Y%m%d")
    cache_key = f"{coord.provider}_{today}"

    if cache.get(cache_key):
        gtfs = cache[cache_key]
        if coord.stop_id in gtfs["stop_times"]:
            return gtfs
        if gtfs.get("_raw"):
            await coord.hass.async_add_executor_job(_parse_stop_times_for, gtfs, coord.stop_id)
            return gtfs
        # The raw zip was released after the other hub stops were parsed. A new
        # stop needs a fresh archive so its schedule can be extracted.
        cache.pop(cache_key, None)

    prefix = f"{coord.provider}_"
    for old_key in list(cache.keys()):
        if old_key.startswith(prefix) and old_key != cache_key:
            old_gtfs = cache.pop(old_key, None)
            if old_gtfs:
                old_gtfs.pop("_raw", None)
                old_gtfs.pop("_raw_tram", None)
            _LOGGER.debug("Cleaned old GTFS cache: %s", old_key)

    try:
        gtfs_url = city_cfg.get("gtfs_url")
        if not gtfs_url and city_cfg.get("gtfs_package_id"):
            gtfs_url = await _get_gzm_gtfs_url(session, city_cfg["gtfs_package_id"], now.date())
            if not gtfs_url:
                _LOGGER.warning("GTFS-RT: could not get dynamic URL for GZM")
                return None

        # P1 Performance: Parallel GTFS downloads
        tasks = [_download_zip(coord, session, gtfs_url, "")]
        if city_cfg.get("gtfs_url_tram"):
            tasks.append(_download_zip(coord, session, city_cfg["gtfs_url_tram"], "_tram"))
            
        results = await asyncio.gather(*tasks)
        data = results[0]
        data2 = results[1] if len(results) > 1 else None

        if not data:
            _LOGGER.warning("GTFS-RT: Network failed and no local fallback for %s", coord.provider)
            return None

        gtfs = await coord.hass.async_add_executor_job(_parse_gtfs_zip, data)

        if city_cfg.get("gtfs_url_tram"):
            if data2:
                try:
                    gtfs2 = await coord.hass.async_add_executor_job(_parse_gtfs_zip, data2)
                    gtfs["stops"].update(gtfs2["stops"])
                    gtfs["routes"].update(gtfs2["routes"])
                    gtfs["trips"].update(gtfs2["trips"])
                    gtfs["_raw_tram"] = data2
                except Exception as e:
                    _LOGGER.debug("GTFS-RT: failed to parse tram GTFS for %s: %s", coord.provider, e)

        cache[cache_key] = gtfs
        # Parse stop_times for current stop
        if coord.stop_id not in gtfs["stop_times"]:
            await coord.hass.async_add_executor_job(_parse_stop_times_for, gtfs, coord.stop_id)
        return gtfs
    except Exception as e:
        _LOGGER.warning("GTFS-RT: failed to load GTFS for %s: %s", coord.provider, e)
        return cache.get(cache_key)


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
        async with session.get(city_cfg["vehicles_url"], timeout=aiohttp.ClientTimeout(total=15)) as resp:
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
                    async with session.get(city_cfg["vehicles_url_tram"], timeout=aiohttp.ClientTimeout(total=15)) as resp2:
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
                except Exception as exc:
                    _LOGGER.debug("Failed to load tram vehicles: %s", exc)
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


async def _enrich_with_gps_positions(coord, session, city_cfg, departures):
    """Fetch vehicle GPS positions and enrich departures with vehicle_lat/lng."""
    url = city_cfg.get("positions_url")
    if not url or not departures:
        return

    cache = coord.hass.data[DOMAIN].setdefault("_gtfsrt_positions", {})
    now_ts = dt_util.now().timestamp()
    cached = cache.get(coord.provider)
    if cached and now_ts - cached.get("_ts", 0) < 30:
        _apply_positions(departures, cached.get("data", {}))
        return

    positions = {}
    try:
        if "/api/v2/vehicles" in url:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("data", []):
                        vn = item.get("vehicle", {}).get("number")
                        pos = item.get("position", {})
                        if vn and "latitude" in pos and "longitude" in pos:
                            positions[str(vn)] = {"lat": pos["latitude"], "lng": pos["longitude"], "bearing": pos.get("bearing"), "speed": pos.get("velocity")}
        elif "positions.json" in url:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for p in data.get("positions", []):
                        sn = p.get("side_number")
                        tid = p.get("trip_id")
                        lat = p.get("lat")
                        lon = p.get("lon")
                        if not lat or not lon:
                            continue
                        entry = {"lat": lat, "lng": lon, "bearing": p.get("bearing")}
                        if sn:
                            positions[str(sn)] = entry
                        if tid:
                            positions[tid] = entry
        elif city_cfg.get("positions_format") == "gtfsrt_protobuf" or url.endswith(".pb"):
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    positions = _parse_gtfsrt_positions(await resp.read())
        _apply_positions(departures, positions)
        cache[coord.provider] = {"data": positions, "_ts": now_ts}
    except Exception as e:
        _LOGGER.debug("GPS positions failed for %s: %s", coord.provider, e)


def _apply_position(d: dict, position: dict) -> bool:
    """Copy one position onto a departure, rejecting the 0,0 sentinel."""
    if abs(position["lat"]) < 0.0001 and abs(position["lng"]) < 0.0001:
        return False
    d["vehicle_lat"] = position["lat"]
    d["vehicle_lng"] = position["lng"]
    if position.get("bearing") is not None:
        d["vehicle_direction"] = position["bearing"]
    if position.get("speed") is not None:
        d["vehicle_speed"] = round(position["speed"] * 3.6)
    return True


def _apply_positions(departures, positions):
    """Add vehicle_lat/lng to departures matching positions by vehicle_code/trip.

    The route_id fallback is limited to one departure per vehicle. Assigning a
    route position to every departure on that route painted the same bus on all
    later trips (Poznań issue #52).
    """
    route_positions: dict[str, list[tuple[str, dict]]] = {}
    for vid, entry in positions.items():
        rid = entry.get("route_id")
        if rid:
            route_positions.setdefault(rid, []).append((vid, entry))

    used: set[str] = set()
    for d in departures:
        vc = d.get("vehicle_code", "")
        tid = d.get("trip_id", "")
        key = None
        if vc and vc in positions:
            key = vc
        elif tid and tid in positions:
            key = tid
        if key and key not in used:
            if _apply_position(d, positions[key]):
                used.add(key)

    for route, candidates in route_positions.items():
        available = [(vid, entry) for vid, entry in candidates if vid not in used]
        if not available:
            continue
        unmatched = [
            d
            for d in departures
            if "vehicle_lat" not in d
            and not d.get("vehicle_code")
            and d.get("route") == route
        ]
        unmatched.sort(
            key=lambda d: d.get("estimated_time") or d.get("theoretical_time") or ""
        )
        for d, (vid, entry) in zip(unmatched, available):
            if _apply_position(d, entry):
                used.add(vid)


async def _get_rt_delays(session, rt_url: str) -> dict:
    """Fetch GTFS-RT TripUpdates and return {trip_id_stop_id: delay_seconds}."""
    from google.transit import gtfs_realtime_pb2
    
    last_err = None
    for attempt in range(3):
        try:
            async with session.get(rt_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
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
                await asyncio.sleep([1, 3, 7][attempt])
        except Exception as e:
            _LOGGER.debug("GTFS-RT: failed to parse RT data from %s: %s", rt_url, e)
            return {}
    
    if last_err:
        _LOGGER.debug("GTFS-RT: all retries failed for %s: %s", rt_url, last_err)
    return {}


