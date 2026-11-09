import logging
import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    PROVIDER_ZTM,
    PROVIDER_ZKM,
    PROVIDER_MZK,
    PROVIDER_PLK,
    PROVIDER_TCZEW,
    PROVIDER_LODZ,
    PROVIDER_KRAKOW,
    GTFSRT_PROVIDERS,
    KIEDYPRZYJEDZIE_PROVIDERS,
    KIEDYPRZYJEDZIE_BASE_URLS,
    TIME4BUS_PROVIDERS,
    TIME4BUS_API_BASE,
    TIME4BUS_OPERATORS,
    ZTM_GDANSK_STOPS_URL,
    ZKM_GDYNIA_STOPS_URL,
    PLK_API_BASE,
)

_LOGGER = logging.getLogger(__name__)

async def _load_stops(self, provider: str) -> list[dict]:


    """Load stop list for the selected provider."""


    try:


        if provider == PROVIDER_ZTM:


            return await _load_ztm_stops(self)


        if provider == PROVIDER_ZKM:


            return await _load_zkm_stops(self)


        if provider == PROVIDER_MZK:


            return await _load_mzk_stops(self)


        if provider == PROVIDER_PLK:


            return await _load_plk_stations(self)


        if provider in TIME4BUS_PROVIDERS:


            return await _load_time4bus_stops(self, provider)


        if provider in KIEDYPRZYJEDZIE_PROVIDERS:


            return await _load_kiedyprzyjedzie_stops(self, provider)

        if provider == PROVIDER_KRAKOW:
            return await _load_krakow_stops(self)

        if provider == PROVIDER_LODZ:
            return await _load_gtfs_stops(self, 
                "https://cdn.zbiorkom.live/gtfs/lodz.zip",
                id_column="stop_code",
            )

        if provider in GTFSRT_PROVIDERS:
            return await _load_gtfsrt_stops(self, provider)

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


async def _load_time4bus_stops(self, provider: str) -> list[dict]:


    """Load stops for a Time4BUS operator (Tczew, Bytów)."""


    session = async_get_clientsession(self.hass)
    operator = TIME4BUS_OPERATORS[provider]
    stops_url = f"{TIME4BUS_API_BASE}/operators/{operator}/stops"


    async with session.get(


        stops_url,


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


        ZKM_GDYNIA_STOPS_URL, timeout=aiohttp.ClientTimeout(total=20), ssl=False


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


    # Mark rail stations so a search for e.g. "Zabierzów PKP" picks the train
    # station instead of a nearby bus stop from another provider (issue #40).
    stops = [
        {
            "id": str(s["id"]),
            "name": s["name"] if "PKP" in s["name"].upper() else f"{s['name']} PKP",
        }
        for s in all_stations
        if s.get("id") and s.get("name")
    ]


    stops.sort(key=lambda x: x["name"])


    return stops


async def _load_gtfsrt_stops(self, provider: str) -> list[dict]:
    """Load stops from GTFS-RT provider's static GTFS zip."""
    from .provider_gtfsrt import GTFSRT_CITIES, _get_gzm_gtfs_url

    city_cfg = GTFSRT_CITIES.get(provider)
    if not city_cfg:
        return []

    if city_cfg.get("unavailable"):
        _LOGGER.warning(
            "GTFS-RT: %s has no public GTFS source anymore; skipping stop list",
            provider,
        )
        return []

    # Kraków: use lightweight ttss.pl API instead of 25MB GTFS download
    if provider == "zbiorkom_krakow":
        return await _load_krakow_stops(self)

    gtfs_url = city_cfg.get("gtfs_url")
    # GZM: dynamic URL from CKAN
    if not gtfs_url and city_cfg.get("gtfs_package_id"):
        session = async_get_clientsession(self.hass)
        gtfs_url = await _get_gzm_gtfs_url(session, city_cfg["gtfs_package_id"])
        if not gtfs_url:
            return []

    stops = await _load_gtfs_stops(self, gtfs_url)
    # Merge tram stops if separate zip exists
    if city_cfg.get("gtfs_url_tram"):
        tram_stops = await _load_gtfs_stops(self, city_cfg["gtfs_url_tram"])
        seen = {s["id"] for s in stops}
        for s in tram_stops:
            if s["id"] not in seen:
                stops.append(s)
        stops.sort(key=lambda x: x["name"])
    return stops

async def _load_krakow_stops(self) -> list[dict]:
    """Load Krak?w stops from the zbiorkom.live api6-open stop list."""
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
        _LOGGER.debug("Loaded %d Krak?w stops from zbiorkom.live", len(stops))
        return stops
    except Exception as e:
        _LOGGER.warning("Failed to load Krak?w stops: %s", e)
        return []


async def _load_gtfs_stops(self, gtfs_url: str, id_column: str = "stop_id") -> list[dict]:
    """Download a GTFS zip and parse stops.txt."""
    import csv
    import tempfile
    import zipfile
    from io import TextIOWrapper

    max_download_bytes = 256 * 1024 * 1024
    max_stops_bytes = 64 * 1024 * 1024

    try:
        _LOGGER.debug("GTFS stops: downloading %s", gtfs_url)
        session = async_get_clientsession(self.hass)
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as archive:
            downloaded = 0
            async with session.get(
                gtfs_url, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                resp.raise_for_status()
                if resp.content_length and resp.content_length > max_download_bytes:
                    raise ValueError("GTFS archive exceeds 256 MiB limit")
                async for chunk in resp.content.iter_chunked(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > max_download_bytes:
                        raise ValueError("GTFS archive exceeds 256 MiB limit")
                    archive.write(chunk)

            _LOGGER.debug("GTFS stops: downloaded %d bytes from %s", downloaded, gtfs_url)
            archive.seek(0)
            with zipfile.ZipFile(archive) as zf:
                if "stops.txt" not in zf.namelist():
                    return []
                if zf.getinfo("stops.txt").file_size > max_stops_bytes:
                    raise ValueError("GTFS stops.txt exceeds 64 MiB limit")
                with zf.open("stops.txt") as raw:
                    with TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
                        reader = csv.reader(text)
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
        _LOGGER.warning("Failed to load GTFS stops from %s: %s", gtfs_url, e)
        return []


