"""PLK rail provider."""

import asyncio
from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLK_API_BASE, PROVIDER_PLK

_LOGGER = logging.getLogger(__name__)


async def fetch(coord) -> dict:
    """Fetch departures from PLK OpenData API (PR/SKM/IC)."""
    session = await coord._get_session()
    now = dt_util.now()
    today = now.strftime("%Y-%m-%d")
    headers = {"Content-Type": "application/json"}
    if coord.api_key:
        headers["X-API-Key"] = coord.api_key

    departures = []

    plk_cache = coord.hass.data[DOMAIN].setdefault("_plk_cache", {})
    plk_lock = coord.hass.data[DOMAIN].setdefault("_plk_lock", asyncio.Lock())

    async with plk_lock:
        cache_age = (now - plk_cache.get("_ts", now - timedelta(days=1))).total_seconds()

        if cache_age > coord.update_interval.total_seconds():
            all_plk_stations = set()
            for coords in coord.hass.data[DOMAIN].get("_coordinators", {}).values():
                for c in (coords if isinstance(coords, list) else [coords]):
                    if c.provider == PROVIDER_PLK:
                        all_plk_stations.add(c.stop_id)
            stations_param = ",".join(all_plk_stations)

            try:
                ops_url = f"{PLK_API_BASE}/operations"
                params = {
                    "stations": stations_param,
                    "withPlanned": "true",
                    "pageSize": "100",
                }
                ops_data_raw = await _fetch_plk_with_retry(session, ops_url, params, headers)
                if ops_data_raw:
                    plk_cache["_data"] = ops_data_raw
                    plk_cache["_ts"] = now
                    plk_cache["_req_count"] = plk_cache.get("_req_count", 0) + 1
            except UpdateFailed:
                raise
            except Exception as e:
                if "429" in str(e):
                    _LOGGER.warning("PLK API rate limit hit, skipping this cycle")
                    plk_cache["_429_count"] = plk_cache.get("_429_count", 0) + 1
                else:
                    _LOGGER.debug("PLK operations fetch failed for %s: %s", stations_param, e)

    ops_data = plk_cache.get("_data")

    # Fetch schedules — per station, cached for the day
    sched_cache_key = f"_sched_{coord.stop_id}"
    sched_cache_date_key = f"_sched_date_{coord.stop_id}"
    sched_data = None
    cached_date = plk_cache.get(sched_cache_date_key)

    if cached_date == today and plk_cache.get(sched_cache_key):
        sched_data = plk_cache[sched_cache_key]
    else:
        try:
            sched_url = f"{PLK_API_BASE}/schedules"
            params = {
                "stations": coord.stop_id,
                "dateFrom": today,
                "dateTo": today,
                "dictionaries": "true",
                "fullRoute": "true",
            }
            sched_data = await _fetch_plk_with_retry(session, sched_url, params, headers)
            if sched_data:
                plk_cache[sched_cache_key] = sched_data
                plk_cache[sched_cache_date_key] = today
                plk_cache["_req_count"] = plk_cache.get("_req_count", 0) + 1
        except Exception as e:
            if "429" in str(e):
                _LOGGER.warning("PLK API rate limit hit on schedules")
            else:
                _LOGGER.debug("PLK schedules fetch failed for %s: %s", coord.stop_id, e)

    if not sched_data:
        sched_data = plk_cache.get(sched_cache_key)

    # Resolve station name
    if not coord.stop_name and sched_data:
        dicts = sched_data.get("dictionaries", {})
        stations = dicts.get("stations", {})
        entry = stations.get(str(coord.stop_id), {})
        coord.stop_name = entry if isinstance(entry, str) else entry.get("name", f"Stacja {coord.stop_id}")

    # Build realtime map from operations
    rt_map: dict[str, dict] = {}
    if ops_data:
        trains_list = ops_data.get("trains") or ops_data.get("routes") or ops_data.get("items") or []
        if not trains_list and isinstance(ops_data.get("data"), dict):
            trains_list = ops_data["data"].get("trains", [])
        if not trains_list and isinstance(ops_data, list):
            trains_list = ops_data
        _LOGGER.debug(
            "PLK operations for %s: top-level keys=%s, trains=%d",
            coord.stop_id,
            list(ops_data.keys()) if isinstance(ops_data, dict) else "list",
            len(trains_list) if trains_list else 0,
        )
        for train in (trains_list or []):
            for st in train.get("stations", []):
                if str(st.get("stationId")) == str(coord.stop_id):
                    delay = 0
                    actual_dep = st.get("actualDeparture")
                    planned_dep = st.get("plannedDeparture")
                    if actual_dep and planned_dep:
                        try:
                            a = dt_util.parse_datetime(actual_dep)
                            p = dt_util.parse_datetime(planned_dep)
                            if a and p:
                                delay = int((a - p).total_seconds() / 60)
                        except (ValueError, TypeError):
                            pass
                    rt_info = {
                        "delay": delay,
                        "cancelled": st.get("cancelled", False),
                        "confirmed": st.get("isConfirmed", False),
                    }
                    for k in ("trainNumber", "nationalNumber", "orderId", "trainOrderId"):
                        v = train.get(k)
                        if v:
                            rt_map[str(v)] = rt_info
                    break
        _LOGGER.debug("PLK rt_map keys for %s: %s", coord.stop_id, list(rt_map.keys())[:10])

    # Parse schedule data
    if sched_data:
        dicts = sched_data.get("dictionaries", {})
        carriers = dicts.get("carriers", {})
        stations_dict = dicts.get("stations", {})

        for route in sched_data.get("routes", []):
            route_stations = route.get("stations", [])
            carrier_code = route.get("carrierCode", "")
            carrier_name = carriers.get(carrier_code, carrier_code)
            train_number = str(
                route.get("nationalNumber")
                or route.get("trainOrderId")
                or route.get("orderId")
                or route.get("trainNumber")
                or ""
            )
            category = route.get("commercialCategorySymbol", carrier_code)

            for i, stop in enumerate(route_stations):
                if str(stop.get("stationId")) != str(coord.stop_id):
                    continue

                dep_time_str = stop.get("departureTime")
                if not dep_time_str:
                    continue

                operating_date = route.get("operatingDate", today)
                dep_dt = _time_to_datetime(operating_date, dep_time_str, stop.get("departureDay", 0))
                if dep_dt < now - timedelta(minutes=2):
                    continue

                dest_stations = route_stations[i + 1:]
                dest_id = dest_stations[-1]["stationId"] if dest_stations else ""
                dest_entry = stations_dict.get(str(dest_id), "")
                destination = dest_entry if isinstance(dest_entry, str) else dest_entry.get("name", "")

                rt = {}
                is_realtime = False
                for candidate in (
                    train_number,
                    str(route.get("nationalNumber") or ""),
                    str(route.get("orderId") or ""),
                    str(route.get("trainOrderId") or ""),
                    str(route.get("trainNumber") or ""),
                    str(stop.get("departureTrainNumber") or ""),
                ):
                    if candidate and candidate in rt_map:
                        rt = rt_map[candidate]
                        is_realtime = True
                        break
                delay_min = rt.get("delay", 0)
                is_cancelled = rt.get("cancelled", False)

                departures.append({
                    "route": category or "R",
                    "headsign": destination or "—",
                    "estimated_time": (dep_dt + timedelta(minutes=delay_min)).isoformat() if is_realtime else dep_dt.isoformat(),
                    "theoretical_time": dep_dt.isoformat(),
                    "delay_seconds": delay_min * 60,
                    "realtime": is_realtime,
                    "vehicle_type": "train",
                    "bike_allowed": None,
                    "wheelchair_accessible": None,
                    "air_conditioning": None,
                    "carrier": carrier_name,
                    "category": category,
                    "train_number": str(stop.get("departureTrainNumber") or train_number or ""),
                    "platform": stop.get("departurePlatform") or stop.get("platform") or "",
                    "track": stop.get("departureTrack") or stop.get("track") or "",
                    "cancelled": is_cancelled,
                    "provider": PROVIDER_PLK,
                })
                break

    departures.sort(key=lambda x: x.get("estimated_time") or "")
    departures = departures[:30]
    return {
        "stop_id": coord.stop_id,
        "stop_name": coord.stop_name or f"Stacja {coord.stop_id}",
        "provider": PROVIDER_PLK,
        "departures": departures,
        "last_update": now.isoformat(),
    }


def _time_to_datetime(operating_date: str, time_str: str, day_offset: int = 0) -> datetime:
    """Convert PLK time (HH:MM:SS or PT duration) + operating date to datetime."""
    # Handle ISO 8601 duration format PT{hours}H{minutes}M{seconds}S
    if time_str.startswith("PT"):
        h, m, s = 0, 0, 0
        import re
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", time_str)
        if match:
            h = int(match.group(1) or 0)
            m = int(match.group(2) or 0)
            s = int(match.group(3) or 0)
    else:
        parts = time_str.split(":")
        h = int(parts[0]) if len(parts) > 0 else 0
        m = int(parts[1]) if len(parts) > 1 else 0
        s = int(parts[2]) if len(parts) > 2 else 0
    base = datetime.strptime(operating_date[:10], "%Y-%m-%d").replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return base.replace(hour=0, minute=0, second=0) + timedelta(days=day_offset, hours=h, minutes=m, seconds=s)


async def _fetch_plk_with_retry(session, url: str, params: dict, headers: dict) -> dict | None:
    """Fetch PLK API with retry on network errors, handling 429 separately."""
    RETRY_DELAYS = (1, 3, 7)
    last_err = None
    for attempt in range(3):
        try:
            async with session.get(
                url, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 429:
                    raise Exception(f"429 rate limit")
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientConnectorError, aiohttp.ServerDisconnectedError, asyncio.TimeoutError) as err:
            last_err = err
            if attempt < 2:
                _LOGGER.debug("PLK API attempt %d failed: %s, retrying...", attempt + 1, err)
                await asyncio.sleep(RETRY_DELAYS[attempt])
    if last_err:
        raise last_err
    return None
