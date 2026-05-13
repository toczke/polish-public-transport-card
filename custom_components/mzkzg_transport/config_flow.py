"""Config flow for MZKZG Transport."""

from __future__ import annotations

import logging
import re

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_API_KEY,
    CONF_NAME,
    CONF_PLK_TIER,
    CONF_PROVIDER,
    CONF_STOP_ID,
    DOMAIN,
    KIEDYPRZYJEDZIE_BASE_URLS,
    KIEDYPRZYJEDZIE_PROVIDERS,
    PLK_API_BASE,
    PLK_TIER_LIMITS,
    PROVIDER_ALBATROS,
    PROVIDER_BYTOW,
    PROVIDER_CZLUCHOW,
    PROVIDER_GRYF,
    PROVIDER_MZK,
    PROVIDER_MZK_MALBORK,
    PROVIDER_MZK_STAROGARD,
    PROVIDER_NORD_EXPRESS,
    PROVIDER_PKS_GDANSK,
    PROVIDER_PKS_GDYNIA,
    PROVIDER_PKS_SLUPSK,
    PROVIDER_PKS_STAROGARD,
    PROVIDER_PLK,
    PROVIDER_ZKM,
    PROVIDER_ZTM,
    STOP_ID_PATTERN,
    ZKM_GDYNIA_STOPS_URL,
    ZTM_GDANSK_STOPS_URL,
)

_LOGGER = logging.getLogger(__name__)

PROVIDER_OPTIONS = {
    PROVIDER_ZTM: "ZTM Gdańsk",
    PROVIDER_ZKM: "ZKM Gdynia",
    PROVIDER_MZK: "MZK Wejherowo",
    PROVIDER_PLK: "PKP / SKM / PR (PLK API)",
    PROVIDER_PKS_GDANSK: "PKS GdaÅ„sk Sp. z o.o.",
    PROVIDER_ALBATROS: "Albatros",
    PROVIDER_GRYF: "Przewozy Autobusowe GRYF",
    PROVIDER_NORD_EXPRESS: "Nord Express",
    PROVIDER_PKS_GDYNIA: "PKS Gdynia S.A.",
    PROVIDER_MZK_MALBORK: "Miejski Zakład Komunikacji w Malborku",
    PROVIDER_PKS_SLUPSK: "PKS Słupsk S.A.",
    PROVIDER_MZK_STAROGARD: "MZK Starogard Gdański",
    PROVIDER_PKS_STAROGARD: "PKS Starogard Gdański S.A.",
    PROVIDER_BYTOW: "Bytów",
    PROVIDER_CZLUCHOW: "Powiat Człuchowski",
}


class MzkzgTransportConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MZKZG Transport."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._provider: str = ""
        self._stops: list[dict] = []
        self._api_key: str = ""
        self._plk_tier: str = "basic"

    async def async_step_user(self, user_input=None):
        """Step 1: Choose provider."""
        if user_input is not None:
            self._provider = user_input[CONF_PROVIDER]
            if self._provider == PROVIDER_PLK:
                # Reuse stored API key if available (memory or existing entries)
                stored_key = self.hass.data.get(DOMAIN, {}).get("_global", {}).get(CONF_API_KEY, "")
                if not stored_key:
                    for entry in self.hass.config_entries.async_entries(DOMAIN):
                        if entry.data.get("provider") == PROVIDER_PLK and entry.data.get("api_key"):
                            stored_key = entry.data["api_key"]
                            break
                if stored_key:
                    self._api_key = stored_key
                    self._stops = await self._load_stops(self._provider)
                    return await self.async_step_stop()
                return await self.async_step_api_key()
            self._stops = await self._load_stops(self._provider)
            return await self.async_step_stop()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_PROVIDER, default=PROVIDER_ZTM): vol.In(PROVIDER_OPTIONS)}
            ),
        )

    async def async_step_api_key(self, user_input=None):
        """Step for PLK: enter API key and select usage tier."""
        errors = {}
        if user_input is not None:
            self._api_key = user_input.get(CONF_API_KEY, "").strip()
            self._plk_tier = user_input.get(CONF_PLK_TIER, "basic")
            if not self._api_key:
                errors[CONF_API_KEY] = "api_key_required"
            else:
                self.hass.data.setdefault(DOMAIN, {"_entries": {}, "_global": {}})
                self.hass.data[DOMAIN]["_global"][CONF_API_KEY] = self._api_key
                self.hass.data[DOMAIN]["_global"][CONF_PLK_TIER] = self._plk_tier
                self._stops = await self._load_stops(self._provider)
                return await self.async_step_stop()

        tier_options = {
            "basic": "Basic (100/godz., 1 000/dzień)",
            "standard": "Standard (500/godz., 5 000/dzień)",
            "premium": "Premium (2 000/godz., 20 000/dzień)",
        }
        return self.async_show_form(
            step_id="api_key",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
                vol.Required(CONF_PLK_TIER, default="basic"): vol.In(tier_options),
            }),
            errors=errors,
        )

    async def async_step_stop(self, user_input=None):
        """Step 2: Select stop from list."""
        errors = {}

        if user_input is not None:
            stop_id = str(user_input[CONF_STOP_ID]).strip()
            name = user_input.get(CONF_NAME, "").strip()

            if not stop_id or not re.match(STOP_ID_PATTERN, stop_id):
                errors[CONF_STOP_ID] = "invalid_stop_id"
            else:
                await self.async_set_unique_id(f"{self._provider}_{stop_id}")
                self._abort_if_unique_id_configured()

                # Resolve name from stops list if not provided
                if not name:
                    for s in self._stops:
                        if str(s["id"]) == stop_id:
                            name = s["name"]
                            break

                title = name or f"{PROVIDER_OPTIONS.get(self._provider, '')} {stop_id}"
                data = {
                    CONF_STOP_ID: stop_id,
                    CONF_PROVIDER: self._provider,
                    CONF_NAME: name,
                }
                if self._api_key:
                    data[CONF_API_KEY] = self._api_key
                    data[CONF_PLK_TIER] = self._plk_tier
                return self.async_create_entry(title=title, data=data)

        # Build stop options as dict for selector
        if self._stops:
            from homeassistant.helpers.selector import (
                SelectOptionDict,
                SelectSelector,
                SelectSelectorConfig,
                SelectSelectorMode,
            )
            options = [
                SelectOptionDict(value=str(s["id"]), label=f"{s['name']} ({s['id']})")
                for s in self._stops
            ]
            schema = vol.Schema(
                {
                    vol.Required(CONF_STOP_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                            custom_value=True,
                            sort=False,
                        )
                    ),
                    vol.Optional(CONF_NAME, default=""): str,
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Required(CONF_STOP_ID): str,
                    vol.Optional(CONF_NAME, default=""): str,
                }
            )

        return self.async_show_form(
            step_id="stop",
            data_schema=schema,
            errors=errors,
            description_placeholders={"provider": PROVIDER_OPTIONS.get(self._provider, "")},
        )

    async def _load_stops(self, provider: str) -> list[dict]:
        """Load stop list for the selected provider."""
        try:
            if provider == PROVIDER_ZTM:
                return await self._load_ztm_stops()
            if provider == PROVIDER_ZKM:
                return await self._load_zkm_stops()
            if provider == PROVIDER_MZK:
                return await self._load_mzk_stops()
            if provider == PROVIDER_PLK:
                return await self._load_plk_stations()
            if provider in KIEDYPRZYJEDZIE_PROVIDERS:
                return await self._load_kiedyprzyjedzie_stops(provider)
        except Exception as err:
            _LOGGER.warning("Could not load stops for %s: %s", provider, err)
        return []

    async def _load_kiedyprzyjedzie_stops(self, provider: str) -> list[dict]:
        """Load stops from kiedyPrzyjedzie for bus carriers."""
        session = async_get_clientsession(self.hass)
        base_url = KIEDYPRZYJEDZIE_BASE_URLS[provider]

        async with session.get(
            f"{base_url}/stops", timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        stops_raw = data.get("stops", []) if isinstance(data, dict) else []
        stops = []
        for stop in stops_raw:
            if not isinstance(stop, (list, tuple)) or len(stop) < 3:
                continue
            stop_id = stop[0]
            stop_name = stop[2]
            stops.append({"id": stop_id, "name": stop_name})

        stops.sort(key=lambda x: x["name"])
        return stops

    async def _load_ztm_stops(self) -> list[dict]:
        """Load ZTM Gdańsk stops."""
        from datetime import date as dt_date

        session = async_get_clientsession(self.hass)
        async with session.get(
            ZTM_GDANSK_STOPS_URL, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        # Use today's key, fallback to first available
        today_str = dt_date.today().strftime("%Y-%m-%d")
        stops_data = data.get(today_str) or data.get(sorted(data.keys())[0], {})
        stops_raw = stops_data.get("stops", [])
        stops = []
        for s in stops_raw:
            if s.get("nonpassenger"):
                continue
            name = str(s.get("stopDesc") or s.get("stopName") or "")
            sub = str(s.get("subName") or s.get("stopCode") or "")
            label = f"{name} {sub}".strip() if sub else name
            stops.append({"id": s["stopId"], "name": label})

        stops.sort(key=lambda x: x["name"])
        return stops

    async def _load_zkm_stops(self) -> list[dict]:
        """Load ZKM Gdynia stops."""
        session = async_get_clientsession(self.hass)
        async with session.get(
            ZKM_GDYNIA_STOPS_URL, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        stops_raw = data if isinstance(data, list) else data.get("stops", [])
        stops = []
        for s in stops_raw:
            name = s.get("stopName", s.get("stopDesc", ""))
            stops.append({"id": s["stopId"], "name": name})

        stops.sort(key=lambda x: x["name"])
        return stops

    async def _load_mzk_stops(self) -> list[dict]:
        """Load MZK Wejherowo stops from GTFS."""
        from .gtfs_provider import get_gtfs_data

        gtfs = await get_gtfs_data()
        stops = [
            {"id": sid, "name": info["name"]}
            for sid, info in gtfs.stops.items()
        ]
        stops.sort(key=lambda x: x["name"])
        return stops

    async def _load_plk_stations(self) -> list[dict]:
        """Load PLK stations from API (paginated, requires key)."""
        all_stations = []
        page = 1
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        session = async_get_clientsession(self.hass)
        while True:
            async with session.get(
                f"{PLK_API_BASE}/dictionaries/stations",
                params={"page": str(page), "pageSize": "1000"},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            stations_list = data.get("stations", [])
            all_stations.extend(stations_list)
            if page >= data.get("totalPages", 1) or page >= 20:
                break
            page += 1

        stops = [{"id": str(s["id"]), "name": s["name"]} for s in all_stations if s.get("id") and s.get("name")]
        stops.sort(key=lambda x: x["name"])
        return stops

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return MzkzgTransportOptionsFlow(config_entry)


class MzkzgTransportOptionsFlow(config_entries.OptionsFlow):
    """Handle options for a stop entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME,
                        default=self.config_entry.data.get(CONF_NAME, ""),
                    ): str,
                }
            ),
        )
