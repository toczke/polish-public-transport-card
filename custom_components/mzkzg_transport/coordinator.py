"""Data coordinator for MZKZG Transport."""

from datetime import timedelta
import logging
import re

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    KIEDYPRZYJEDZIE_PROVIDERS,
    PROVIDER_LODZ,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_ZTM,
    STOP_ID_PATTERN,
    TIME4BUS_PROVIDERS,
)

_LOGGER = logging.getLogger(__name__)
_STOP_ID_RE = re.compile(STOP_ID_PATTERN)


class MzkzgTransportCoordinator(DataUpdateCoordinator):
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

        plk_stations = sum(1 for e in hass.data.get(DOMAIN, {}).get("_coordinators", {}).values()
                          if getattr(e, "provider", None) == PROVIDER_PLK) + (1 if provider == PROVIDER_PLK else 0)
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
        self._routes_map: dict[str, str] = {}
        self._routes_load_failed_at: float = 0

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

    async def _async_update_data(self) -> dict:
        """Fetch departures from the appropriate provider module."""
        try:
            if self.provider == PROVIDER_ZTM:
                from . import provider_ztm
                return await provider_ztm.fetch(self)
            if self.provider == PROVIDER_MZK:
                from . import provider_mzk
                return await provider_mzk.fetch(self)
            if self.provider == PROVIDER_LODZ:
                from . import provider_lodz
                return await provider_lodz.fetch(self)
            if self.provider == PROVIDER_PLK:
                from . import provider_plk
                return await provider_plk.fetch(self)
            if self.provider in TIME4BUS_PROVIDERS:
                from . import provider_time4bus
                return await provider_time4bus.fetch(self)
            if self.provider in KIEDYPRZYJEDZIE_PROVIDERS:
                from . import provider_kiedyprzyjedzie
                return await provider_kiedyprzyjedzie.fetch(self)
            from . import provider_zkm
            return await provider_zkm.fetch(self)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
