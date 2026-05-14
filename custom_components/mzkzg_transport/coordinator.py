"""Data coordinator for MZKZG Transport."""



import asyncio

from datetime import datetime, timedelta

import logging

import re



import aiohttp



from homeassistant.core import HomeAssistant

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.util import dt as dt_util

# Compatible timezone getter (works on HA 2024.4+ and newer)
def _get_tz():
    return getattr(dt_util, "get_default_time_zone", lambda: dt_util.DEFAULT_TIME_ZONE)()



from .const import (

    DEFAULT_SCAN_INTERVAL,

    DOMAIN,

    KIEDYPRZYJEDZIE_BASE_URLS,

    KIEDYPRZYJEDZIE_PROVIDERS,

    PLK_API_BASE,

    TIME4BUS_PROVIDERS,

    TIME4BUS_TCZEW_LIVE_DEPARTURES_URL,

    TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL,

    PROVIDER_MZK,

    PROVIDER_PLK,

    PROVIDER_TCZEW,

    PROVIDER_ZKM,

    PROVIDER_ZTM,

    ZKM_GDYNIA_DELAYS_URL,

    ZKM_GDYNIA_ROUTES_URL,

    ZTM_GDANSK_DEPARTURES_URL,

    STOP_ID_PATTERN,

)



_LOGGER = logging.getLogger(__name__)

_STOP_ID_RE = re.compile(STOP_ID_PATTERN)





class MzkzgTransportCoordinator(DataUpdateCoordinator):

    """Coordinator that fetches departure data from ZTM/ZKM APIs."""



    def __init__(

        self,

        hass: HomeAssistant,

        stop_id: str,

        provider: str,

        name: str,

        api_key: str = "",

        plk_tier: str = "basic",

    ) -> None:

        """Initialize coordinator."""

        from .const import PLK_DAILY_LIMITS, PLK_TIER_LIMITS



        # Count PLK stations to calculate safe interval

        plk_stations = sum(1 for e in hass.data.get(DOMAIN, {}).get("_coordinators", {}).values()

                          if getattr(e, "provider", None) == PROVIDER_PLK) + (1 if provider == PROVIDER_PLK else 0)

        hourly_limit = PLK_TIER_LIMITS.get(plk_tier, 100)

        daily_limit = PLK_DAILY_LIMITS.get(plk_tier, 1000)

        # 1 operations req (shared) + 1 schedules req (daily, negligible) per refresh

        # Use 80% of limit as safety margin

        safe_refreshes = int(hourly_limit * 0.8) // max(plk_stations, 1)

        plk_interval = max(60, 3600 // max(safe_refreshes, 1))

        safe_daily_ops = max(int(daily_limit * 0.8) - plk_stations, 1)

        plk_daily_interval = max(60, -(-86400 // safe_daily_ops))

        super().__init__(

            hass,

            _LOGGER,

            name=f"{DOMAIN}_{stop_id}",

            update_interval=timedelta(

                seconds=max(plk_interval, plk_daily_interval) if provider == PROVIDER_PLK else DEFAULT_SCAN_INTERVAL

            ),

        )

        self.stop_id = stop_id

        if not _STOP_ID_RE.match(str(stop_id)):

            raise ValueError(f"Invalid stop_id: {stop_id}")

        self.provider = provider

        self.stop_name = name

        self.api_key = api_key

        self._routes_map: dict[str, str] = {}

        self._routes_load_failed_at: float = 0



    async def _get_session(self) -> aiohttp.ClientSession:

        return async_get_clientsession(self.hass)



    async def _async_update_data(self) -> dict:

        """Fetch departures from the appropriate API."""

        try:

            if self.provider == PROVIDER_ZTM:

                return await self._fetch_ztm()

            if self.provider == PROVIDER_MZK:

                return await self._fetch_mzk()

            if self.provider == PROVIDER_PLK:

                return await self._fetch_plk()

            if self.provider in TIME4BUS_PROVIDERS:

                return await self._fetch_time4bus_tczew()

            if self.provider in KIEDYPRZYJEDZIE_PROVIDERS:

                return await self._fetch_kiedyprzyjedzie()

            return await self._fetch_zkm()

        except Exception as err:
            _LOGGER.debug("Fetch error for %s (%s): %s", self.stop_id, self.provider, err, exc_info=True)
            raise UpdateFailed(f"Error fetching data: {err}") from err



    async def _fetch_ztm(self) -> dict:

        """Fetch departures from ZTM Gdańsk TRISTAR API."""

        session = await self._get_session()

        url = f"{ZTM_GDANSK_DEPARTURES_URL}?stopId={self.stop_id}"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:

            resp.raise_for_status()

            data = await resp.json()



        # Load vehicle fleet cache (once per day)

        fleet = await self._get_ztm_fleet(session)



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

                "vehicle_type": self._ztm_vehicle_type(d.get("routeShortName") or d.get("routeId")),

                "bike_allowed": vinfo.get("bikeHolders", 0) > 0 if vinfo else d.get("bikeAllowed"),

                "wheelchair_accessible": vinfo.get("wheelchairsRamp") if vinfo else d.get("wheelchairAccessible"),

                "air_conditioning": vinfo.get("airConditioning") if vinfo else d.get("airConditioning"),

                "usb": vinfo.get("usb", False),

                "ticket_machine": vinfo.get("ticketMachine", False),

                "vehicle_code": vcode,

                "provider": PROVIDER_ZTM,

            })



        departures.sort(key=lambda x: x.get("estimated_time") or "")

        return {

            "stop_id": self.stop_id,

            "stop_name": self.stop_name,

            "provider": PROVIDER_ZTM,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    async def _fetch_zkm(self) -> dict:

        """Fetch departures from ZKM Gdynia ZDiZ API."""

        session = await self._get_session()



        # Load routes map if empty

        if not self._routes_map and (dt_util.now().timestamp() - self._routes_load_failed_at > 3600):

            await self._load_zkm_routes(session)



        url = f"{ZKM_GDYNIA_DELAYS_URL}?stopId={self.stop_id}"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:

            resp.raise_for_status()

            data = await resp.json()



        departures = []

        now = dt_util.now()

        for d in data.get("delay", []):

            route_id = d.get("routeId") or d.get("routeShortName")

            route_name = self._routes_map.get(str(route_id), str(route_id))

            time_str = d.get("estimatedTime") or d.get("theoreticalTime") or d.get("time")

            if not time_str:

                continue



            # ZDiZ returns HH:MM:SS format

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

                "vehicle_type": self._zkm_vehicle_type(route_name),

                "bike_allowed": d.get("bikeAllowed", None),

                "wheelchair_accessible": d.get("wheelchairAccessible", None),

                "air_conditioning": d.get("airConditioning", None),

                "vehicle_code": str(d.get("vehicleCode") or d.get("vehicleId") or "") or None,

                "provider": PROVIDER_ZKM,

            })



        departures.sort(key=lambda x: x.get("estimated_time") or "")

        return {

            "stop_id": self.stop_id,

            "stop_name": self.stop_name,

            "provider": PROVIDER_ZKM,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    async def _fetch_kiedyprzyjedzie(self) -> dict:

        """Fetch departures from kiedyPrzyjedzie carriers."""

        session = await self._get_session()

        base_url = self._kiedyprzyjedzie_base_url()

        now = dt_util.now()



        async with session.get(

            f"{base_url}/api/departures/{self.stop_id}",

            timeout=aiohttp.ClientTimeout(total=15),

        ) as resp:

            resp.raise_for_status()

            data = await resp.json()



        api_timestamp = data.get("timestamp")

        reference_dt = (

            datetime.fromtimestamp(api_timestamp, tz=_get_tz())

            if isinstance(api_timestamp, (int, float))

            else now

        )

        directions = {

            str(k): str(v)

            for k, v in (data.get("directions") or {}).items()

            if k is not None and v is not None

        }



        if not self.stop_name:

            self.stop_name = str(data.get("station_name") or f"Przystanek {self.stop_id}")



        departures = []

        for row in data.get("rows", []):

            estimated_dt, estimated_realtime = self._parse_kiedyprzyjedzie_time(

                row.get("time"), reference_dt

            )

            theoretical_dt, _ = self._parse_kiedyprzyjedzie_time(

                row.get("static_time") or row.get("time"), reference_dt

            )

            if estimated_dt is None:

                continue

            if theoretical_dt is None:

                theoretical_dt = estimated_dt



            time_diff = row.get("time_diff")

            delay_seconds = 0

            if time_diff not in (None, "", 0, 0.0):

                try:

                    delay_minutes = int(float(time_diff))

                except (TypeError, ValueError):

                    delay_minutes = 0

                if delay_minutes:

                    delay_seconds = delay_minutes * 60

                estimated_dt = theoretical_dt + timedelta(seconds=delay_seconds)

            else:

                delay_seconds = int((estimated_dt - theoretical_dt).total_seconds())



            if estimated_dt < now - timedelta(minutes=1):

                continue



            direction_id = row.get("direction_id")

            direction = directions.get(str(direction_id)) or "—"

            vehicle_attributes = [str(attr) for attr in row.get("vehicle_attributes", []) if attr]

            realtime = bool(row.get("is_estimated")) or estimated_realtime or delay_seconds != 0



            departures.append({

                "route": str(row.get("line_name") or "?"),

                "headsign": direction,

                "estimated_time": estimated_dt.isoformat(),

                "theoretical_time": theoretical_dt.isoformat(),

                "delay_seconds": delay_seconds,

                "realtime": realtime,

                "vehicle_type": "bus",

                "bike_allowed": "bike_transport" in vehicle_attributes,

                "wheelchair_accessible": "low_floor" in vehicle_attributes or "wheelchair" in vehicle_attributes,

                "air_conditioning": "ac" in vehicle_attributes,

                "ticket_machine": "ticket_machine" in vehicle_attributes,

                "vehicle_attributes": vehicle_attributes,

                "platform": row.get("platform"),

                "trip_id": row.get("trip_id"),

                "trip_execution_id": row.get("trip_execution_id"),

                "trip_index": row.get("trip_index"),

                "cancelled": row.get("canceled", False),

                "provider": self.provider,

            })



        departures.sort(key=lambda x: x.get("estimated_time") or "")

        return {

            "stop_id": self.stop_id,

            "stop_name": self.stop_name,

            "provider": self.provider,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    def _kiedyprzyjedzie_base_url(self) -> str:

        """Return the base URL for the configured kiedyPrzyjedzie carrier."""

        return KIEDYPRZYJEDZIE_BASE_URLS[self.provider]



    @staticmethod

    def _parse_kiedyprzyjedzie_time(value, reference_dt: datetime) -> tuple[datetime | None, bool]:

        """Parse kiedyPrzyjedzie time strings into absolute datetimes."""

        if value is None:

            return None, False



        text = str(value).strip()

        if not text:

            return None, False



        relative_match = re.match(r"^(\d+)\s*min(?:\.|utes?)?$", text, re.IGNORECASE)

        if relative_match:

            minutes = int(relative_match.group(1))

            return reference_dt + timedelta(minutes=minutes), True



        clock_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)

        if clock_match:

            hour = int(clock_match.group(1))

            minute = int(clock_match.group(2))

            second = int(clock_match.group(3) or 0)

            dep_dt = reference_dt.replace(hour=hour, minute=minute, second=second, microsecond=0)

            if (dep_dt - reference_dt).total_seconds() < -3600:

                dep_dt += timedelta(days=1)

            return dep_dt, False



        return None, False



    async def _fetch_time4bus_tczew(self) -> dict:

        """Fetch departures from Time4BUS for Tczew with live fallback."""

        session = await self._get_session()

        now = dt_util.now()

        live_url = f"{TIME4BUS_TCZEW_LIVE_DEPARTURES_URL}/{self.stop_id}/departures"

        schedule_url = f"{TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL}/{self.stop_id}/departures?date={now:%Y-%m-%d}"



        live_data = None

        schedule_data = None

        departures = []



        try:

            async with session.get(live_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:

                if resp.status == 404:

                    live_data = None

                else:

                    resp.raise_for_status()

                    live_data = await resp.json()

            departures = self._parse_time4bus_live_departures(live_data, now)

        except Exception as err:

            _LOGGER.debug("Time4BUS live fetch failed for %s: %s", self.stop_id, err)

            departures = []



        if not departures:

            try:

                async with session.get(schedule_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:

                    resp.raise_for_status()

                    schedule_data = await resp.json()

                departures = self._parse_time4bus_schedule_departures(schedule_data, now)

            except Exception as err:

                _LOGGER.debug("Time4BUS schedule fetch failed for %s: %s", self.stop_id, err)

                if not departures:

                    raise



        stop_name = self.stop_name

        if not stop_name:

            stop_name = self._extract_time4bus_stop_name(live_data, schedule_data) or f"Przystanek {self.stop_id}"

            self.stop_name = stop_name



        departures.sort(key=lambda x: x.get("estimated_time") or "")

        return {

            "stop_id": self.stop_id,

            "stop_name": stop_name,

            "provider": self.provider,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    @staticmethod

    def _extract_time4bus_stop_name(live_data, schedule_data) -> str | None:

        """Extract a human-readable stop name from Time4BUS payloads."""

        if isinstance(live_data, dict):

            for key in ("stopName", "name", "station_name"):

                value = live_data.get(key)

                if value:

                    return str(value)

        if isinstance(schedule_data, dict):

            for key in ("stopName", "name", "station_name"):

                value = schedule_data.get(key)

                if value:

                    return str(value)

        return None



    @staticmethod

    def _parse_time4bus_clock_time(value, reference_dt: datetime) -> datetime | None:

        """Parse Time4BUS clock times into absolute datetimes."""

        if value is None:

            return None

        text = str(value).strip()

        if not text:

            return None

        clock_match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", text)

        if not clock_match:

            return None

        hour = int(clock_match.group(1))

        minute = int(clock_match.group(2))

        second = int(clock_match.group(3) or 0)

        dep_dt = reference_dt.replace(hour=hour, minute=minute, second=second, microsecond=0)

        if (dep_dt - reference_dt).total_seconds() < -3600:

            dep_dt += timedelta(days=1)

        return dep_dt



    def _parse_time4bus_live_departures(self, data, reference_dt: datetime) -> list[dict]:

        """Normalize live Time4BUS departures."""

        departures = []

        if not isinstance(data, dict):

            return departures



        for row in data.get("departures", []) or []:

            if not isinstance(row, dict):

                continue

            leave_time = row.get("leaveTime")

            plan_time = row.get("planTime")

            if leave_time is None:

                continue

            try:

                estimated_dt = datetime.fromtimestamp(float(leave_time) / 1000, tz=_get_tz())

            except (TypeError, ValueError, OSError):

                continue

            if plan_time is not None:

                try:

                    theoretical_dt = datetime.fromtimestamp(float(plan_time) / 1000, tz=_get_tz())

                except (TypeError, ValueError, OSError):

                    theoretical_dt = estimated_dt

            else:

                theoretical_dt = estimated_dt



            if estimated_dt < reference_dt - timedelta(minutes=1):

                continue



            delay_seconds = int(round((estimated_dt - theoretical_dt).total_seconds()))

            vehicle_info = row.get("vehicleInfo") or {}

            if not isinstance(vehicle_info, dict):

                vehicle_info = {}

            departures.append({

                "route": str(row.get("line") or row.get("lineName") or "?"),

                "headsign": str(row.get("direction") or row.get("lastStop") or "?"),

                "estimated_time": estimated_dt.isoformat(),

                "theoretical_time": theoretical_dt.isoformat(),

                "delay_seconds": delay_seconds,

                "realtime": bool(row.get("isReal")) or delay_seconds != 0,

                "vehicle_type": "bus",

                "bike_allowed": None,

                "wheelchair_accessible": bool(vehicle_info.get("lowFloor")) if vehicle_info else None,

                "air_conditioning": vehicle_info.get("airConditioning") if vehicle_info else None,

                "ticket_machine": bool(vehicle_info.get("ticketMachine")) if vehicle_info else None,

                "vehicle_code": vehicle_info.get("name") if vehicle_info else None,

                "platform": row.get("platform"),

                "track": row.get("track"),

                "trip_id": row.get("tid"),

                "provider": self.provider,

            })



        return departures



    def _parse_time4bus_schedule_departures(self, data, reference_dt: datetime) -> list[dict]:

        """Normalize fallback Time4BUS schedule departures."""

        departures = []

        if not isinstance(data, dict):

            return departures



        for row in data.get("items", []) or []:

            if not isinstance(row, dict):

                continue

            time_text = row.get("departureTime") or row.get("arrivalTime")

            estimated_dt = self._parse_time4bus_clock_time(time_text, reference_dt)

            if estimated_dt is None:

                continue

            if estimated_dt < reference_dt - timedelta(minutes=1):

                continue



            departures.append({

                "route": str(row.get("lineName") or row.get("lineLongName") or row.get("lineId") or "?"),

                "headsign": str(row.get("directionName") or "?"),

                "estimated_time": estimated_dt.isoformat(),

                "theoretical_time": estimated_dt.isoformat(),

                "delay_seconds": 0,

                "realtime": False,

                "vehicle_type": "bus",

                "bike_allowed": None,

                "wheelchair_accessible": None,

                "air_conditioning": None,

                "platform": row.get("platform"),

                "track": row.get("track"),

                "trip_id": row.get("tripId"),

                "provider": self.provider,

            })



        return departures



    async def _fetch_plk(self) -> dict:

        """Fetch departures from PLK OpenData API (PR/SKM/IC)."""

        session = await self._get_session()

        now = dt_util.now()

        today = now.strftime("%Y-%m-%d")

        headers = {"Content-Type": "application/json"}

        if self.api_key:

            headers["X-API-Key"] = self.api_key



        departures = []



        # Share operations data across all PLK coordinators to reduce API calls

        plk_cache = self.hass.data[DOMAIN].setdefault("_plk_cache", {})

        plk_lock = self.hass.data[DOMAIN].setdefault("_plk_lock", asyncio.Lock())



        async with plk_lock:

            cache_age = (now - plk_cache.get("_ts", now - timedelta(days=1))).total_seconds()



            if cache_age > self.update_interval.total_seconds():  # Respect tier interval

                # Collect all PLK station IDs

                all_plk_stations = set()

                for coord in self.hass.data[DOMAIN].get("_coordinators", {}).values():

                    if coord.provider == PROVIDER_PLK:

                        all_plk_stations.add(coord.stop_id)

                stations_param = ",".join(all_plk_stations)



                try:

                    ops_url = f"{PLK_API_BASE}/operations"

                    params = {

                        "stations": stations_param,

                        "withPlanned": "true",

                        "pageSize": "100",

                    }

                    async with session.get(

                        ops_url, params=params, headers=headers,

                        timeout=aiohttp.ClientTimeout(total=20),

                    ) as resp:

                        if resp.status == 429:

                            _LOGGER.warning("PLK API rate limit hit, skipping this cycle")

                            plk_cache["_429_count"] = plk_cache.get("_429_count", 0) + 1

                        elif resp.status == 200:

                            plk_cache["_data"] = await resp.json()

                            plk_cache["_ts"] = now

                            plk_cache["_req_count"] = plk_cache.get("_req_count", 0) + 1

                except UpdateFailed:

                    raise

                except Exception:

                    _LOGGER.debug("PLK operations fetch failed for %s", stations_param)



        ops_data = plk_cache.get("_data")



        # Fetch schedules (planned) — per station, cached for the day

        sched_cache_key = f"_sched_{self.stop_id}"

        sched_cache_date_key = f"_sched_date_{self.stop_id}"

        sched_data = None

        cached_date = plk_cache.get(sched_cache_date_key)



        if cached_date == today and plk_cache.get(sched_cache_key):

            sched_data = plk_cache[sched_cache_key]

        else:

            try:

                sched_url = f"{PLK_API_BASE}/schedules"

                params = {

                    "stations": self.stop_id,

                    "dateFrom": today,

                    "dateTo": today,

                    "dictionaries": "true",

                    "fullRoute": "true",

                }

                async with session.get(

                    sched_url, params=params, headers=headers,

                    timeout=aiohttp.ClientTimeout(total=20),

                ) as resp:

                    if resp.status == 429:

                        _LOGGER.warning("PLK API rate limit hit on schedules")

                    elif resp.status == 200:

                        sched_data = await resp.json()

                        plk_cache[sched_cache_key] = sched_data

                        plk_cache[sched_cache_date_key] = today

                        plk_cache["_req_count"] = plk_cache.get("_req_count", 0) + 1

            except Exception:

                _LOGGER.debug("PLK schedules fetch failed for %s", self.stop_id)



        # Fallback to cached schedule

        if not sched_data:

            sched_data = plk_cache.get(sched_cache_key)



        # Resolve station name

        if not self.stop_name and sched_data:

            dicts = sched_data.get("dictionaries", {})

            stations = dicts.get("stations", {})

            entry = stations.get(str(self.stop_id), {})

            self.stop_name = entry if isinstance(entry, str) else entry.get("name", f"Stacja {self.stop_id}")



        # Build realtime map from operations — index by multiple keys for matching

        rt_map: dict[str, dict] = {}

        if ops_data:

            # Operations API may return trains under different keys

            trains_list = ops_data.get("trains") or ops_data.get("routes") or ops_data.get("items") or []

            if not trains_list and isinstance(ops_data.get("data"), dict):

                trains_list = ops_data["data"].get("trains", [])

            if not trains_list and isinstance(ops_data, list):

                trains_list = ops_data

            _LOGGER.debug(

                "PLK operations for %s: top-level keys=%s, trains=%d",

                self.stop_id,

                list(ops_data.keys()) if isinstance(ops_data, dict) else "list",

                len(trains_list) if trains_list else 0,

            )

            for train in (trains_list or []):

                for st in train.get("stations", []):

                    if str(st.get("stationId")) == str(self.stop_id):

                        # Calculate delay from actual vs planned times

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

                        # Index by all possible identifiers

                        for k in ("trainNumber", "nationalNumber", "orderId", "trainOrderId"):

                            v = train.get(k)

                            if v:

                                rt_map[str(v)] = rt_info

                        break

            _LOGGER.debug("PLK rt_map keys for %s: %s", self.stop_id, list(rt_map.keys())[:10])



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

                    if str(stop.get("stationId")) != str(self.stop_id):

                        continue



                    dep_time_str = stop.get("departureTime")

                    if not dep_time_str:

                        continue



                    # Parse HH:MM:SS duration into datetime

                    operating_date = route.get("operatingDate", today)

                    dep_dt = self._plk_time_to_datetime(

                        operating_date, dep_time_str, stop.get("departureDay", 0)

                    )

                    if dep_dt < now - timedelta(minutes=2):

                        continue



                    # Destination = last station

                    dest_stations = route_stations[i + 1:]

                    dest_id = dest_stations[-1]["stationId"] if dest_stations else ""

                    dest_entry = stations_dict.get(str(dest_id), "")

                    destination = dest_entry if isinstance(dest_entry, str) else dest_entry.get("name", "")



                    # Realtime info — try matching by multiple identifiers

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

        departures = departures[:30]  # Limit to nearest 30

        return {

            "stop_id": self.stop_id,

            "stop_name": self.stop_name or f"Stacja {self.stop_id}",

            "provider": PROVIDER_PLK,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    @staticmethod

    def _plk_time_to_datetime(operating_date: str, time_str: str, day_offset: int = 0) -> datetime:

        """Convert PLK time (HH:MM:SS duration) + operating date to datetime."""

        parts = time_str.replace("PT", "").replace("H", ":").replace("M", ":").replace("S", "").split(":")

        if len(parts) >= 2:

            h, m = int(parts[0]), int(parts[1])

            s = int(parts[2]) if len(parts) > 2 else 0

        else:

            h, m, s = 0, 0, 0

        base = datetime.strptime(operating_date[:10], "%Y-%m-%d").replace(tzinfo=_get_tz())

        return base.replace(hour=0, minute=0, second=0) + timedelta(days=day_offset, hours=h, minutes=m, seconds=s)



    async def _fetch_mzk(self) -> dict:

        """Fetch departures from MZK Wejherowo static GTFS."""

        from .gtfs_provider import get_gtfs_data



        gtfs = await get_gtfs_data()

        now = dt_util.now()



        if not self.stop_name:

            stop_info = gtfs.stops.get(self.stop_id, {})

            self.stop_name = stop_info.get("name", f"Przystanek {self.stop_id}")



        departures = gtfs.get_departures(self.stop_id, now)

        return {

            "stop_id": self.stop_id,

            "stop_name": self.stop_name,

            "provider": PROVIDER_MZK,

            "departures": departures,

            "last_update": now.isoformat(),

        }



    async def _get_ztm_fleet(self, session: aiohttp.ClientSession) -> dict:

        """Get ZTM vehicle fleet data (cached weekly in hass.data)."""

        cache = self.hass.data[DOMAIN].setdefault("_ztm_fleet", {})

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



    async def _load_zkm_routes(self, session: aiohttp.ClientSession) -> None:

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

                            self._routes_map[str(r["routeId"])] = str(r["routeShortName"])

                else:

                    self._routes_load_failed_at = dt_util.now().timestamp()

        except Exception:

            _LOGGER.warning("Could not load ZKM routes")

            self._routes_load_failed_at = dt_util.now().timestamp()



    @staticmethod

    def _ztm_vehicle_type(route_id) -> str:

        """Determine vehicle type for ZTM Gdańsk."""

        s = str(route_id or "")

        n = int(s) if s.isdigit() else None

        if n is not None and n < 100:

            return "tram"

        return "bus"



    @staticmethod

    def _zkm_vehicle_type(route_name) -> str:

        """Determine vehicle type for ZKM Gdynia."""

        s = str(route_name or "")

        n = int(s) if s.isdigit() else None

        if n is not None and 20 <= n <= 29:

            return "trolleybus"

        return "bus"



