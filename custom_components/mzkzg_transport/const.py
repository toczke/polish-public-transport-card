"""Constants for MZKZG Transport integration."""

DOMAIN = "mzkzg_transport"

# API endpoints
ZTM_GDANSK_DEPARTURES_URL = "https://ckan2.multimediagdansk.pl/departures"
ZTM_GDANSK_STOPS_URL = (
    "https://mapa.ztm.gda.pl/dataset/"
    "c24aa637-3619-4dc2-a171-a23eec8f2172/resource/"
    "4c4025f0-01bf-41f7-a39f-d156d201b82b/download/stops.json"
)

ZKM_GDYNIA_DELAYS_URL = "https://api.zdiz.gdynia.pl/pt/delays"
ZKM_GDYNIA_STOPS_URL = "https://api.zdiz.gdynia.pl/pt/stops"
ZKM_GDYNIA_ROUTES_URL = "https://api.zdiz.gdynia.pl/pt/routes"
KIEDYPRZYJEDZIE_PKS_GDANSK_URL = "https://pksgdansk.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_ALBATROS_URL = "https://albatros.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_GRYF_URL = "https://gryf.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_NORD_EXPRESS_URL = "https://nordexpress.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_PKS_GDYNIA_URL = "https://pksgdynia.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_ZKM_GDYNIA_URL = "https://gdynia.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_MZK_MALBORK_URL = "https://malbork.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_PKS_SLUPSK_URL = "https://pksslupsk.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_MZK_STAROGARD_URL = "https://starogard.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_PKS_STAROGARD_URL = "https://pksstarogard.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_BYTOW_URL = "https://bytow.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_CZLUCHOW_URL = "https://czluchow.kiedyprzyjedzie.pl"

# Providers
PROVIDER_ZTM = "ztm_gdansk"
PROVIDER_ZKM = "zkm_gdynia"
PROVIDER_MZK = "mzk_wejherowo"
PROVIDER_PLK = "plk_rail"
PROVIDER_PKS_GDANSK = "kiedyprzyjedzie_pks_gdansk"
PROVIDER_ALBATROS = "kiedyprzyjedzie_albatros"
PROVIDER_GRYF = "kiedyprzyjedzie_gryf"
PROVIDER_NORD_EXPRESS = "kiedyprzyjedzie_nord_express"
PROVIDER_PKS_GDYNIA = "kiedyprzyjedzie_pks_gdynia"
PROVIDER_KIEDYPRZYJEDZIE_ZKM_GDYNIA = "kiedyprzyjedzie_zkm_gdynia"
PROVIDER_MZK_MALBORK = "kiedyprzyjedzie_mzk_malbork"
PROVIDER_PKS_SLUPSK = "kiedyprzyjedzie_pks_slupsk"
PROVIDER_MZK_STAROGARD = "kiedyprzyjedzie_mzk_starogard"
PROVIDER_PKS_STAROGARD = "kiedyprzyjedzie_pks_starogard"
PROVIDER_BYTOW = "kiedyprzyjedzie_bytow"
PROVIDER_CZLUCHOW = "kiedyprzyjedzie_czluchow"

KIEDYPRZYJEDZIE_BASE_URLS = {
    PROVIDER_PKS_GDANSK: KIEDYPRZYJEDZIE_PKS_GDANSK_URL,
    PROVIDER_ALBATROS: KIEDYPRZYJEDZIE_ALBATROS_URL,
    PROVIDER_GRYF: KIEDYPRZYJEDZIE_GRYF_URL,
    PROVIDER_NORD_EXPRESS: KIEDYPRZYJEDZIE_NORD_EXPRESS_URL,
    PROVIDER_PKS_GDYNIA: KIEDYPRZYJEDZIE_PKS_GDYNIA_URL,
    PROVIDER_KIEDYPRZYJEDZIE_ZKM_GDYNIA: KIEDYPRZYJEDZIE_ZKM_GDYNIA_URL,
    PROVIDER_MZK_MALBORK: KIEDYPRZYJEDZIE_MZK_MALBORK_URL,
    PROVIDER_PKS_SLUPSK: KIEDYPRZYJEDZIE_PKS_SLUPSK_URL,
    PROVIDER_MZK_STAROGARD: KIEDYPRZYJEDZIE_MZK_STAROGARD_URL,
    PROVIDER_PKS_STAROGARD: KIEDYPRZYJEDZIE_PKS_STAROGARD_URL,
    PROVIDER_BYTOW: KIEDYPRZYJEDZIE_BYTOW_URL,
    PROVIDER_CZLUCHOW: KIEDYPRZYJEDZIE_CZLUCHOW_URL,
}

KIEDYPRZYJEDZIE_PROVIDERS = set(KIEDYPRZYJEDZIE_BASE_URLS)

PROVIDER_LABELS = {
    PROVIDER_ZTM: "ZTM Gdańsk",
    PROVIDER_ZKM: "ZKM Gdynia",
    PROVIDER_MZK: "MZK Wejherowo",
    PROVIDER_PLK: "PKP / SKM / PR (PLK API)",
    PROVIDER_PKS_GDANSK: "PKS Gdańsk Sp. z o.o.",
    PROVIDER_ALBATROS: "Albatros",
    PROVIDER_GRYF: "Przewozy Autobusowe GRYF",
    PROVIDER_NORD_EXPRESS: "Nord Express",
    PROVIDER_PKS_GDYNIA: "PKS Gdynia S.A.",
    PROVIDER_KIEDYPRZYJEDZIE_ZKM_GDYNIA: "ZKM Gdynia (kiedyPrzyjedzie)",
    PROVIDER_MZK_MALBORK: "Miejski Zakład Komunikacji w Malborku",
    PROVIDER_PKS_SLUPSK: "PKS Słupsk S.A.",
    PROVIDER_MZK_STAROGARD: "MZK Starogard Gdański",
    PROVIDER_PKS_STAROGARD: "PKS Starogard Gdański S.A.",
    PROVIDER_BYTOW: "Bytów",
    PROVIDER_CZLUCHOW: "Powiat Człuchowski",
}

PROVIDER_SHORT_NAMES = {
    PROVIDER_ZTM: "ztm",
    PROVIDER_ZKM: "zkm",
    PROVIDER_MZK: "mzk",
    PROVIDER_PLK: "plk",
    PROVIDER_PKS_GDANSK: "pks",
    PROVIDER_ALBATROS: "alb",
    PROVIDER_GRYF: "gryf",
    PROVIDER_NORD_EXPRESS: "nord",
    PROVIDER_PKS_GDYNIA: "pksgd",
    PROVIDER_KIEDYPRZYJEDZIE_ZKM_GDYNIA: "kpgd",
    PROVIDER_MZK_MALBORK: "malb",
    PROVIDER_PKS_SLUPSK: "slupsk",
    PROVIDER_MZK_STAROGARD: "starog",
    PROVIDER_PKS_STAROGARD: "pksst",
    PROVIDER_BYTOW: "bytow",
    PROVIDER_CZLUCHOW: "czl",
}

PROVIDER_COLORS = {
    PROVIDER_ZTM: "#DA2128",
    PROVIDER_ZKM: "#005eb8",
    PROVIDER_MZK: "#478AC9",
    PROVIDER_PLK: "#1a1a2e",
    PROVIDER_PKS_GDANSK: "#0f766e",
    PROVIDER_ALBATROS: "#1d4ed8",
    PROVIDER_GRYF: "#f59e0b",
    PROVIDER_NORD_EXPRESS: "#0f172a",
    PROVIDER_PKS_GDYNIA: "#0e7490",
    PROVIDER_KIEDYPRZYJEDZIE_ZKM_GDYNIA: "#2563eb",
    PROVIDER_MZK_MALBORK: "#ea580c",
    PROVIDER_PKS_SLUPSK: "#4f46e5",
    PROVIDER_MZK_STAROGARD: "#be123c",
    PROVIDER_PKS_STAROGARD: "#7c3aed",
    PROVIDER_BYTOW: "#16a34a",
    PROVIDER_CZLUCHOW: "#64748b",
}

CONF_STOPS = "stops"
CONF_STOP_ID = "stop_id"
CONF_PROVIDER = "provider"
CONF_NAME = "name"
CONF_API_KEY = "api_key"
CONF_PLK_TIER = "plk_tier"

DEFAULT_SCAN_INTERVAL = 30
STOP_ID_PATTERN = r"^[a-zA-Z0-9_:-]+$"

# PLK tier → max requests per hour
PLK_TIER_LIMITS = {
    "basic": 100,
    "standard": 500,
    "premium": 2000,
}

# PLK tier → max requests per day
PLK_DAILY_LIMITS = {
    "basic": 1000,
    "standard": 5000,
    "premium": 20000,
}

MZK_GTFS_URL = "https://mkuran.pl/gtfs/wejherowo.zip"
PLK_API_BASE = "https://pdp-api.plk-sa.pl/api/v1"
