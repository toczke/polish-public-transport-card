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
KIEDYPRZYJEDZIE_MZK_MALBORK_URL = "https://malbork.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_PKS_SLUPSK_URL = "https://pksslupsk.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_MZK_STAROGARD_URL = "https://starogard.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_PKS_STAROGARD_URL = "https://pksstarogard.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_BYTOW_URL = "https://bytow.kiedyprzyjedzie.pl"
KIEDYPRZYJEDZIE_CZLUCHOW_URL = "https://czluchow.kiedyprzyjedzie.pl"
TIME4BUS_API_BASE = "https://time4bus.com/t4b"
TIME4BUS_TCZEW_OPERATOR = "tczew"
TIME4BUS_TCZEW_STOPS_URL = f"{TIME4BUS_API_BASE}/operators/{TIME4BUS_TCZEW_OPERATOR}/stops"
TIME4BUS_TCZEW_LIVE_DEPARTURES_URL = f"{TIME4BUS_API_BASE}/live/schedules/{TIME4BUS_TCZEW_OPERATOR}/stops"
TIME4BUS_TCZEW_SCHEDULE_DEPARTURES_URL = f"{TIME4BUS_API_BASE}/operators/{TIME4BUS_TCZEW_OPERATOR}/stops"

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
PROVIDER_MZK_MALBORK = "kiedyprzyjedzie_mzk_malbork"
PROVIDER_PKS_SLUPSK = "kiedyprzyjedzie_pks_slupsk"
PROVIDER_MZK_STAROGARD = "kiedyprzyjedzie_mzk_starogard"
PROVIDER_PKS_STAROGARD = "kiedyprzyjedzie_pks_starogard"
PROVIDER_BYTOW = "kiedyprzyjedzie_bytow"
PROVIDER_CZLUCHOW = "kiedyprzyjedzie_czluchow"
PROVIDER_TCZEW = "time4bus_tczew"
PROVIDER_LODZ = "mpk_lodz"
PROVIDER_POZNAN = "gtfsrt_poznan"
PROVIDER_LUBLIN = "gtfsrt_lublin"
PROVIDER_KIELCE = "gtfsrt_kielce"
PROVIDER_RADOM = "gtfsrt_radom"
PROVIDER_CZESTOCHOWA = "gtfsrt_czestochowa"
PROVIDER_ELBLAG = "gtfsrt_elblag"
PROVIDER_GORZOW = "gtfsrt_gorzow"
PROVIDER_SUWALKI = "gtfsrt_suwalki"
PROVIDER_PRZEMYSL = "gtfsrt_przemysl"
PROVIDER_RYBNIK = "gtfsrt_rybnik"
PROVIDER_KUTNO = "gtfsrt_kutno"
PROVIDER_LEGNICA = "gtfsrt_legnica"
PROVIDER_GZM = "gtfsrt_gzm"
PROVIDER_KRAKOW = "gtfsrt_krakow"
PROVIDER_SZCZECIN = "gtfsrt_szczecin"
PROVIDER_WARSZAWA = "gtfsrt_warszawa"
PROVIDER_ELK = "gtfsrt_elk"
PROVIDER_WKD = "gtfsrt_wkd"
PROVIDER_BIALYSTOK = "gtfs_bialystok"
PROVIDER_OLSZTYN = "gtfs_olsztyn"
PROVIDER_OPOLE = "gtfs_opole"
PROVIDER_RZESZOW = "gtfs_rzeszow"
PROVIDER_LESZNO = "gtfs_leszno"

GTFSRT_PROVIDERS = {
    PROVIDER_POZNAN, PROVIDER_LUBLIN, PROVIDER_KIELCE,
    PROVIDER_RADOM, PROVIDER_CZESTOCHOWA, PROVIDER_ELBLAG, PROVIDER_GORZOW,
    PROVIDER_SUWALKI, PROVIDER_PRZEMYSL, PROVIDER_RYBNIK, PROVIDER_KUTNO,
    PROVIDER_LEGNICA, PROVIDER_GZM, PROVIDER_SZCZECIN, PROVIDER_WARSZAWA,
    PROVIDER_ELK, PROVIDER_WKD,
    PROVIDER_BIALYSTOK, PROVIDER_OLSZTYN, PROVIDER_OPOLE, PROVIDER_RZESZOW, PROVIDER_LESZNO,
}

KIEDYPRZYJEDZIE_BASE_URLS = {
    PROVIDER_PKS_GDANSK: KIEDYPRZYJEDZIE_PKS_GDANSK_URL,
    PROVIDER_ALBATROS: KIEDYPRZYJEDZIE_ALBATROS_URL,
    PROVIDER_GRYF: KIEDYPRZYJEDZIE_GRYF_URL,
    PROVIDER_NORD_EXPRESS: KIEDYPRZYJEDZIE_NORD_EXPRESS_URL,
    PROVIDER_PKS_GDYNIA: KIEDYPRZYJEDZIE_PKS_GDYNIA_URL,
    PROVIDER_MZK_MALBORK: KIEDYPRZYJEDZIE_MZK_MALBORK_URL,
    PROVIDER_PKS_SLUPSK: KIEDYPRZYJEDZIE_PKS_SLUPSK_URL,
    PROVIDER_MZK_STAROGARD: KIEDYPRZYJEDZIE_MZK_STAROGARD_URL,
    PROVIDER_PKS_STAROGARD: KIEDYPRZYJEDZIE_PKS_STAROGARD_URL,
    PROVIDER_BYTOW: KIEDYPRZYJEDZIE_BYTOW_URL,
    PROVIDER_CZLUCHOW: KIEDYPRZYJEDZIE_CZLUCHOW_URL,
}

TIME4BUS_BASE_URLS = {
    PROVIDER_TCZEW: TIME4BUS_API_BASE,
}

KIEDYPRZYJEDZIE_PROVIDERS = set(KIEDYPRZYJEDZIE_BASE_URLS)
TIME4BUS_PROVIDERS = set(TIME4BUS_BASE_URLS)

PROVIDER_LABELS = {
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
    PROVIDER_TCZEW: "Tczew",
    PROVIDER_LODZ: "MPK \u0141\u00f3d\u017a",
    PROVIDER_POZNAN: "ZTM Pozna\u0144",
    PROVIDER_KRAKOW: "ZTP Krak\u00f3w",
    PROVIDER_SZCZECIN: "ZDiTM Szczecin",
    PROVIDER_WARSZAWA: "ZTM Warszawa",
    PROVIDER_ELK: "MZK Ełk",
    PROVIDER_WKD: "WKD",
    PROVIDER_LUBLIN: "ZTM Lublin",
    PROVIDER_KIELCE: "MPK Kielce",
    PROVIDER_RADOM: "MZDiK Radom",
    PROVIDER_CZESTOCHOWA: "MPK Częstochowa",
    PROVIDER_ELBLAG: "ZKM Elbląg",
    PROVIDER_GORZOW: "MZK Gorzów Wlkp.",
    PROVIDER_SUWALKI: "PGK Suwałki",
    PROVIDER_PRZEMYSL: "MZK Przemyśl",
    PROVIDER_RYBNIK: "ZTZ Rybnik",
    PROVIDER_KUTNO: "MZK Kutno",
    PROVIDER_LEGNICA: "MPK Legnica",
    PROVIDER_GZM: "ZTM GZM (Katowice)",
    PROVIDER_BIALYSTOK: "BKM Białystok",
    PROVIDER_OLSZTYN: "ZDZiT Olsztyn",
    PROVIDER_OPOLE: "MZK Opole",
    PROVIDER_RZESZOW: "ZTM Rzeszów",
    PROVIDER_LESZNO: "MZK Leszno",
}

PROVIDER_COLORS = {
    PROVIDER_ZTM: "#DA2128",
    PROVIDER_ZKM: "#005eb8",
    PROVIDER_MZK: "#478AC9",
    PROVIDER_PLK: "#1a1a2e",
    PROVIDER_PKS_GDANSK: "#475569",
    PROVIDER_ALBATROS: "#166534",
    PROVIDER_GRYF: "#2f2f2f",
    PROVIDER_NORD_EXPRESS: "#9d174d",
    PROVIDER_PKS_GDYNIA: "#0f766e",
    PROVIDER_MZK_MALBORK: "#14532d",
    PROVIDER_PKS_SLUPSK: "#0f172a",
    PROVIDER_MZK_STAROGARD: "#7f1d1d",
    PROVIDER_PKS_STAROGARD: "#1e3a8a",
    PROVIDER_BYTOW: "#155e75",
    PROVIDER_CZLUCHOW: "#991b1b",
    PROVIDER_TCZEW: "#1d4ed8",
    PROVIDER_LODZ: "#e11d48",
    PROVIDER_POZNAN: "#15803d",
    PROVIDER_LUBLIN: "#0054a0",
    PROVIDER_KIELCE: "#006d3f",
    PROVIDER_RADOM: "#1e3a8a",
    PROVIDER_CZESTOCHOWA: "#e30613",
    PROVIDER_ELBLAG: "#003d7c",
    PROVIDER_GORZOW: "#009640",
    PROVIDER_SUWALKI: "#2e5090",
    PROVIDER_PRZEMYSL: "#1b4f8f",
    PROVIDER_RYBNIK: "#e4002b",
    PROVIDER_KUTNO: "#0072bc",
    PROVIDER_LEGNICA: "#d4213d",
    PROVIDER_GZM: "#009b3a",
    PROVIDER_KRAKOW: "#e2001a",
    PROVIDER_SZCZECIN: "#005ca9",
    PROVIDER_WARSZAWA: "#c4161c",
    PROVIDER_ELK: "#1a5276",
    PROVIDER_WKD: "#4a235a",
    PROVIDER_BIALYSTOK: "#1e40af",
    PROVIDER_OLSZTYN: "#065f46",
    PROVIDER_OPOLE: "#7c2d12",
    PROVIDER_RZESZOW: "#4338ca",
    PROVIDER_LESZNO: "#0f766e",
}

CONF_STOPS = "stops"
CONF_STOP_ID = "stop_id"
CONF_PROVIDER = "provider"
CONF_NAME = "name"
CONF_API_KEY = "api_key"
CONF_PLK_TIER = "plk_tier"
CONF_SLEEP_START = "sleep_start"
CONF_SLEEP_END = "sleep_end"
CONF_SLEEP_ENABLED = "sleep_enabled"

DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SLEEP_START = "00:00"
DEFAULT_SLEEP_END = "04:30"
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
