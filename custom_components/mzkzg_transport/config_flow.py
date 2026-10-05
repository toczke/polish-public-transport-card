"""Config flow for MZKZG Transport."""




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
    CONF_FALLBACK_MIN,


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


                    self._stops = await self._load_stops(self._provider)


                    return await self.async_step_stop()


                return await self.async_step_api_key()


            self._stops = await self._load_stops(self._provider)


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


    async def async_step_lodz_mode(self, user_input=None):
        """Łódź: choose single stop or bus stop group (węzeł przesiadkowy)."""
        if user_input is not None:
            if user_input.get("mode") == "group":
                self._lodz_stops = await self._load_lodz_groups()
                return await self.async_step_lodz_group()
            # Single stop
            self._stops = await self._load_stops(self._provider)
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


            if provider == PROVIDER_TCZEW:


                return await self._load_time4bus_tczew_stops()


            if provider in KIEDYPRZYJEDZIE_PROVIDERS:


                return await self._load_kiedyprzyjedzie_stops(provider)

            if provider in GTFSRT_PROVIDERS:
                return await self._load_gtfsrt_stops(provider)

            if provider == PROVIDER_KRAKOW:
                return await self._load_krakow_stops()

            if provider == PROVIDER_LODZ:
                return await self._load_gtfs_stops(
                    "https://cdn.zbiorkom.live/gtfs/lodz.zip",
                    id_column="stop_code",
                )

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


    async def _load_time4bus_tczew_stops(self) -> list[dict]:


        """Load Tczew stops from Time4BUS."""


        session = async_get_clientsession(self.hass)


        async with session.get(


            TIME4BUS_TCZEW_STOPS_URL,


            params={"limit": "1000", "offset": "0"},


            timeout=aiohttp.ClientTimeout(total=20),


        ) as resp:


            resp.raise_for_status()


            data = await resp.json()


        stops_raw = data.get("items", []) if isinstance(data, dict) else []


        stops = []


        for stop in stops_raw:


            if not isinstance(stop, dict):


                continue


            stop_id = stop.get("fullcode") or stop.get("id")


            stop_name = stop.get("name") or stop.get("groupName") or stop.get("fullcode")


            stop_code = stop.get("code")


            if stop_id is None or not stop_name:


                continue


            label = f"{stop_name} ({stop_code})" if stop_code else str(stop_name)


            stops.append({"id": str(stop_id), "name": label})


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


        return MzkzgTransportOptionsFlow()

    async def _load_gtfsrt_stops(self, provider: str) -> list[dict]:
        """Load stops from GTFS-RT provider's static GTFS zip."""
        from .provider_gtfsrt import GTFSRT_CITIES, _get_gzm_gtfs_url

        city_cfg = GTFSRT_CITIES.get(provider)
        if not city_cfg:
            return []

        # Kraków: use the zbiorkom.live stop list instead of the GTFS download
        if provider == "zbiorkom_krakow":
            return await self._load_krakow_stops()

        gtfs_url = city_cfg.get("gtfs_url")
        # GZM: dynamic URL from CKAN
        if not gtfs_url and city_cfg.get("gtfs_package_id"):
            session = async_get_clientsession(self.hass)
            gtfs_url = await _get_gzm_gtfs_url(session, city_cfg["gtfs_package_id"])
            if not gtfs_url:
                return []

        stops = await self._load_gtfs_stops(gtfs_url)
        # Merge tram stops if separate zip exists
        if city_cfg.get("gtfs_url_tram"):
            tram_stops = await self._load_gtfs_stops(city_cfg["gtfs_url_tram"])
            seen = {s["id"] for s in stops}
            for s in tram_stops:
                if s["id"] not in seen:
                    stops.append(s)
            stops.sort(key=lambda x: x["name"])
        return stops

    async def _load_krakow_stops(self) -> list[dict]:
        """Load Kraków stops from the zbiorkom.live open data API (ZTP, Mobilis and agglomeration lines)."""
        from .provider_krakow import ZBIORKOM_API

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{ZBIORKOM_API}/stops", timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
            stops = [
                {"id": row[0], "name": f"{row[2]} {row[3]}".strip()}
                for row in data.get("stops", [])
                if isinstance(row, list) and len(row) >= 4 and row[0] and row[2]
            ]
            stops.sort(key=lambda x: x["name"])
            _LOGGER.debug("Loaded %d Kraków stops from zbiorkom.live", len(stops))
            return stops
        except Exception as e:
            _LOGGER.warning("Failed to load Kraków stops: %s", e)
            return []

    async def _load_gtfs_stops(self, gtfs_url: str, id_column: str = "stop_id") -> list[dict]:
        """Download a GTFS zip and parse stops.txt."""
        import csv
        import zipfile
        from io import BytesIO, StringIO

        try:
            _LOGGER.debug("GTFS stops: downloading %s", gtfs_url)
            session = async_get_clientsession(self.hass)
            async with session.get(
                gtfs_url, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                resp.raise_for_status()
                data = await resp.read()
            _LOGGER.debug("GTFS stops: downloaded %d bytes from %s", len(data), gtfs_url)
        except Exception as e:
            _LOGGER.warning("Failed to download GTFS from %s: %s", gtfs_url, e)
            return []

        try:
            stops = []
            with zipfile.ZipFile(BytesIO(data)) as zf:
                if "stops.txt" not in zf.namelist():
                    return []
                text = zf.read("stops.txt").decode("utf-8-sig")
                reader = csv.reader(StringIO(text))
                header = next(reader)
                id_idx = header.index(id_column)
                name_idx = header.index("stop_name")
                stops_by_id = {}
                for parts in reader:
                    if len(parts) > max(id_idx, name_idx):
                        sid = parts[id_idx]
                        name = parts[name_idx]
                        if sid and name:
                            stops_by_id.setdefault(sid, {"id": sid, "name": name})

                stops = list(stops_by_id.values())

            stops.sort(key=lambda x: x["name"])
            _LOGGER.debug("GTFS stops: parsed %d stops from %s", len(stops), gtfs_url)
            return stops
        except Exception as e:
            _LOGGER.warning("Failed to parse GTFS zip from %s: %s", gtfs_url, e)
            return []


class MzkzgTransportOptionsFlow(config_entries.OptionsFlow):
    """Handle options for a stop entry."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_opts = self.config_entry.options
        provider = self.config_entry.data.get(CONF_PROVIDER, "")
        schema = {
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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )
