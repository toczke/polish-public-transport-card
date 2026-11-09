"""Data coordinator for Polish Transport."""

from datetime import timedelta
import logging
import re
import time

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.util import dt as dt_util

def _get_tz():
    return getattr(dt_util, "get_default_time_zone", lambda: dt_util.DEFAULT_TIME_ZONE)()

from .const import (
    CONF_OFFLINE_ONLY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GTFSRT_PROVIDERS,
    KIEDYPRZYJEDZIE_PROVIDERS,
    PROVIDER_KRAKOW,
    PROVIDER_LODZ,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_ZTM,
    STOP_ID_PATTERN,
    TIME4BUS_PROVIDERS,
)
from .offline import async_load_snapshot, async_save_snapshot, replay_snapshot

_LOGGER = logging.getLogger(__name__)
_STOP_ID_RE = re.compile(STOP_ID_PATTERN)


class PolishTransportCoordinator(DataUpdateCoordinator):
    """Coordinator that fetches departure data from transport APIs."""

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

        plk_stations = sum(
            1 for coords in hass.data.get(DOMAIN, {}).get("_coordinators", {}).values()
            for c in (coords if isinstance(coords, list) else [coords])
            if getattr(c, "provider", None) == PROVIDER_PLK
        ) + (1 if provider == PROVIDER_PLK else 0)
        hourly_limit = PLK_TIER_LIMITS.get(plk_tier, 100)
        daily_limit = PLK_DAILY_LIMITS.get(plk_tier, 1000)
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
        self.stop_lat: float | None = None
        self.stop_lon: float | None = None
        self._options: dict = {}
        self._routes_map: dict[str, str] = {}
        self._routes_load_failed_at: float = 0
        self._last_offline_save: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        return async_get_clientsession(self.hass)

    # Backward-compatible shims (used by tests)
    async def _fetch_ztm(self):
        from . import provider_ztm
        return await provider_ztm.fetch(self)

    async def _fetch_zkm(self):
        from . import provider_zkm
        return await provider_zkm.fetch(self)

    async def _fetch_kiedyprzyjedzie(self):
        from . import provider_kiedyprzyjedzie
        return await provider_kiedyprzyjedzie.fetch(self)

    async def _fetch_time4bus_tczew(self):
        from . import provider_time4bus
        return await provider_time4bus.fetch(self)

    async def _fetch_plk(self):
        from . import provider_plk
        return await provider_plk.fetch(self)

    async def _fetch_mzk(self):
        from . import provider_mzk
        return await provider_mzk.fetch(self)

    @staticmethod
    def _ztm_vehicle_type(route_id) -> str:
        from .provider_ztm import _vehicle_type
        return _vehicle_type(route_id)

    @staticmethod
    def _zkm_vehicle_type(route_name) -> str:
        from .provider_zkm import _vehicle_type
        return _vehicle_type(route_name)

    @staticmethod
    def _plk_time_to_datetime(operating_date: str, time_str: str, day_offset: int = 0):
        from .provider_plk import _time_to_datetime
        return _time_to_datetime(operating_date, time_str, day_offset)

    @staticmethod
    def _parse_kiedyprzyjedzie_time(value, reference_dt):
        from .provider_kiedyprzyjedzie import _parse_time
        return _parse_time(value, reference_dt)

    @staticmethod
    def _headsigns_compatible(first: str, second: str) -> bool:
        """Return True when two headsigns describe the same destination."""
        a = (first or "").strip().casefold()
        b = (second or "").strip().casefold()
        if not a or not b or a == b:
            return True
        return a.startswith(b) or b.startswith(a)

    @staticmethod
    def _merge_departure(base: dict, extra: dict) -> dict:
        """Merge two rows for the same departure, keeping the richer fields."""
        # A realtime row wins as the base so delay and vehicle data survive.
        if extra.get("realtime") and not base.get("realtime"):
            base, extra = extra, base
        merged = dict(base)
        for key, value in extra.items():
            if key == "headsign":
                continue
            if merged.get(key) in (None, "", [], {}) and value not in (None, "", [], {}):
                merged[key] = value
        # Keep the more specific terminus ("Brzeźno Dom Zdrojowy" over "Brzeźno").
        base_hs = str(base.get("headsign") or "")
        extra_hs = str(extra.get("headsign") or "")
        if len(extra_hs) > len(base_hs):
            merged["headsign"] = extra["headsign"]
        return merged

    @staticmethod
    def _deduplicate_prefer_rt(departures: list) -> list:
        """Merge schedule and realtime rows for the same departure.

        Route + theoretical time is the stable identity. Headsigns may differ
        when one is a prefix of the other, because providers often return both
        a short and a full terminus for the same trip (for example "Brzeźno"
        and "Brzeźno Dom Zdrojowy"). The merged row keeps the more specific
        headsign and fills missing vehicle/trip fields from the other source.
        """
        groups: list[dict] = []
        for d in departures:
            route = d.get("route")
            t = (d.get("theoretical_time") or d.get("estimated_time") or "")[:16]
            headsign = d.get("headsign") or ""
            match = None
            for group in groups:
                if (
                    group["route"] == route
                    and group["time"] == t
                    and PolishTransportCoordinator._headsigns_compatible(
                        group["base"].get("headsign"), headsign
                    )
                ):
                    match = group
                    break
            if match:
                match["base"] = PolishTransportCoordinator._merge_departure(match["base"], d)
            else:
                groups.append({"route": route, "time": t, "base": d})
        return [group["base"] for group in groups]

    async def _async_update_data(self) -> dict:
        """Fetch departures from the appropriate provider module."""
        from homeassistant.util import dt as dt_util
        from .const import CONF_SLEEP_ENABLED, CONF_SLEEP_START, CONF_SLEEP_END, DEFAULT_SLEEP_START, DEFAULT_SLEEP_END

        now = dt_util.now()

        # Sleep mode from options
        if not self._options.get(CONF_SLEEP_ENABLED, True):
            is_sleeping = False
        else:
            sleep_start = self._options.get(CONF_SLEEP_START, DEFAULT_SLEEP_START)
            sleep_end = self._options.get(CONF_SLEEP_END, DEFAULT_SLEEP_END)
            try:
                sh, sm = map(int, sleep_start.split(":"))
                eh, em = map(int, sleep_end.split(":"))
                now_min = now.hour * 60 + now.minute
                start_min = sh * 60 + sm
                end_min = eh * 60 + em
                if start_min <= end_min:
                    is_sleeping = start_min <= now_min < end_min
                else:
                    is_sleeping = now_min >= start_min or now_min < end_min
            except (ValueError, AttributeError):
                is_sleeping = False

        if is_sleeping:
            if self.data:
                return self.data
            return {
                "stop_id": self.stop_id,
                "stop_name": self.stop_name or f"Przystanek {self.stop_id}",
                "provider": self.provider,
                "departures": [],
                "last_update": now.isoformat(),
                "sleep_mode": True,
            }

        if self._options.get(CONF_OFFLINE_ONLY, False):
            return await self._async_offline_data(now)

        try:
            if self.provider == PROVIDER_ZTM:
                from . import provider_ztm
                data = await provider_ztm.fetch(self)
            elif self.provider == PROVIDER_MZK:
                from . import provider_mzk
                data = await provider_mzk.fetch(self)
            elif self.provider == PROVIDER_LODZ:
                from . import provider_lodz
                data = await provider_lodz.fetch(self)
            elif self.provider == PROVIDER_KRAKOW:
                from . import provider_krakow
                data = await provider_krakow.fetch(self)
            elif self.provider in GTFSRT_PROVIDERS:
                from . import provider_gtfsrt
                data = await provider_gtfsrt.fetch(self)
            elif self.provider == PROVIDER_PLK:
                from . import provider_plk
                data = await provider_plk.fetch(self)
            elif self.provider in TIME4BUS_PROVIDERS:
                from . import provider_time4bus
                data = await provider_time4bus.fetch(self)
            elif self.provider in KIEDYPRZYJEDZIE_PROVIDERS:
                from . import provider_kiedyprzyjedzie
                data = await provider_kiedyprzyjedzie.fetch(self)
            else:
                from . import provider_zkm
                data = await provider_zkm.fetch(self)
            data["departures"] = self._deduplicate_prefer_rt(data.get("departures", []))
            await self._async_save_offline_snapshot(data, now)

            # P2.5 — Enrich with stop coordinates and walking distance from HA home
            # Try to get stop coordinates from GTFS cache (GTFS-RT providers only)
            if self.stop_lat is None and self.provider in GTFSRT_PROVIDERS:
                try:
                    gtfs_cache = self.hass.data.get(DOMAIN, {}).get("_gtfsrt_cache", {})
                    from homeassistant.util import dt as dt_util
                    today = dt_util.now().strftime("%Y%m%d")
                    gtfs = gtfs_cache.get(f"{self.provider}_{today}")
                    if gtfs:
                        stop_info = gtfs.get("stops", {}).get(self.stop_id, {})
                        if "lat" in stop_info and "lon" in stop_info:
                            self.stop_lat = stop_info["lat"]
                            self.stop_lon = stop_info["lon"]
                except Exception:
                    pass

            if self.stop_lat is not None:
                from .walking import stop_walking_info
                home_lat = self.hass.config.latitude
                home_lon = self.hass.config.longitude
                walking = stop_walking_info(home_lat, home_lon, self.stop_lat, self.stop_lon)
                if walking:
                    data.update(walking)

            return data
        except Exception as err:
            offline = await self._async_offline_data(now, log_missing=False)
            if offline and offline.get("departures"):
                _LOGGER.warning(
                    "Fetch failed for %s (%s); serving the last offline schedule: %s",
                    self.stop_id,
                    self.provider,
                    err,
                )
                return offline
            _LOGGER.debug("Fetch error for %s (%s): %s", self.stop_id, self.provider, err, exc_info=True)
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def _async_save_offline_snapshot(self, data: dict, now) -> None:
        """Persist the last successful timetable for offline fallback."""
        if not data.get("departures"):
            return
        if self._last_offline_save and time.monotonic() - self._last_offline_save < 900:
            return
        try:
            saved = await async_save_snapshot(
                self.hass,
                self.provider,
                self.stop_id,
                data.get("stop_name") or self.stop_name,
                data["departures"],
                now=now,
            )
            if saved:
                self._last_offline_save = time.monotonic()
        except Exception as err:  # noqa: BLE001 - snapshots must not break updates
            _LOGGER.debug("Offline snapshot save failed for %s: %s", self.stop_id, err)

    async def _async_offline_data(self, now, log_missing: bool = True) -> dict:
        """Return the replay of the last saved schedule, if one exists."""
        try:
            snapshot = await async_load_snapshot(self.hass, self.provider, self.stop_id)
        except Exception as err:  # noqa: BLE001 - offline cache must not crash
            _LOGGER.debug("Offline snapshot read failed for %s: %s", self.stop_id, err)
            snapshot = None
        if snapshot:
            data = replay_snapshot(snapshot, now)
            data["stop_id"] = self.stop_id
            data["provider"] = self.provider
            if self.stop_name:
                data["stop_name"] = self.stop_name
            return data
        if log_missing:
            _LOGGER.warning(
                "Offline mode is enabled for %s (%s), but no saved schedule exists yet",
                self.stop_id,
                self.provider,
            )
        return {
            "stop_id": self.stop_id,
            "stop_name": self.stop_name or f"Przystanek {self.stop_id}",
            "provider": self.provider,
            "departures": [],
            "last_update": now.isoformat(),
            "offline": True,
            "offline_missing": True,
        }
