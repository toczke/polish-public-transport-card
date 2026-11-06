"""Config flow for MZKZG Transport."""




import logging


import re


import aiohttp


from homeassistant.helpers.aiohttp_client import async_get_clientsession


import voluptuous as vol


from homeassistant import config_entries


from homeassistant.core import callback


from .config_flow_stops import _load_stops
from .const import (


    CONF_API_KEY,


    CONF_NAME,
    CONF_FALLBACK_MIN,
    CONF_TIMETABLE_LINES,


    CONF_PLK_TIER,


    CONF_PROVIDER,


    CONF_SLEEP_ENABLED,
    CONF_SLEEP_END,
    CONF_SLEEP_START,
    CONF_STOP_ID,
    CONF_STOPS,
    DEFAULT_FALLBACK_MIN,
    DEFAULT_SLEEP_END,
    DEFAULT_SLEEP_START,


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


    PROVIDER_BIELSKO,


    PROVIDER_PLK,


    PROVIDER_TCZEW,


    PROVIDER_LODZ,

    PROVIDER_POZNAN,
    PROVIDER_LUBLIN,
    PROVIDER_KIELCE,
    PROVIDER_RADOM,
    PROVIDER_CZESTOCHOWA,
    PROVIDER_ELBLAG,
    PROVIDER_GORZOW,
    PROVIDER_SUWALKI,
    PROVIDER_PRZEMYSL,
    PROVIDER_RYBNIK,
    PROVIDER_KUTNO,
    PROVIDER_LEGNICA,
    PROVIDER_GZM,
    PROVIDER_KRAKOW,
    PROVIDER_SZCZECIN,
    PROVIDER_WARSZAWA,
    PROVIDER_ELK,
    PROVIDER_WKD,
    PROVIDER_BIALYSTOK,
    PROVIDER_OLSZTYN,
    PROVIDER_OPOLE,
    PROVIDER_RZESZOW,
    PROVIDER_BYDGOSZCZ,
    PROVIDER_MIELEC,
    PROVIDER_OSWIECIM,
    PROVIDER_RADOMSKO,
    PROVIDER_DEBICA,
    PROVIDER_KOLOBRZEG,
    PROVIDER_SANOK,
    PROVIDER_OSTROLEKA,
    PROVIDER_LESZNO,
    PROVIDER_TORUN,
    PROVIDER_WROCLAW,
    PROVIDER_SWINOUJSCIE,
    PROVIDER_WALBRZYCH,
    PROVIDER_TARNOW,
    PROVIDER_STARACHOWICE,
    PROVIDER_SIEDLCE,
    PROVIDER_PLOCK,
    PROVIDER_PILA,
    PROVIDER_KROSNO,
    PROVIDER_KOSZALIN,
    PROVIDER_KONIN,
    PROVIDER_KALISZ,

    GTFSRT_PROVIDERS,

    PROVIDER_ZKM,


    PROVIDER_ZTM,


    TIME4BUS_TCZEW_STOPS_URL,


    STOP_ID_PATTERN,


    ZKM_GDYNIA_STOPS_URL,


    ZTM_GDANSK_STOPS_URL,


)


_LOGGER = logging.getLogger(__name__)


PROVIDER_OPTIONS = {
    PROVIDER_ZTM: "ZTM Gda\u0144sk",
    PROVIDER_ZKM: "ZKM Gdynia",
    PROVIDER_MZK: "MZK Wejherowo",
    PROVIDER_PLK: "Polskie Linie Kolejowe (PKP, SKM, PR, IC)",
    PROVIDER_PKS_GDANSK: "PKS Gda\u0144sk Sp. z o.o.",
    PROVIDER_ALBATROS: "Albatros",
    PROVIDER_GRYF: "Przewozy Autobusowe GRYF",
    PROVIDER_NORD_EXPRESS: "Nord Express",
    PROVIDER_PKS_GDYNIA: "PKS Gdynia S.A.",
    PROVIDER_MZK_MALBORK: "Miejski Zak\u0142ad Komunikacji w Malborku",
    PROVIDER_PKS_SLUPSK: "PKS S\u0142upsk S.A.",
    PROVIDER_MZK_STAROGARD: "MZK Starogard Gda\u0144ski",
    PROVIDER_PKS_STAROGARD: "PKS Starogard Gda\u0144ski S.A.",
    PROVIDER_BIELSKO: "MZK Bielsko-Bia\u0142a",
    PROVIDER_BYTOW: "Byt\u00f3w",
    PROVIDER_CZLUCHOW: "Powiat Cz\u0142uchowski",
    PROVIDER_TCZEW: "Tczew (Time4BUS)",
    PROVIDER_LODZ: "MPK \u0141\u00f3d\u017a",
    PROVIDER_POZNAN: "ZTM Pozna\u0144",
    PROVIDER_LUBLIN: "ZTM Lublin",
    PROVIDER_KIELCE: "MPK Kielce",
    PROVIDER_RADOM: "MZDiK Radom",
    PROVIDER_CZESTOCHOWA: "MPK Cz\u0119stochowa",
    PROVIDER_ELBLAG: "ZKM Elbl\u0105g",
    PROVIDER_GORZOW: "MZK Gorz\u00f3w Wlkp.",
    PROVIDER_SUWALKI: "PGK Suwa\u0142ki",
    PROVIDER_PRZEMYSL: "MZK Przemy\u015bl",
    PROVIDER_RYBNIK: "ZTZ Rybnik",
    PROVIDER_KUTNO: "MZK Kutno",
    PROVIDER_LEGNICA: "MPK Legnica",
    PROVIDER_GZM: "ZTM GZM (Katowice)",
    PROVIDER_KRAKOW: "ZTP Krak\u00f3w",
    PROVIDER_SZCZECIN: "ZDiTM Szczecin",
    PROVIDER_WARSZAWA: "ZTM Warszawa",
    PROVIDER_ELK: "MZK Ełk",
    PROVIDER_WKD: "WKD",
    PROVIDER_BIALYSTOK: "BKM Białystok",
    PROVIDER_OLSZTYN: "ZDZiT Olsztyn",
    PROVIDER_OPOLE: "MZK Opole",
    PROVIDER_RZESZOW: "ZTM Rzeszów",
    PROVIDER_TORUN: "MZK Toruń",
    PROVIDER_WROCLAW: "MPK Wrocław",
    PROVIDER_BYDGOSZCZ: "ZDMiKP Bydgoszcz",
    PROVIDER_MIELEC: "MKS Mielec",
    PROVIDER_OSWIECIM: "MZK Oświęcim",
    PROVIDER_RADOMSKO: "MPK Radomsko",
    PROVIDER_DEBICA: "MKS Dębica",
    PROVIDER_KOLOBRZEG: "KM Kołobrzeg",
    PROVIDER_SANOK: "SPGK Sanok",
    PROVIDER_OSTROLEKA: "MZK Ostrołęka",
    PROVIDER_LESZNO: "MZK Leszno",
    PROVIDER_SWINOUJSCIE: "KA Świnoujście",
    PROVIDER_WALBRZYCH: "ZKM Wałbrzych",
    PROVIDER_TARNOW: "MPK Tarnów",
    PROVIDER_STARACHOWICE: "MZK Starachowice",
    PROVIDER_SIEDLCE: "MPK Siedlce",
    PROVIDER_PLOCK: "KM Płock",
    PROVIDER_PILA: "MZK Piła",
    PROVIDER_KROSNO: "MKS Krosno",
    PROVIDER_KOSZALIN: "MZK Koszalin",
    PROVIDER_KONIN: "MZK Konin",
    PROVIDER_KALISZ: "MZK Kalisz",
}

PROVIDER_OPTIONS_SORTED = dict(
    sorted(PROVIDER_OPTIONS.items(), key=lambda item: item[1].casefold())
)


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


            if self._provider == PROVIDER_LODZ:
                return await self.async_step_lodz_mode()


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


                    self._stops = await _load_stops(self, self._provider)


                    return await self.async_step_stop()


                return await self.async_step_api_key()


            self._stops = await _load_stops(self, self._provider)


            return await self.async_step_stop()


        return self.async_show_form(


            step_id="user",


            data_schema=vol.Schema(


                {vol.Required(CONF_PROVIDER, default=PROVIDER_ZTM): vol.In(PROVIDER_OPTIONS_SORTED)}


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


                self._stops = await _load_stops(self, self._provider)


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


    async def async_step_lodz_mode(self, user_input=None):
        """Łódź: choose single stop or bus stop group (węzeł przesiadkowy)."""
        if user_input is not None:
            if user_input.get("mode") == "group":
                self._lodz_stops = await self._load_lodz_groups()
                return await self.async_step_lodz_group()
            # Single stop
            self._stops = await _load_stops(self, self._provider)
            return await self.async_step_stop()

        return self.async_show_form(
            step_id="lodz_mode",
            data_schema=vol.Schema({
                vol.Required("mode", default="single"): vol.In({
                    "single": "Pojedynczy przystanek",
                    "group": "Węzeł przesiadkowy (grupa przystanków)",
                })
            }),
        )

    async def _load_lodz_groups(self) -> list:
        """Fetch bus stop groups from rozklady.lodz.pl API."""
        import aiohttp
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://rozklady.lodz.pl/Home/GetMapBusStopGroupList",
                    timeout=timeout,
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.warning("Łódź groups API HTTP %s", resp.status)
                        return []
                    text = await resp.text()
                    import json
                    data = json.loads(text)
        except Exception as exc:
            _LOGGER.warning("Failed to load Łódź bus stop groups: %s", exc)
            return []

        groups = []
        for item in data:
            if not isinstance(item, list) or len(item) < 5:
                continue
            gid = item[0]
            gname = item[1]
            stops = item[4]  # list of [stop_id, stop_name]
            expanded = [
                {"id": str(s[0]), "name": s[1]}
                for s in stops if isinstance(s, list) and len(s) >= 2
            ]
            if expanded:
                groups.append({
                    "id": str(gid),
                    "name": gname,
                    "stops": expanded,
                })
        groups.sort(key=lambda g: g["name"].casefold())
        return groups

    async def async_step_lodz_group(self, user_input=None):
        """Łódź: select a bus stop group."""
        errors = {}
        if user_input is not None:
            group_id = str(user_input["group_id"])
            selected = None
            for g in self._lodz_stops:
                if g["id"] == group_id:
                    selected = g
                    break
            if not selected:
                errors["group_id"] = "invalid_group"
            else:
                stops_data = [{"stop_id": s["id"], "name": s["name"]} for s in selected["stops"]]
                await self.async_set_unique_id(f"mpk_lodz_group_{group_id}")
                self._abort_if_unique_id_configured()
                data = {
                    CONF_STOPS: stops_data,
                    CONF_PROVIDER: self._provider,
                    CONF_NAME: selected["name"],
                }
                return self.async_create_entry(
                    title=f"Łódź: {selected['name']} ({len(stops_data)} przyst.)",
                    data=data,
                )

        if not self._lodz_stops:
            _LOGGER.warning("No Łódź bus stop groups loaded")
            return self.async_abort(reason="lodz_groups_failed")

        options = [
            {"value": g["id"], "label": f"{g['name']} ({len(g['stops'])} przyst.)"}
            for g in self._lodz_stops
        ]
        from homeassistant.helpers.selector import (
            SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode,
        )
        select_options = [SelectOptionDict(**o) for o in options]

        return self.async_show_form(
            step_id="lodz_group",
            data_schema=vol.Schema({
                vol.Required("group_id"): SelectSelector(
                    SelectSelectorConfig(
                        options=select_options,
                        mode=SelectSelectorMode.DROPDOWN,
                        sort=False,
                    )
                ),
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


                title = PROVIDER_OPTIONS.get(self._provider, self._provider)


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
        if self._stops and len(self._stops) <= 3000:
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


    @staticmethod


    @callback


    def async_get_options_flow(config_entry):


        """Get options flow."""


        return MzkzgTransportOptionsFlow()

class MzkzgTransportOptionsFlow(config_entries.OptionsFlow):
    """Handle options for a stop entry."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            current_opts = self.config_entry.options
            merged = {**current_opts, **user_input}
            return self.async_create_entry(title="", data=merged)

        current_opts = self.config_entry.options
        current_data = self.config_entry.data
        provider = current_data.get(CONF_PROVIDER, "")
        stop_id = current_data.get(CONF_STOP_ID, "")

        def _opt(key, default=""):
            return current_opts.get(key, current_data.get(key, default))

        schema = {
            vol.Optional(
                CONF_NAME,
                default=_opt(CONF_NAME, ""),
            ): str,
            vol.Optional(
                "destination_filter",
                default=_opt("destination_filter", ""),
            ): str,
            vol.Optional(
                "filter_routes",
                default=_opt("filter_routes", ""),
            ): str,
            vol.Optional(
                "highlight_mode",
                default=bool(_opt("highlight_mode", False)),
            ): bool,
            vol.Optional(
                "hide_terminus",
                default=bool(_opt("hide_terminus", False)),
            ): bool,
            vol.Optional(
                "realtime_only",
                default=bool(_opt("realtime_only", False)),
            ): bool,
            vol.Optional(
                CONF_SLEEP_ENABLED,
                default=current_opts.get(CONF_SLEEP_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_SLEEP_START,
                default=current_opts.get(CONF_SLEEP_START, DEFAULT_SLEEP_START),
            ): str,
            vol.Optional(
                CONF_SLEEP_END,
                default=current_opts.get(CONF_SLEEP_END, DEFAULT_SLEEP_END),
            ): str,
        }
        if provider == PROVIDER_LODZ:
            schema[vol.Optional(
                CONF_FALLBACK_MIN,
                default=current_opts.get(CONF_FALLBACK_MIN, DEFAULT_FALLBACK_MIN),
            )] = vol.All(vol.Coerce(int), vol.Range(min=1, max=30))
        if provider in KIEDYPRZYJEDZIE_PROVIDERS:
            schema[vol.Optional(
                CONF_TIMETABLE_LINES,
                default=_opt(CONF_TIMETABLE_LINES, ""),
            )] = str

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
            description_placeholders={
                "stop_id": stop_id,
                "provider": provider,
            },
        )
