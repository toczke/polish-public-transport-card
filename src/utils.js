/**
 * Polish Transport Card
 * Unified Lovelace card for Polish public transport providers.
 * Reads data from the Polish Transport HA integration sensors.
 */

export const CARD_VERSION = "2.0.1";

export const LOCALE = {
  pl: {
    no_entities: "Dodaj encje sensorów w konfiguracji",
    no_departures: "Brak nadchodzących odjazdów",
    unavailable: "Dane niedostępne — sprawdź połączenie",
    missing_entities: "Brak encji w HA — sprawdź konfigurację karty",
    plk_rate_limit: "Limit API wyczerpany — dane odświeżą się automatycznie",
    cancelled: "odwołany",
    track: "tor",
    min: "min",
    departing: "Odjeżdża",
    in: "za",
    show_on_map: "Pokaż pojazd na mapie",
    bike: "Rower",
    wheelchair: "Wózek",
    ac: "Klimatyzacja",
    ticket_machine: "Biletomat",
    platform: "peron",
    last_update: "Odświeżono",
    refresh: "Odśwież",
    refreshing: "Odświeżanie…",
    grouped: "Grupuj po linii",
    next: "Następny",
    select_entities: "Wybierz encje",
    other: "Inne",
    train_no: "nr",
    trains: "Pociągi (SKM/IC/PR)",
    map_refresh: "Odświeżanie co 30 s",
    map_title: "Mapa pojazdu",
    close: "Zamknij",
    on_time: "o czasie",
    no_route: "?",
    editor_data: "Dane",
    editor_appearance: "Wygląd",
    editor_filtering: "Filtrowanie",
    editor_interactions: "Interakcje",
    editor_advanced: "Zaawansowane",
  },
  en: {
    no_entities: "Add sensor entities in configuration",
    no_departures: "No upcoming departures",
    unavailable: "Data unavailable — check connection",
    missing_entities: "Configured entities were not found in Home Assistant",
    plk_rate_limit: "API rate limit reached — data will refresh automatically",
    cancelled: "cancelled",
    track: "track",
    min: "min",
    departing: "Departing",
    in: "in",
    show_on_map: "Show vehicle on map",
    bike: "Bike",
    wheelchair: "Wheelchair",
    ac: "A/C",
    ticket_machine: "Ticket machine",
    platform: "platform",
    last_update: "Updated",
    refresh: "Refresh",
    refreshing: "Refreshing…",
    grouped: "Group by line",
    next: "Next",
    select_entities: "Select entities",
    other: "Other",
    train_no: "No.",
    trains: "Trains (SKM/IC/PR)",
    map_refresh: "Refreshing every 30 s",
    map_title: "Vehicle map",
    close: "Close",
    on_time: "on time",
    no_route: "?",
    editor_data: "Data",
    editor_appearance: "Appearance",
    editor_filtering: "Filtering",
    editor_interactions: "Interactions",
    editor_advanced: "Advanced",
  },
};

export function t(key) {
  const lang = (document.documentElement.lang || navigator.language || "pl").slice(0, 2);
  return (LOCALE[lang] || LOCALE.pl)[key] || LOCALE.pl[key] || key;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]);
}

export function parseVehiclePosition(lat, lng) {
  if (lat == null || lng == null || lat === "" || lng === "") return null;
  const parsedLat = Number(lat);
  const parsedLng = Number(lng);
  if (!Number.isFinite(parsedLat) || !Number.isFinite(parsedLng)) return null;
  if (parsedLat < -90 || parsedLat > 90 || parsedLng < -180 || parsedLng > 180) return null;
  return [parsedLat, parsedLng];
}

export function minutesUntil(isoStr) {
  if (!isoStr) return null;
  let dep;
  if (/^\d{1,2}:\d{2}/.test(isoStr)) {
    const now = new Date();
    const [h, m, s] = isoStr.split(":").map(Number);
    dep = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, s || 0);
    if ((dep - now) < -3600000) dep.setDate(dep.getDate() + 1);
  } else {
    dep = new Date(isoStr);
  }
  if (isNaN(dep.getTime())) return null;
  return Math.round((dep - Date.now()) / 60000);
}

export function formatTime(isoStr, locale = null) {
  if (!isoStr) return "—";
  if (/^\d{1,2}:\d{2}/.test(isoStr)) return isoStr.slice(0, 5);
  return new Date(isoStr).toLocaleTimeString(
    locale || document.documentElement.lang || "pl-PL",
    { hour: "2-digit", minute: "2-digit" }
  );
}

export function formatMins(min) {
  if (min === null || min < 0) return "";
  if (min === 0) return "&lt;1 min";
  if (min >= 60) { const h = Math.floor(min/60), m = min%60; return m ? `${h}h ${m}min` : `${h}h`; }
  return `${min} min`;
}

export function routeColor(route, provider, gtfsColor = null) {
  if (gtfsColor) return gtfsColor;
  const s = String(route || "");
  if (/^[Nn]/.test(s)) return "#1e293b";  // Night lines (all providers)
  if (provider === "zkm_gdynia") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n >= 20 && n <= 29) return "#0891b2";
    return "#ea580c";
  }
  if (provider === "mzk_wejherowo") return "#478AC9";
  if (provider === "plk_rail") {
    const r = s.toUpperCase();
    if (r.startsWith("S") && r.length <= 3) return "#1a3668";  // SKM: S1, S2, S3...
    if (r === "EIP" || r === "EIC") return "#1a1a4e";
    if (r === "IC") return "#f57c00";
    if (r === "TLK") return "#7b1fa2";
    return "#d32f2f";  // Polregio R, RE, PKM, Os
  }
  if (provider === "ztm_gdansk") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n < 100) {
      if (n >= 90) return "#8b5cf6";  // 9x special
      if (n >= 60 && n < 70) return "#f59e0b";  // 6x seasonal summer
      if (n <= 15) return "#0369a1";  // tram (1-13)
      return "#DA2128";  // bus
    }
    return "#DA2128";
  }
  if (provider === "gtfsrt_poznan") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 18) return "#006b3f";  // tram
    if (!isNaN(n) && n >= 100) return "#15803d";  // bus 100+
    return "#2d8a4e";
  }
  if (provider === "gtfsrt_lublin") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 10) return "#1565c0";  // trolejbus
    if (!isNaN(n) && n >= 150) return "#0d47a1";  // express
    return "#1976d2";  // bus
  }
  if (provider === "gtfsrt_kielce") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 5) return "#004d40";  // tram (Kielce has none but future-proof)
    return "#00796b";  // bus
  }
  if (provider === "gtfsrt_czestochowa") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 15) return "#b71c1c";  // tram
    return "#d32f2f";  // bus
  }
  if (provider === "gtfsrt_elblag") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 5) return "#01579b";  // tram
    return "#0277bd";  // bus
  }
  if (provider === "gtfsrt_gorzow") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 3) return "#1b5e20";  // tram
    return "#2e7d32";  // bus
  }
  if (provider === "gtfsrt_rybnik") return "#880e4f";
  if (provider === "gtfsrt_gzm") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 43) return "#009b3a";  // tram
    return "#1565c0";  // bus
  }
  if (provider === "gtfsrt_radom") return "#4a148c";
  if (provider === "gtfsrt_suwalki") return "#283593";
  if (provider === "gtfsrt_przemysl") return "#e65100";
  if (provider === "gtfsrt_kutno") return "#006064";
  if (provider === "gtfsrt_legnica") return "#b71c1c";
  if (provider === "mpk_lodz") {
    const n = parseInt(s, 10);
    if (!isNaN(n) && n <= 20) return "#ad1457";  // tram
    return "#c62828";  // bus
  }
  if (PROVIDER_BADGE_COLORS[provider]) return PROVIDER_BADGE_COLORS[provider];
  return "#005eb8";
}

export function normalizeText(t) {
  return (t || "").replace(/\s/g, "").toLowerCase().replace(/\d+$/, "");
}

export function normalizeList(value) {
  if (Array.isArray(value)) return value.map(v => String(v).trim()).filter(Boolean);
  if (value === undefined || value === null) return [];
  return String(value).split(",").map(v => v.trim()).filter(Boolean);
}

export function normalizeEntityEntry(item) {
  if (typeof item === "string") return { entity: item };
  if (!item || typeof item !== "object" || typeof item.entity !== "string") return null;
  const entry = { entity: item.entity };
  if ("filter_routes" in item) entry.filter_routes = normalizeList(item.filter_routes);
  if ("exclude_routes" in item) entry.exclude_routes = normalizeList(item.exclude_routes);
  if ("max_departures" in item) entry.max_departures = Math.max(1, Math.min(100, parseInt(item.max_departures) || 0)) || null;
  if ("destination_filter" in item) entry.destination_filter = normalizeList(item.destination_filter);
  if ("exclude_destinations" in item) entry.exclude_destinations = normalizeList(item.exclude_destinations);
  if ("filter_vehicle_types" in item) entry.filter_vehicle_types = normalizeList(item.filter_vehicle_types).map(v => v.toLowerCase());
  if ("filter_providers" in item) entry.filter_providers = normalizeList(item.filter_providers);
  if ("filter_platform" in item) entry.filter_platform = item.filter_platform == null ? "" : String(item.filter_platform);
  if ("filter_track" in item) entry.filter_track = item.filter_track == null ? "" : String(item.filter_track);
  if ("realtime_only" in item) entry.realtime_only = item.realtime_only === true;
  if ("hide_terminus" in item) entry.hide_terminus = item.hide_terminus === true;
  if ("hide_cancelled" in item) entry.hide_cancelled = item.hide_cancelled === true;
  if ("max_minutes" in item) entry.max_minutes = Math.max(0, Math.min(1440, parseInt(item.max_minutes) || 0));
  if ("hide_departed" in item) entry.hide_departed = item.hide_departed === true;
  if ("departed_grace_minutes" in item) entry.departed_grace_minutes = Math.max(0, Math.min(60, parseInt(item.departed_grace_minutes) || 0));
  if ("only_low_floor" in item) entry.only_low_floor = item.only_low_floor === true;
  if ("only_bike" in item) entry.only_bike = item.only_bike === true;
  if ("only_ac" in item) entry.only_ac = item.only_ac === true;
  if ("only_ticket_machine" in item) entry.only_ticket_machine = item.only_ticket_machine === true;
  if ("highlight_mode" in item) entry.highlight_mode = item.highlight_mode === true;
  return entry;
}

export function normalizeActionConfig(cfg, fallbackAction = "none") {
  if (!cfg || typeof cfg !== "object") return { action: fallbackAction };
  const action = String(cfg.action || fallbackAction).toLowerCase();
  const out = { action };
  if (cfg.navigation_path) out.navigation_path = String(cfg.navigation_path);
  if (cfg.url_path) out.url_path = String(cfg.url_path);
  if (cfg.perform_action) out.perform_action = String(cfg.perform_action);
  if (cfg.service) out.service = String(cfg.service);
  if (cfg.data && typeof cfg.data === "object") out.data = cfg.data;
  if (cfg.target && typeof cfg.target === "object") out.target = cfg.target;
  return out;
}

export function fireHassEvent(node, type, detail = {}) {
  node.dispatchEvent(new CustomEvent(type, { detail, bubbles: true, composed: true }));
}

export const PROVIDER_HEADER_COLORS = {
  kiedyprzyjedzie_pks_gdansk: "#475569",
  kiedyprzyjedzie_albatros: "#166534",
  kiedyprzyjedzie_gryf: "#2f2f2f",
  kiedyprzyjedzie_nord_express: "#9d174d",
  kiedyprzyjedzie_pks_gdynia: "#0f766e",
  kiedyprzyjedzie_mzk_malbork: "#14532d",
  kiedyprzyjedzie_pks_slupsk: "#0f172a",
  kiedyprzyjedzie_mzk_starogard: "#7f1d1d",
  kiedyprzyjedzie_pks_starogard: "#1e3a8a",
  kiedyprzyjedzie_bytow: "#155e75",
  kiedyprzyjedzie_czluchow: "#991b1b",
  kiedyprzyjedzie_czernica: "#1e3a8a",
  time4bus_tczew: "#1d4ed8",
  gtfsrt_poznan: "#15803d",
  gtfsrt_lublin: "#0054a0",
  gtfsrt_kielce: "#006d3f",
  gtfsrt_radom: "#4a2080",
  gtfsrt_czestochowa: "#e30613",
  gtfsrt_elblag: "#003d7c",
  gtfsrt_gorzow: "#009640",
  gtfsrt_suwalki: "#2e5090",
  gtfsrt_przemysl: "#d4760a",
  gtfsrt_rybnik: "#8b1a2d",
  gtfsrt_kutno: "#0072bc",
  gtfsrt_legnica: "#d4213d",
  gtfsrt_gzm: "#009b3a",
  zbiorkom_krakow: "#e2001a",
  gtfsrt_szczecin: "#005ca9",
  gtfsrt_warszawa: "#c4161c",
  gtfsrt_elk: "#1a5276",
  gtfsrt_wkd: "#4a235a",
  gtfs_bialystok: "#1e40af",
  gtfs_olsztyn: "#065f46",
  gtfs_opole: "#7c2d12",
  gtfs_rzeszow: "#4338ca",
  gtfs_leszno: "#0f766e",
  mpk_lodz: "#e11d48",
};

export const PROVIDER_DISPLAY_NAMES = {
  ztm_gdansk: "ZTM Gdańsk",
  zkm_gdynia: "ZKM Gdynia",
  mzk_wejherowo: "MZK Wejherowo",
  plk_rail: "Polskie Linie Kolejowe",
  kiedyprzyjedzie_pks_gdansk: "PKS Gdańsk",
  kiedyprzyjedzie_albatros: "Albatros",
  kiedyprzyjedzie_gryf: "GRYF",
  kiedyprzyjedzie_nord_express: "Nord Express",
  kiedyprzyjedzie_pks_gdynia: "PKS Gdynia",
  kiedyprzyjedzie_mzk_malbork: "MZK Malbork",
  kiedyprzyjedzie_pks_slupsk: "PKS Słupsk",
  kiedyprzyjedzie_mzk_starogard: "MZK Starogard",
  kiedyprzyjedzie_pks_starogard: "PKS Starogard",
  kiedyprzyjedzie_bytow: "Komunikacja Miejska Bytów",
  kiedyprzyjedzie_czluchow: "Powiat Człuchowski",
  kiedyprzyjedzie_czernica: "Gmina Czernica",
  time4bus_tczew: "Komunikacja Miejska Tczew",
  gtfsrt_poznan: "ZTM Poznań",
  gtfsrt_lublin: "ZTM Lublin",
  gtfsrt_kielce: "MPK Kielce",
  gtfsrt_radom: "MZDiK Radom",
  gtfsrt_czestochowa: "MPK Częstochowa",
  gtfsrt_elblag: "ZKM Elbląg",
  gtfsrt_gorzow: "MZK Gorzów Wlkp.",
  gtfsrt_suwalki: "PGK Suwałki",
  gtfsrt_przemysl: "MZK Przemyśl",
  gtfsrt_rybnik: "ZTZ Rybnik",
  gtfsrt_kutno: "MZK Kutno",
  gtfsrt_legnica: "MPK Legnica",
  gtfsrt_gzm: "ZTM GZM (Katowice)",
  zbiorkom_krakow: "ZTP Kraków",
  gtfsrt_szczecin: "ZDiTM Szczecin",
  gtfsrt_warszawa: "ZTM Warszawa",
  gtfsrt_elk: "MZK Ełk",
  gtfsrt_wkd: "WKD",
  gtfs_bialystok: "BKM Białystok",
  gtfs_olsztyn: "ZDZiT Olsztyn",
  gtfs_opole: "MZK Opole",
  gtfs_rzeszow: "ZTM Rzeszów",
  gtfs_leszno: "MZK Leszno",
  mpk_lodz: "MPK Łódź",
};

export const PROVIDER_BADGE_COLORS = {
  kiedyprzyjedzie_pks_gdansk: "#0f766e",
  kiedyprzyjedzie_albatros: "#22c55e",
  kiedyprzyjedzie_gryf: "#facc15",
  kiedyprzyjedzie_nord_express: "#ec4899",
  kiedyprzyjedzie_pks_gdynia: "#16a34a",
  kiedyprzyjedzie_mzk_malbork: "#d97706",
  kiedyprzyjedzie_pks_slupsk: "#2563eb",
  kiedyprzyjedzie_mzk_starogard: "#dc2626",
  kiedyprzyjedzie_pks_starogard: "#0ea5e9",
  kiedyprzyjedzie_bytow: "#14b8a6",
  kiedyprzyjedzie_czluchow: "#f97316",
  kiedyprzyjedzie_czernica: "#3b82f6",
  time4bus_tczew: "#dc2626",
  gtfsrt_poznan: "#22c55e",
  gtfsrt_lublin: "#3b82f6",
  gtfsrt_kielce: "#10b981",
  gtfsrt_radom: "#8b5cf6",
  gtfsrt_czestochowa: "#ef4444",
  gtfsrt_elblag: "#0ea5e9",
  gtfsrt_gorzow: "#34d399",
  gtfsrt_suwalki: "#6366f1",
  gtfsrt_przemysl: "#f59e0b",
  gtfsrt_rybnik: "#e11d48",
  gtfsrt_kutno: "#06b6d4",
  gtfsrt_legnica: "#f43f5e",
  gtfsrt_gzm: "#22c55e",
  zbiorkom_krakow: "#dc2626",
  gtfsrt_szczecin: "#2563eb",
  gtfsrt_warszawa: "#b91c1c",
  gtfsrt_elk: "#0369a1",
  gtfsrt_wkd: "#7c3aed",
  gtfs_bialystok: "#3b82f6",
  gtfs_olsztyn: "#10b981",
  gtfs_opole: "#f97316",
  gtfs_rzeszow: "#8b5cf6",
  gtfs_leszno: "#14b8a6",
  mpk_lodz: "#fb7185",
};



export const PROVIDER_LABELS = {
  ztm_gdansk: "ZTM Gdańsk",
  zkm_gdynia: "ZKM Gdynia",
  mzk_wejherowo: "MZK Wejherowo",
  plk_rail: "Polskie Linie Kolejowe",
  kiedyprzyjedzie_pks_gdansk: "PKS Gdańsk",
  kiedyprzyjedzie_albatros: "Albatros",
  kiedyprzyjedzie_gryf: "GRYF",
  kiedyprzyjedzie_nord_express: "Nord Express",
  kiedyprzyjedzie_pks_gdynia: "PKS Gdynia",
  kiedyprzyjedzie_mzk_malbork: "MZK Malbork",
  kiedyprzyjedzie_pks_slupsk: "PKS Słupsk",
  kiedyprzyjedzie_mzk_starogard: "MZK Starogard",
  kiedyprzyjedzie_pks_starogard: "PKS Starogard",
  kiedyprzyjedzie_bielsko: "MZK Bielsko-Biała",
  kiedyprzyjedzie_bytow: "Bytów",
  kiedyprzyjedzie_czluchow: "Powiat Człuchowski",
  kiedyprzyjedzie_czernica: "Gmina Czernica",
  time4bus_tczew: "Time4BUS Tczew",
  gtfsrt_poznan: "ZTM Poznań",
  gtfsrt_lublin: "ZTM Lublin",
  gtfsrt_kielce: "MPK Kielce",
  gtfsrt_radom: "MZDiK Radom",
  gtfsrt_czestochowa: "MPK Częstochowa",
  gtfsrt_elblag: "ZKM Elbląg",
  gtfsrt_gorzow: "MZK Gorzów",
  gtfsrt_suwalki: "PGK Suwałki",
  gtfsrt_przemysl: "MZK Przemyśl",
  gtfsrt_rybnik: "ZTZ Rybnik",
  gtfsrt_kutno: "MZK Kutno",
  gtfsrt_legnica: "MPK Legnica",
  gtfsrt_gzm: "ZTM GZM",
  gtfsrt_szczecin: "ZDiTM Szczecin",
  gtfsrt_warszawa: "ZTM Warszawa",
  gtfsrt_elk: "MZK Ełk",
  gtfsrt_wkd: "WKD",
  gtfs_bialystok: "BKM Białystok",
  gtfs_olsztyn: "ZDZiT Olsztyn",
  gtfs_opole: "MZK Opole",
  gtfs_rzeszow: "ZTM Rzeszów",
  gtfs_bydgoszcz: "ZDMiKP Bydgoszcz",
  gtfs_mielec: "MKS Mielec",
  gtfs_oswiecim: "MZK Oświęcim",
  gtfs_radomsko: "MPK Radomsko",
  gtfs_debica: "MKS Dębica",
  gtfs_kolobrzeg: "KM Kołobrzeg",
  gtfs_sanok: "SPGK Sanok",
  gtfs_ostroleka: "MZK Ostrołęka",
  gtfs_leszno: "MZK Leszno",
  gtfs_swinoujscie: "KA Świnoujście",
  gtfs_walbrzych: "ZKM Wałbrzych",
  gtfs_tarnow: "MPK Tarnów",
  gtfs_starachowice: "MZK Starachowice",
  gtfs_siedlce: "MPK Siedlce",
  gtfs_plock: "KM Płock",
  gtfs_pila: "MZK Piła",
  gtfs_krosno: "MKS Krosno",
  gtfs_koszalin: "MZK Koszalin",
  gtfs_konin: "MZK Konin",
  gtfs_kalisz: "MZK Kalisz",
  gtfsrt_wroclaw: "MPK Wrocław",
  gtfsrt_torun: "MZK Toruń",
  zbiorkom_krakow: "ZTP Kraków",
  mpk_lodz: "MPK Łódź",
};

export function providerLabel(key) {
  return PROVIDER_LABELS[key] || String(key || "").replaceAll("_", " ");
}
