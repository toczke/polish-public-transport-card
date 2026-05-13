/**
 * MZKZG Transport Card
 * Unified Lovelace card for ZTM Gdańsk, ZKM Gdynia and kiedyPrzyjedzie.pl carriers
 * Reads data from mzkzg_transport HA integration sensors.
 */

const MZKZG_VERSION = "1.2.1";

const LOCALE = {
  pl: {
    no_entities: "Dodaj encje sensorów w konfiguracji",
    no_departures: "Brak nadchodzących odjazdów",
    unavailable: "Dane niedostępne — sprawdź połączenie",
    plk_rate_limit: "Limit API wyczerpany — dane odświeżą się automatycznie",
    cancelled: "odwołany",
    track: "tor",
    min: "min",
  },
  en: {
    no_entities: "Add sensor entities in configuration",
    no_departures: "No upcoming departures",
    unavailable: "Data unavailable — check connection",
    plk_rate_limit: "API rate limit reached — data will refresh automatically",
    cancelled: "cancelled",
    track: "track",
    min: "min",
  },
};

function t(key) {
  const lang = (document.documentElement.lang || navigator.language || "pl").slice(0, 2);
  return (LOCALE[lang] || LOCALE.pl)[key] || LOCALE.pl[key] || key;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[c]);
}

function minutesUntil(isoStr) {
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

function formatTime(isoStr) {
  if (!isoStr) return "—";
  if (/^\d{1,2}:\d{2}/.test(isoStr)) return isoStr.slice(0, 5);
  return new Date(isoStr).toLocaleTimeString("pl-PL", { hour: "2-digit", minute: "2-digit" });
}

function formatMins(min) {
  if (min === null || min < 0) return "";
  if (min === 0) return "&lt;1 min";
  if (min >= 60) { const h = Math.floor(min/60), m = min%60; return m ? `${h}h ${m}min` : `${h}h`; }
  return `${min} min`;
}

function routeColor(route, provider) {
  const s = String(route || "");
  if (/^[Nn]/.test(s)) return "#1e293b";  // Night lines (all providers)
  const n = parseInt(s, 10);
  if (provider === "zkm_gdynia") {
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
  // ztm_gdansk
  if (!isNaN(n) && n < 100) {
    if (n >= 90) return "#8b5cf6";  // 9x special
    if (n >= 60 && n < 70) return "#f59e0b";  // 6x seasonal summer
    if (n <= 15) return "#0369a1";  // regular tram (1-13 + reserves)
    return "#DA2128";  // bus lines 16-59, 70-89
  }
  return "#DA2128";
}

function normalizeText(t) {
  return (t || "").replace(/\s/g, "").toLowerCase().replace(/\d+$/, "");
}

/* ── CSS ─────────────────────────────────────────────────────────────────── */

const CARD_CSS = `
:host { display: block; }
* { box-sizing: border-box; margin: 0; padding: 0; }
ha-card { overflow: hidden; font-family: var(--ha-card-header-font-family, inherit); }
.header {
  padding: 8px 12px; display: flex; align-items: center; gap: 8px; user-select: none;
}
.header-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 24px; height: 24px; color: #fff; }
.header-icon svg { width: 18px; height: 18px; }
.header-body { flex: 1; min-width: 0; }
.header-title { color: #fff; font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-sub { color: rgba(255,255,255,0.72); font-size: 10px; margin-top: 1px; }
.dep-list { list-style: none; }
.dep-row { transition: opacity 0.4s, max-height 0.4s, padding 0.4s; max-height: 80px; overflow: hidden; }
.dep-row.departing { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
ha-card.e-ink .dep-row { transition: none; }
.tabs { display: flex; border-bottom: 1px solid var(--divider-color, #e5e5e5); }
.tab { flex: 1; padding: 8px 14px; font-size: 12px; font-weight: 600; color: var(--secondary-text-color, #888); cursor: pointer; white-space: nowrap; border-bottom: 2px solid transparent; text-align: center; }
.tab.active { color: var(--primary-text-color, #111); border-bottom-color: var(--primary-color, #005eb8); }
.tab:hover { color: var(--primary-text-color, #111); }
.dep-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-bottom: 1px solid var(--divider-color, #f0f0f0); min-height: 46px;
}
.dep-row:last-child { border-bottom: none; }
.dep-row.imminent { }
.dep-row.dimmed { opacity: 0.35; }
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 7px; border-radius: 6px; font-size: 13px; font-weight: 700;
  color: #fff; min-width: 40px; flex-shrink: 0;
}
.headsign {
  font-size: 13px; font-weight: 500; color: var(--primary-text-color, #111);
  flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px;
}
.headsign-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%; }
.icons { display: inline-flex; gap: 3px; align-items: center; flex-shrink: 0; white-space: nowrap; }
.icons svg { color: var(--secondary-text-color, #666); opacity: 0.8; }
.stop-name { display: block; font-size: 10px; color: var(--secondary-text-color, #888); font-weight: 400; margin-top: 1px; width: 100%; }
ha-card.compact .stop-name { display: none; }
ha-card.compact .icons { display: none; }
ha-card.compact .platform { display: none; }
ha-card.compact .footer { display: none; }
.dep-row.cancelled .headsign { text-decoration: line-through; opacity: 0.6; }
.dep-row.cancelled .badge { opacity: 0.5; }
.time-main.cancelled { font-size: 12px; color: #dc2626; font-weight: 600; }
.platform { display: inline-block; font-size: 10px; color: var(--secondary-text-color, #888); background: var(--divider-color, #e5e5e5); border-radius: 3px; padding: 1px 5px; vertical-align: middle; flex-shrink: 0; }

.time-col { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.time-main { font-size: 15px; font-weight: 600; color: var(--primary-text-color, #111); white-space: nowrap; }
.time-struck { text-decoration: line-through; opacity: 0.5; font-size: 13px; font-weight: 400; }
.time-sub { font-size: 11px; color: var(--secondary-text-color, #888); white-space: nowrap; display: flex; align-items: center; gap: 4px; }
.time-sub .dot { color: #10b981; font-weight: 700; }
.delay-badge { font-size: 11px; font-weight: 600; }
.delay-badge.late { color: #dc2626; }
.delay-badge.early { color: #0369a1; }
.state-msg { padding: 24px 16px; text-align: center; color: var(--secondary-text-color, #888); font-size: 13px; }
.state-msg .icon { font-size: 28px; display: block; margin-bottom: 8px; }
.footer { padding: 5px 14px; font-size: 10px; color: var(--secondary-text-color, #aaa); text-align: right; border-top: 1px solid var(--divider-color, #f0f0f0); }
.skel { background: var(--divider-color, #e5e5e5); border-radius: 4px; }
@keyframes shimmer { 0%,100%{opacity:.5} 50%{opacity:1} }
.skel { animation: shimmer 1.4s ease-in-out infinite; }

/* e-ink */
ha-card.e-ink { background: #fff; color: #000; border: 0; border-radius: 0; box-shadow: none; }
ha-card.e-ink .header { background: #fff !important; border-bottom: 2px solid #000; }
ha-card.e-ink .header-title, ha-card.e-ink .header-sub, ha-card.e-ink .header-icon { color: #000; }
ha-card.e-ink .header-icon ha-icon { color: #000 !important; --mdc-icon-size: 20px; }
ha-card.e-ink .stop-name, ha-card.e-ink .platform, ha-card.e-ink .icons, ha-card.e-ink .time-sub, ha-card.e-ink .footer { display: none; }
ha-card.e-ink .badge { background: #fff !important; border: 2px solid #000; color: #000; }
ha-card.e-ink .dep-row { border-bottom-color: #000; }
ha-card.e-ink .dep-row { border-bottom-color: #000; }
ha-card.e-ink .dep-row.imminent { background: #fff; }
ha-card.e-ink .badge { background: #fff !important; border: 1px solid #000; color: #000; }
ha-card.e-ink .headsign, ha-card.e-ink .time-main, ha-card.e-ink .time-sub, ha-card.e-ink .footer, ha-card.e-ink .state-msg { color: #000; }
ha-card.e-ink .time-sub .dot, ha-card.e-ink .delay-badge, ha-card.e-ink .delay-badge.late, ha-card.e-ink .delay-badge.early { color: #000; }
ha-card.e-ink .skel { animation: none; }

/* compact */
ha-card.compact .header { padding: 9px 12px; gap: 8px; }
ha-card.compact .header-icon { width: 24px; height: 24px; }
ha-card.compact .header-icon svg { width: 19px; height: 19px; }
ha-card.compact .header-title { font-size: 14px; }
ha-card.compact .header-sub { font-size: 10px; }
ha-card.compact .dep-list { padding-top: 4px; }
ha-card.compact .dep-row { min-height: 36px; padding: 6px 12px; gap: 8px; }
ha-card.compact .badge { min-width: 34px; padding: 2px 6px; font-size: 12px; }
ha-card.compact .headsign { font-size: 12px; }
ha-card.compact .time-main { font-size: 13px; }
ha-card.compact .time-sub { font-size: 10px; }
ha-card.compact .footer { padding: 5px 12px; }

/* Responsive — small cards (< 300px width) */
@container (max-width: 300px) {
  .header { padding: 10px 10px; gap: 8px; }
  .header-icon { width: 22px; height: 22px; }
  .header-icon svg { width: 17px; height: 17px; }
  .header-title { font-size: 13px; }
  .header-sub { font-size: 9px; }
  .dep-row { padding: 8px 10px; gap: 8px; min-height: 38px; }
  .badge { min-width: 34px; padding: 2px 5px; font-size: 11px; }
  .headsign { font-size: 12px; }
  .time-main { font-size: 13px; }
  .time-sub { font-size: 10px; }
  .icons { gap: 2px; }
  .platform { font-size: 9px; padding: 1px 3px; }
  .tab { padding: 6px 8px; font-size: 11px; }
  .footer { font-size: 9px; padding: 4px 10px; }
}

/* Responsive — large cards (> 500px width, e.g. tablet panels) */
@container (min-width: 500px) {
  .header { padding: 16px 18px; }
  .header-title { font-size: 17px; }
  .header-sub { font-size: 12px; }
  .dep-row { padding: 12px 18px; gap: 12px; }
  .badge { min-width: 46px; padding: 4px 9px; font-size: 14px; }
  .headsign { font-size: 14px; }
  .time-main { font-size: 16px; }
  .time-sub { font-size: 12px; }
  .footer { padding: 6px 18px; font-size: 11px; }
}

/* Container query setup */
:host { container-type: inline-size; }
ha-card { container-type: inline-size; }
`;

const BUS_ICON = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 16.01L16.01 15.99"/><path d="M6 16.01L6.01 15.99"/><path d="M20 22V15V8M20 8H18V2H22V8H20Z"/><path d="M4 20V22H6V20H4Z" fill="currentColor"/><path d="M14 20V22H16V20H14Z" fill="currentColor"/><path d="M16 20H2.6A.6.6 0 012 19.4V12.6c0-.33.27-.6.6-.6H16"/><path d="M14 8H6M14 2H6C3.79 2 2 3.79 2 6V8"/></svg>`;

// Unified SVG feature icons (official MDI, 14x14)
const ICON_BIKE = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M5,20.5A3.5,3.5 0 0,1 1.5,17A3.5,3.5 0 0,1 5,13.5A3.5,3.5 0 0,1 8.5,17A3.5,3.5 0 0,1 5,20.5M5,12A5,5 0 0,0 0,17A5,5 0 0,0 5,22A5,5 0 0,0 10,17A5,5 0 0,0 5,12M14.8,10H19V8.2H15.8L13.86,4.93C13.57,4.43 13,4.1 12.4,4.1C11.93,4.1 11.5,4.29 11.2,4.6L7.5,8.29C7.19,8.6 7,9 7,9.5C7,10.13 7.33,10.66 7.85,10.97L11.2,13V18H13V11.5L10.75,9.85L13.07,7.5M19,20.5A3.5,3.5 0 0,1 15.5,17A3.5,3.5 0 0,1 19,13.5A3.5,3.5 0 0,1 22.5,17A3.5,3.5 0 0,1 19,20.5M19,12A5,5 0 0,0 14,17A5,5 0 0,0 19,22A5,5 0 0,0 24,17A5,5 0 0,0 19,12M16,4.8C17,4.8 17.8,4 17.8,3C17.8,2 17,1.2 16,1.2C15,1.2 14.2,2 14.2,3C14.2,4 15,4.8 16,4.8Z"/></svg>`;
const ICON_WHEELCHAIR = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M18.4,11.2L14.3,11.4L16.6,8.8C16.8,8.5 16.9,8 16.8,7.5C16.7,7.2 16.6,6.9 16.3,6.7L10.9,3.5C10.5,3.2 9.9,3.3 9.5,3.6L6.8,6.1C6.3,6.6 6.2,7.3 6.7,7.8C7.1,8.3 7.9,8.3 8.4,7.9L10.4,6.1L12.3,7.2L8.1,11.5C8,11.6 8,11.7 7.9,11.7C7.4,11.9 6.9,12.1 6.5,12.4L8,13.9C8.5,13.7 9,13.5 9.5,13.5C11.4,13.5 13,15.1 13,17C13,17.6 12.9,18.1 12.6,18.5L14.1,20C14.7,19.1 15,18.1 15,17C15,15.8 14.6,14.6 13.9,13.7L17.2,13.4L17,18.2C16.9,18.9 17.4,19.4 18.1,19.5H18.2C18.8,19.5 19.3,19 19.4,18.4L19.6,12.5C19.6,12.2 19.5,11.8 19.3,11.6C19,11.3 18.7,11.2 18.4,11.2M18,5.5A2,2 0 0,0 20,3.5A2,2 0 0,0 18,1.5A2,2 0 0,0 16,3.5A2,2 0 0,0 18,5.5M12.5,21.6C11.6,22.2 10.6,22.5 9.5,22.5C6.5,22.5 4,20 4,17C4,15.9 4.3,14.9 4.9,14L6.4,15.5C6.2,16 6,16.5 6,17C6,18.9 7.6,20.5 9.5,20.5C10.1,20.5 10.6,20.4 11,20.1L12.5,21.6Z"/></svg>`;
const ICON_AC = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M20.79,13.95L18.46,14.57L16.46,13.44V10.56L18.46,9.43L20.79,10.05L21.31,8.12L19.54,7.65L20,5.88L18.07,5.36L17.45,7.69L15.45,8.82L13,7.38V5.12L14.71,3.41L13.29,2L12,3.29L10.71,2L9.29,3.41L11,5.12V7.38L8.5,8.82L6.5,7.69L5.92,5.36L4,5.88L4.47,7.65L2.7,8.12L3.22,10.05L5.55,9.43L7.55,10.56V13.45L5.55,14.58L3.22,13.96L2.7,15.89L4.47,16.36L4,18.12L5.93,18.64L6.55,16.31L8.55,15.18L11,16.62V18.88L9.29,20.59L10.71,22L12,20.71L13.29,22L14.7,20.59L13,18.88V16.62L15.5,15.17L17.5,16.3L18.12,18.63L20,18.12L19.53,16.35L21.3,15.88L20.79,13.95M9.5,10.56L12,9.11L14.5,10.56V13.44L12,14.89L9.5,13.44V10.56Z"/></svg>`;

/* ── Editor ──────────────────────────────────────────────────────────────── */

class MzkzgTransportCardEditor extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._rendered = false;
    this._firing = false;
    this._fireTimer = null;
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) { this._render(); return; }
    this._refreshEntityOptions();
  }

  setConfig(config) {
    if (this._firing) { this._firing = false; return; }
    this._config = { ...config };
    if (this._rendered) this._updateValues();
    else this._render();
  }

  _getEntities() {
    if (!this._hass) return [];
    return Object.keys(this._hass.states)
      .filter(e => e.startsWith("sensor.") && this._hass.states[e].attributes?.departures !== undefined)
      .sort();
  }

  _fire() {
    if (this._fireTimer) clearTimeout(this._fireTimer);
    this._fireTimer = setTimeout(() => this._doFire(), 300);
  }

  _fireNow() {
    if (this._fireTimer) clearTimeout(this._fireTimer);
    this._doFire();
  }

  _doFire() {
    const val = id => this.shadowRoot.getElementById(id)?.value ?? "";
    const checked = id => { const el = this.shadowRoot.getElementById(id); return el ? el.checked : (this._config[id.replace(/-/g,"_")] ?? false); };

    const entitiesEl = this.shadowRoot.getElementById("entities");
    const entities = entitiesEl ? [...entitiesEl.selectedOptions].map(o => o.value) : [];
    const filterRoutes = val("filter_routes").split(",").map(r => r.trim()).filter(Boolean);
    const autoColor = checked("header_color_auto");

    const config = {
      type: "custom:mzkzg-transport-card",
      entities: entities.length ? entities : (this._config.entities || undefined),
      title: val("title") || undefined,
      icon: val("icon") || undefined,
      header_color: autoColor ? undefined : (val("header_color") || undefined),
      max_departures: parseInt(val("max_departures")) || 10,
      display_preset: this.shadowRoot.querySelector('input[name="display_preset"]:checked')?.value || "standard",
      view_mode: this.shadowRoot.querySelector('input[name="view_mode"]:checked')?.value || "mixed",
      filter_routes: filterRoutes.length ? filterRoutes : undefined,
      destination_filter: val("destination_filter").split(",").map(s => s.trim()).filter(Boolean) || undefined,
      filter_platform: val("filter_platform") || undefined,
      filter_track: val("filter_track") || undefined,
      highlight_mode: checked("highlight_mode"),
      show_delays: checked("show_delays"),
      hide_terminus: checked("hide_terminus"),
      realtime_only: checked("realtime_only"),
      show_footer: checked("show_footer"),
      show_bike: checked("show_bike"),
      show_wheelchair: checked("show_wheelchair"),
      show_ac: checked("show_ac"),
      show_ticket_machine: checked("show_ticket_machine"),
      refresh_interval: parseInt(val("refresh_interval")) || 60,
    };

    this._config = config;
    this._firing = true;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  _refreshEntityOptions() {
    const el = this.shadowRoot.getElementById("entities");
    if (!el) return;
    const entities = this._getEntities();
    const current = [...el.options].map(o => o.value);
    if (entities.length === current.length && entities.every((e, i) => e === current[i])) return;
    const selected = new Set(this._config.entities || []);
    el.innerHTML = entities.map(e =>
      `<option value="${escapeHtml(e)}" ${selected.has(e) ? "selected" : ""}>${escapeHtml(e.replace("sensor.",""))}</option>`
    ).join("");
  }

  _updateValues() {
    const el = this.shadowRoot.getElementById("entities");
    if (el) {
      const selected = new Set(this._config.entities || []);
      for (const opt of el.options) opt.selected = selected.has(opt.value);
    }
  }

  _render() {
    const c = this._config;
    const entities = this._getEntities();
    const preset = c.display_preset || "standard";
    const isEink = preset === "e_ink";
    const autoColor = !c.header_color;

    const selectedEntities = new Set(c.entities || []);
    const entityOptions = entities.map(e =>
      `<option value="${escapeHtml(e)}" ${selectedEntities.has(e) ? "selected" : ""}>${escapeHtml(e.replace("sensor.",""))}</option>`
    ).join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .form { display: flex; flex-direction: column; gap: 16px; }
        .section { display: flex; flex-direction: column; gap: 8px; }
        .section-title { font-size: 13px; font-weight: 600; color: var(--primary-text-color, #111); margin: 0; }
        .field { display: flex; flex-direction: column; gap: 4px; }
        .field-row { display: flex; gap: 10px; }
        .field-row .field { flex: 1; min-width: 0; }
        label { font-size: 12px; font-weight: 500; color: var(--secondary-text-color, #6b7280); margin: 0; }
        input[type="text"], select { width: 100%; height: 40px; padding: 8px 12px; border: 1px solid var(--divider-color, #d1d5db); border-radius: 8px; font-size: 14px; background: var(--card-background-color, #fff); color: var(--primary-text-color); font-family: inherit; box-sizing: border-box; }
        select[multiple] { height: auto; min-height: 60px; }
        input[type="text"]:focus, select:focus { border-color: var(--primary-color); outline: none; }
        .preset-group { display: flex; gap: 8px; }
        .preset-option { flex: 1; margin: 0; position: relative; }
        .preset-option input { position: absolute; opacity: 0; width: 0; height: 0; }
        .preset-card { display: flex; flex-direction: column; align-items: center; gap: 2px; border: 1px solid var(--divider-color, #d1d5db); border-radius: 8px; padding: 10px 4px; text-align: center; cursor: pointer; }
        .preset-option input:checked + .preset-card { border-color: var(--primary-color); background: rgba(0,94,184,0.06); }
        .preset-name { font-size: 12px; font-weight: 700; color: var(--primary-text-color); }
        .preset-desc { font-size: 10px; color: var(--secondary-text-color); }
        .switch-list { display: flex; flex-direction: column; }
        .switch-row { display: flex; align-items: center; justify-content: space-between; height: 36px; padding: 0; border-bottom: 1px solid var(--divider-color, #f0f0f0); }
        .switch-row:last-child { border-bottom: none; }
        .switch-row label { flex: 1; font-size: 13px; font-weight: 400; color: var(--primary-text-color); cursor: pointer; margin: 0; }
        .switch-row input[type="checkbox"] { width: 18px; height: 18px; accent-color: var(--primary-color, #005eb8); cursor: pointer; flex-shrink: 0; }
        .color-row { display: flex; gap: 6px; align-items: center; }
        .color-row input[type="color"] { width: 40px; height: 40px; padding: 2px; border: 1px solid var(--divider-color,#d1d5db); border-radius: 8px; cursor: pointer; background: none; }
        .color-row input[type="text"] { flex: 1; }
        .color-row.disabled { opacity: 0.4; pointer-events: none; }
      </style>
      <div class="form">
        <div class="section">
          <div class="section-title">Sensory</div>
          <div class="field">
            <select id="entities" multiple size="${Math.min(Math.max(entities.length, 3), 8)}">
              ${entities.map(e => `<option value="${escapeHtml(e)}" ${(c.entities || []).includes(e) ? "selected" : ""}>${escapeHtml(e.replace("sensor.",""))}</option>`).join("")}
            </select>
          </div>
        </div>

        <div class="section">
          <div class="section-title">Wygląd</div>
          <div class="field">
            <label for="title">Tytuł</label>
            <input id="title" type="text" value="${escapeHtml(c.title || "")}" placeholder="Auto z nazwy przystanku" />
          </div>
          <div class="field">
            <label for="icon">Ikona (MDI)</label>
            <input id="icon" type="text" value="${escapeHtml(c.icon || "")}" placeholder="mdi:tram, mdi:bus, mdi:train" />
          </div>
          <div class="preset-group">
            <label class="preset-option"><input type="radio" name="display_preset" value="standard" ${preset==="standard"?"checked":""}/><span class="preset-card"><span class="preset-name">Standard</span><span class="preset-desc">Codzienny</span></span></label>
            <label class="preset-option"><input type="radio" name="display_preset" value="compact" ${preset==="compact"?"checked":""}/><span class="preset-card"><span class="preset-name">Kompakt</span><span class="preset-desc">Więcej wierszy</span></span></label>
            <label class="preset-option"><input type="radio" name="display_preset" value="e_ink" ${preset==="e_ink"?"checked":""}/><span class="preset-card"><span class="preset-name">E-ink</span><span class="preset-desc">Tylko czas</span></span></label>
          </div>
          ${!isEink ? `
          <div class="field">
            <label>Kolor nagłówka</label>
            <div class="switch-row" style="margin-bottom:6px">
              <label for="header_color_auto">Auto z providera</label>
              <input id="header_color_auto" type="checkbox" ${autoColor ? "checked" : ""}/>
            </div>
            <div class="color-row ${autoColor ? "disabled" : ""}" id="color-row">
              <input id="header_color_picker" type="color" value="${escapeHtml(c.header_color || "#005eb8")}" />
              <input id="header_color" type="text" value="${escapeHtml(c.header_color || "")}" placeholder="#005eb8" />
            </div>
          </div>` : ""}
          <div class="field">
            <label>Widok wielu przystanków</label>
            <div style="display:flex;gap:8px;margin-top:4px">
              <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--primary-text-color);cursor:pointer"><input type="radio" name="view_mode" value="mixed" ${(c.view_mode||"mixed")==="mixed"?"checked":""} style="width:auto;height:auto"/> Miks</label>
              <label style="display:flex;align-items:center;gap:4px;font-size:13px;color:var(--primary-text-color);cursor:pointer"><input type="radio" name="view_mode" value="tabs" ${c.view_mode==="tabs"?"checked":""} style="width:auto;height:auto"/> Zakładki</label>
            </div>
          </div>
        </div>

        <div class="section">
          <div class="section-title">Filtrowanie</div>
          <div class="field-row">
            <div class="field">
              <label for="max_departures">Max odjazdów</label>
              <input id="max_departures" type="text" inputmode="numeric" value="${escapeHtml(c.max_departures ?? 10)}" />
            </div>
            <div class="field">
              <label for="filter_routes">Linie</label>
              <input id="filter_routes" type="text" value="${escapeHtml((c.filter_routes || []).join(", "))}" placeholder="131, 21, S1" />
            </div>
          </div>
          <div class="field">
            <label for="destination_filter">Kierunki</label>
            <input id="destination_filter" type="text" value="${escapeHtml((c.destination_filter || []).join(", "))}" placeholder="Wrzeszcz, Oliwa" />
          </div>
          <div class="field">
            <label for="filter_platform">Peron</label>
            <input id="filter_platform" type="text" value="${escapeHtml(c.filter_platform || "")}" placeholder="np. 1" />
          </div>
          <div class="field">
            <label for="filter_track">Tor</label>
            <input id="filter_track" type="text" value="${escapeHtml(c.filter_track || "")}" placeholder="np. 502" />
          </div>
          <div class="switch-list">
            <div class="switch-row"><label for="highlight_mode">Podświetlaj zamiast ukrywać</label><input id="highlight_mode" type="checkbox" ${c.highlight_mode ? "checked" : ""}/></div>
            <div class="switch-row"><label for="hide_terminus">Ukryj kończące bieg/trasę</label><input id="hide_terminus" type="checkbox" ${c.hide_terminus !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="realtime_only">Tylko realtime</label><input id="realtime_only" type="checkbox" ${c.realtime_only ? "checked" : ""}/></div>
          </div>
        </div>

        ${!isEink ? `
        <div class="section">
          <div class="section-title">Wyświetlanie</div>
          <div class="switch-list">
            <div class="switch-row"><label for="show_delays">Opóźnienia</label><input id="show_delays" type="checkbox" ${c.show_delays !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="show_footer">Czas aktualizacji</label><input id="show_footer" type="checkbox" ${c.show_footer !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="show_bike">Miejsce na rower</label><input id="show_bike" type="checkbox" ${c.show_bike !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="show_wheelchair">Miejsce na wózek</label><input id="show_wheelchair" type="checkbox" ${c.show_wheelchair !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="show_ac">Klimatyzacja</label><input id="show_ac" type="checkbox" ${c.show_ac !== false ? "checked" : ""}/></div>
            <div class="switch-row"><label for="show_ticket_machine">Biletomat</label><input id="show_ticket_machine" type="checkbox" ${c.show_ticket_machine !== false ? "checked" : ""}/></div>
          </div>
          <div class="field" style="margin-top:8px">
            <label for="refresh_interval">Odświeżanie (s)</label>
            <input id="refresh_interval" type="text" inputmode="numeric" value="${escapeHtml(c.refresh_interval ?? 60)}" />
          </div>
        </div>` : ""}
      </div>`;

    this._rendered = true;

    // Stop key events from bubbling out of shadow DOM (HA intercepts them)
    this.shadowRoot.addEventListener("keydown", e => e.stopPropagation());

    // Text fields: debounced fire on input
    this.shadowRoot.querySelectorAll("input[type='text']").forEach(el => {
      el.addEventListener("input", () => this._fire());
    });
    // Checkboxes, radios, select: immediate fire
    this.shadowRoot.querySelectorAll("input[type='checkbox'], input[type='radio'], select").forEach(el => {
      el.addEventListener("change", () => this._fireNow());
    });
    // Auto color toggle
    // Auto color toggle — visual only, fire already handled above
    const autoCheck = this.shadowRoot.getElementById("header_color_auto");
    const colorRow = this.shadowRoot.getElementById("color-row");
    if (autoCheck && colorRow) {
      autoCheck.addEventListener("change", () => {
        colorRow.classList.toggle("disabled", autoCheck.checked);
      });
    }
    // Sync color picker
    const picker = this.shadowRoot.getElementById("header_color_picker");
    const colorInput = this.shadowRoot.getElementById("header_color");
    if (picker && colorInput) {
      picker.addEventListener("input", () => { colorInput.value = picker.value; this._fire(); });
      colorInput.addEventListener("input", () => { if (/^#[0-9a-f]{6}$/i.test(colorInput.value)) picker.value = colorInput.value; this._fire(); });
    }
  }
}

if (!customElements.get("mzkzg-transport-card-editor")) {
  customElements.define("mzkzg-transport-card-editor", MzkzgTransportCardEditor);
}

/* ── Card ────────────────────────────────────────────────────────────────── */

class MzkzgTransportCard extends HTMLElement {
  constructor() {
    super();
    this._config = {};
    this._hass = null;
    this._rendered = false;
    this._activeTab = 0;
    this._tickTimer = null;
    this.attachShadow({ mode: "open" });
  }

  static getConfigElement() { return document.createElement("mzkzg-transport-card-editor"); }
  static getStubConfig() {
    return { type: "custom:mzkzg-transport-card", entities: [], max_departures: 10, show_delays: true, hide_terminus: true, show_bike: true, show_wheelchair: true, show_footer: true };
  }

  setConfig(config) {
    if (!config) throw new Error("No configuration provided");
    if (config.entities && !Array.isArray(config.entities)) throw new Error("entities must be an array");
    this._config = {
      ...config,
      max_departures: Math.max(3, Math.min(20, parseInt(config.max_departures) || 10)),
      refresh_interval: Math.max(5, Math.min(600, parseInt(config.refresh_interval) || 60)),
      display_preset: config.display_preset || "standard",
      view_mode: config.view_mode || "mixed",
      show_delays: config.show_delays !== false,
      hide_terminus: config.hide_terminus !== false,
      realtime_only: config.realtime_only === true,
      highlight_mode: config.highlight_mode === true,
      show_bike: config.show_bike !== false,
      show_wheelchair: config.show_wheelchair !== false,
      show_ac: config.show_ac !== false,
      show_ticket_machine: config.show_ticket_machine !== false,
      show_stop_name: config.show_stop_name === true,
      destination_filter: Array.isArray(config.destination_filter) ? config.destination_filter : (config.destination_filter ? String(config.destination_filter).split(",").map(s=>s.trim()).filter(Boolean) : []),
      filter_platform: config.filter_platform || "",
      filter_track: config.filter_track || "",
      icon: config.icon || "",
      show_footer: config.show_footer !== false,
    };
    if (this._rendered) this._fullRender();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered) { this._fullRender(); this._startTick(); }
    else {
      // Only update if our entities' states changed
      const key = (this._config.entities || []).map(e => hass.states[e]?.last_updated).join(",");
      if (key !== this._lastStateKey) { this._lastStateKey = key; this._updateContent(); }
    }
  }

  getCardSize() { return Math.ceil((this._config.max_departures || 10) / 2) + 2; }

  getLayoutOptions() {
    return { grid_rows: Math.ceil((this._config.max_departures || 10) / 2) + 2, grid_min_rows: 3, grid_columns: 4, grid_min_columns: 2 };
  }

  connectedCallback() { this._startTick(); }
  disconnectedCallback() { if (this._tickTimer) { clearInterval(this._tickTimer); this._tickTimer = null; } }

  _startTick() {
    if (this._tickTimer) clearInterval(this._tickTimer);
    if (this._config.display_preset === "e_ink") return;
    this._tickTimer = setInterval(() => this._updateContent(), (this._config.refresh_interval || 60) * 1000);
  }

  _getDepartures() {
    if (!this._hass || !this._config.entities?.length) return [];
    const c = this._config;
    let deps = [];

    // In tabs mode, only show departures from active tab entity
    const entities = (c.view_mode === "tabs" && c.entities.length > 1)
      ? [c.entities[this._activeTab] || c.entities[0]]
      : c.entities;

    for (const entityId of entities) {
      const state = this._hass.states[entityId];
      if (!state || !state.attributes?.departures) continue;
      const provider = state.attributes.provider || "";
      const stopName = state.attributes.stop_name || "";

      for (const d of (Array.isArray(state.attributes.departures) ? state.attributes.departures : [])) {
        deps.push({ ...d, _provider: d.provider || provider, _stopName: stopName });
      }
    }

    // Filter already departed
    deps = deps.filter(d => {
      const min = minutesUntil(d.estimated_time);
      return min === null || min >= -1;
    });

    // Realtime only
    if (c.realtime_only) deps = deps.filter(d => d.realtime);

    // Hide terminus
    if (c.hide_terminus) {
      deps = deps.filter(d => {
        if (!d._stopName) return true;
        return normalizeText(d.headsign) !== normalizeText(d._stopName);
      });
    }

    // Filter routes
    if (c.filter_routes?.length) {
      const fs = new Set(c.filter_routes.map(r => r.toUpperCase()));
      if (c.highlight_mode) {
        deps.forEach(d => { d._dimmed = !fs.has(String(d.route).toUpperCase()); });
      } else {
        deps = deps.filter(d => fs.has(String(d.route).toUpperCase()));
      }
    }

    // Destination filter
    if (c.destination_filter?.length) {
      const df = c.destination_filter.map(f => f.toLowerCase());
      deps = deps.filter(d => {
        const h = (d.headsign || "").toLowerCase();
        return df.some(f => h.includes(f));
      });
    }

    // Platform/track filter
    if (c.filter_platform) {
      deps = deps.filter(d => String(d.platform || "") === c.filter_platform);
    }
    if (c.filter_track) {
      deps = deps.filter(d => String(d.track || "") === c.filter_track);
    }

    // Sort by departure time
    deps.sort((a, b) => {
      const ma = minutesUntil(a.estimated_time) ?? 9999;
      const mb = minutesUntil(b.estimated_time) ?? 9999;
      return ma - mb;
    });

    return deps.slice(0, c.max_departures);
  }

  _getAutoIcon() {
    if (!this._hass || !this._config.entities?.length) return BUS_ICON;
    const providers = new Set();
    for (const eid of this._config.entities) {
      const s = this._hass.states[eid];
      if (s?.attributes?.provider) providers.add(s.attributes.provider);
    }
    if (providers.size === 1 && providers.has("plk_rail")) return `<ha-icon icon="mdi:train" style="color:#fff;--mdc-icon-size:20px"></ha-icon>`;
    return `<ha-icon icon="mdi:bus-stop" style="color:#fff;--mdc-icon-size:20px"></ha-icon>`;
  }

  _getHeaderColor() {
    if (this._config.header_color) {
      const c = this._config.header_color.replace(/[;"'{}]/g, "");
      return c;
    }
    const colors = {
      ztm_gdansk: "#DA2128",
      zkm_gdynia: "#005eb8",
      mzk_wejherowo: "#478AC9",
      plk_rail: "#1a1a2e",
      kiedyprzyjedzie_pks_gdansk: "#0f766e",
      kiedyprzyjedzie_albatros: "#1d4ed8",
      kiedyprzyjedzie_gryf: "#f59e0b",
      kiedyprzyjedzie_nord_express: "#0f172a",
      kiedyprzyjedzie_pks_gdynia: "#0e7490",
      kiedyprzyjedzie_zkm_gdynia: "#2563eb",
      kiedyprzyjedzie_mzk_malbork: "#ea580c",
      kiedyprzyjedzie_pks_slupsk: "#4f46e5",
      kiedyprzyjedzie_mzk_starogard: "#be123c",
      kiedyprzyjedzie_pks_starogard: "#7c3aed",
      kiedyprzyjedzie_bytow: "#16a34a",
      kiedyprzyjedzie_czluchow: "#64748b",
    };
    const providers = new Set();
    if (this._hass && this._config.entities?.length) {
      for (const eid of this._config.entities) {
        const s = this._hass.states[eid];
        if (s?.attributes?.provider) providers.add(s.attributes.provider);
      }
    }
    const list = [...providers];
    if (list.length === 1) return colors[list[0]] || "#005eb8";
    if (list.length >= 2) {
      // Only gradient if actually different colors
      const cols = [...new Set(list.map(p => colors[p] || "#005eb8"))];
      if (cols.length === 1) return cols[0];
      return `linear-gradient(135deg, ${cols[0]} 0%, ${cols[1]} 100%)`;
    }
    return "#005eb8";
  }

  _getTitle() {
    if (this._config.title) return this._config.title;
    if (!this._hass || !this._config.entities?.length) return "MZKZG Transport";
    const first = this._hass.states[this._config.entities[0]];
    return first?.attributes?.stop_name || first?.attributes?.friendly_name || "MZKZG Transport";
  }

  _getSubtitle() {
    if (!this._hass || !this._config.entities?.length) return "Wybierz encje";
    const providers = new Set();
    for (const eid of this._config.entities) {
      const s = this._hass.states[eid];
      if (s?.attributes?.provider) {
        const map = {
          ztm_gdansk: "ZTM Gdańsk",
          zkm_gdynia: "ZKM Gdynia",
          mzk_wejherowo: "MZK Wejherowo",
          plk_rail: "PKP/SKM",
          kiedyprzyjedzie_pks_gdansk: "PKS Gdańsk",
          kiedyprzyjedzie_albatros: "Albatros",
          kiedyprzyjedzie_gryf: "GRYF",
          kiedyprzyjedzie_nord_express: "Nord Express",
          kiedyprzyjedzie_pks_gdynia: "PKS Gdynia",
          kiedyprzyjedzie_zkm_gdynia: "ZKM Gdynia",
          kiedyprzyjedzie_mzk_malbork: "MZK Malbork",
          kiedyprzyjedzie_pks_slupsk: "PKS Słupsk",
          kiedyprzyjedzie_mzk_starogard: "MZK Starogard",
          kiedyprzyjedzie_pks_starogard: "PKS Starogard",
          kiedyprzyjedzie_bytow: "Bytów",
          kiedyprzyjedzie_czluchow: "Powiat Człuchowski",
        };
        providers.add(map[s.attributes.provider] || s.attributes.provider);
      }
    }
    return [...providers].join(" + ") || "MZKZG";
  }

  _fullRender() {
    const c = this._config;
    const cardClass = c.display_preset === "e_ink" ? "e-ink" : c.display_preset === "compact" ? "compact" : "";

    this.shadowRoot.innerHTML = `
      <style>${CARD_CSS}</style>
      <ha-card class="${cardClass}">
        <div class="header" style="background:${this._getHeaderColor()}">
          <span class="header-icon">${c.icon ? `<ha-icon icon="${escapeHtml(c.icon)}" style="color:#fff;--mdc-icon-size:20px"></ha-icon>` : this._getAutoIcon()}</span>
          <div class="header-body">
            <div class="header-title">${escapeHtml(this._getTitle())}</div>
            <div class="header-sub">${escapeHtml(this._getSubtitle())}</div>
          </div>
        </div>
        ${this._renderTabs()}
        <div class="dep-list">${this._renderDeps()}</div>
        ${c.show_footer ? `<div class="footer">${this._getLastUpdate()}</div>` : ""}
      </ha-card>`;
    this._rendered = true;
    this._bindTapActions();
  }

  _getLastUpdate() {
    if (!this._hass || !this._config.entities?.length) return "";
    let latest = null;
    for (const eid of this._config.entities) {
      const s = this._hass.states[eid];
      const lu = s?.attributes?.last_update;
      if (lu && (!latest || lu > latest)) latest = lu;
    }
    if (!latest) return "";
    const d = new Date(latest);
    const time = d.toLocaleTimeString("pl-PL", {hour:"2-digit", minute:"2-digit", second:"2-digit"});
    return `Odświeżono: ${time}`;
  }

  _renderTabs() {
    const c = this._config;
    if (c.view_mode !== "tabs" || !c.entities || c.entities.length <= 1) return "";
    const tabs = c.entities.map((eid, i) => {
      const s = this._hass?.states[eid];
      const name = s?.attributes?.stop_name || eid.replace("sensor.", "");
      return `<span class="tab${i === this._activeTab ? " active" : ""}" data-tab="${i}">${escapeHtml(name)}</span>`;
    });
    return `<div class="tabs">${tabs.join("")}</div>`;
  }

  _bindTabs() {
    this.shadowRoot?.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        this._activeTab = parseInt(tab.dataset.tab);
        this._updateContent();
        // Update active tab style
        this.shadowRoot.querySelectorAll(".tab").forEach((t, i) => t.classList.toggle("active", i === this._activeTab));
      });
    });
  }

  _bindTapActions() {
    this._bindTabs();
  }

  _updateContent() {
    const el = this.shadowRoot?.querySelector(".dep-list");
    if (el) {
      el.innerHTML = this._renderDeps();
      this._bindTapActions();
    }
    // Re-render tabs
    const tabsEl = this.shadowRoot?.querySelector(".tabs");
    const newTabs = this._renderTabs();
    if (tabsEl && !newTabs) tabsEl.remove();
    else if (!tabsEl && newTabs) {
      const depList = this.shadowRoot?.querySelector(".dep-list");
      if (depList) depList.insertAdjacentHTML("beforebegin", newTabs);
      this._bindTabs();
    }
    // Update header color dynamically
    const header = this.shadowRoot?.querySelector(".header");
    if (header) header.style.background = this._getHeaderColor();
    const title = this.shadowRoot?.querySelector(".header-title");
    if (title) title.textContent = this._getTitle();
    const sub = this.shadowRoot?.querySelector(".header-sub");
    if (sub) sub.textContent = this._getSubtitle();
    const footer = this.shadowRoot?.querySelector(".footer");
    if (footer) footer.textContent = this._getLastUpdate();
  }

  _renderDeps() {
    const c = this._config;
    if (!c.entities?.length) return `<div class="state-msg"><span class="icon">📍</span>${t("no_entities")}</div>`;

    if (!this._hass) {
      return Array.from({ length: c.max_departures }, (_, i) =>
        `<div class="dep-row"><div class="skel" style="height:26px;width:40px;border-radius:6px"></div><div class="skel" style="height:13px;flex:1"></div><div class="skel" style="height:13px;width:60px"></div></div>`
      ).join("");
    }

    const deps = this._getDepartures();
    if (!deps.length) {
      // Check if any entity is unavailable (e.g. rate limit)
      const unavailable = c.entities.filter(eid => {
        const s = this._hass.states[eid];
        return s && (s.state === "unavailable" || s.state === "unknown");
      });
      if (unavailable.length) {
        const hasPlk = unavailable.some(eid => this._hass.states[eid]?.attributes?.provider === "plk_rail");
        const msg = hasPlk ? t("plk_rate_limit") : t("unavailable");
        return `<div class="state-msg"><span class="icon">⚠️</span>${msg}</div>`;
      }
      return `<div class="state-msg"><span class="icon">⏳</span>${t("no_departures")}</div>`;
    }

    return deps.map(d => {
      const mins = minutesUntil(d.estimated_time);
      const imminent = d.realtime && mins !== null && mins <= 2;
      const delayMin = Math.round((d.delay_seconds || 0) / 60);
      const showDelay = c.show_delays && d.realtime && Math.abs(delayMin) >= 1;
      const cancelled = d.cancelled === true;

      let timeHTML;
      if (cancelled) {
        timeHTML = `<div class="time-main cancelled">${t("cancelled")}</div>`;
      } else if (c.display_preset === "e_ink") {
        // E-ink: only static departure time, no countdown
        timeHTML = `<div class="time-main">${formatTime(d.estimated_time || d.theoretical_time)}</div>`;
      } else if (d.realtime) {
        const delayPart = showDelay
          ? ` <span class="delay-badge ${delayMin > 0 ? "late" : "early"}">${delayMin > 0 ? "+" : ""}${delayMin}min</span>`
          : "";
        const mainTime = showDelay
          ? `<span class="time-struck">${formatTime(d.theoretical_time || d.estimated_time)}</span> ${formatTime(d.estimated_time)}`
          : formatTime(d.estimated_time);
        timeHTML = `<div class="time-main">${mainTime}</div><div class="time-sub"><span class="dot">●</span> ${formatMins(mins)}${delayPart}</div>`;
      } else {
        timeHTML = `<div class="time-main">${formatTime(d.theoretical_time || d.estimated_time)}</div>`;
      }

      // Platform
      const platformHTML = (() => {
        if (d._provider === "plk_rail") {
          let chips = "";
          if (d.platform) chips += `<span class="platform">peron ${escapeHtml(d.platform)}</span>`;
          if (d.track) chips += `<span class="platform">${t("track")} ${escapeHtml(d.track)}</span>`;
          return chips;
        }
        return d.platform ? `<span class="platform">${t("track")} ${escapeHtml(d.platform)}</span>` : "";
      })();

      // Vehicle info + feature icons
      let iconsHTML = "";
      const icons = [];
      if (c.show_bike && d.bike_allowed === true) icons.push(`<span title="Rower">${ICON_BIKE}</span>`);
      if (c.show_wheelchair && d.wheelchair_accessible === true) icons.push(`<span title="Wózek">${ICON_WHEELCHAIR}</span>`);
      if (c.show_ac && d.air_conditioning === true) icons.push(`<span title="Klimatyzacja">${ICON_AC}</span>`);
      if (d.usb === true) icons.push(`<span title="USB"><svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M15,7V11H16V13H13V5H15L12,1L9,5H11V13H8V10.93C8.7,10.56 9.2,9.85 9.2,9C9.2,7.9 8.3,7 7.2,7C6.1,7 5.2,7.9 5.2,9C5.2,9.85 5.7,10.56 6.4,10.93V13C6.4,14.1 7.3,15 8.4,15H11V18.05C10.3,18.42 9.8,19.15 9.8,20C9.8,21.1 10.7,22 11.8,22C12.9,22 13.8,21.1 13.8,20C13.8,19.15 13.3,18.42 12.6,18.05V15H15.6C16.7,15 17.6,14.1 17.6,13V11H18.6V7H15Z"/></svg></span>`);
      if (d.ticket_machine === true && c.show_ticket_machine) icons.push(`<span title="Biletomat"><svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M15.58,16.8L12,14.5L8.42,16.8L9.5,12.68L6.21,10L10.46,9.74L12,5.84L13.54,9.74L17.79,10L14.5,12.68M20,2H4A2,2 0 0,0 2,4V22L7,20L12,22L17,20L22,22V4A2,2 0 0,0 20,2Z"/></svg></span>`);
      if (icons.length) iconsHTML = `<span class="icons">${icons.join("")}</span>`;
      const vehicleChip = (d.vehicle_code && d.realtime) ? `<span class="platform">${escapeHtml(d.vehicle_code)}</span>` : "";

      // Auto show_stop_name when multiple entities
      const showStop = c.show_stop_name && c.entities.length > 1 && c.view_mode !== "tabs" && d._stopName;
      const cleanStopName = (d._stopName || "").replace(/\s*\(?(bus|tramwaj|tram|train|skm)\)?\s*/gi, " ").trim();
      // Train details for PLK
      let trainInfo = "";
      if (d.train_number && d._provider === "plk_rail") {
        const shortCarrier = (d.carrier || "").replace(/^[„""'\s]+/, "").replace(/PKP\s*Szybka\s*Kolej\s*Miejska.*/i, "SKM").replace(/PKP\s*Intercity.*/i, "IC").replace(/POLREGIO.*/i, "Polregio").replace(/\s*sp\.?\s*z\s*o\.?\s*o\.?.*/i, "");
        trainInfo = `<span class="stop-name">nr ${escapeHtml(d.train_number)} - ${escapeHtml(shortCarrier)}</span>`;
      }

      return `<div class="dep-row${imminent ? " imminent" : ""}${d._dimmed ? " dimmed" : ""}${cancelled ? " cancelled" : ""}">
        <span class="badge" style="background:${routeColor(d.route, d._provider || d.provider)}">${escapeHtml(d.route)}</span>
        <span class="headsign"><span class="headsign-text">${escapeHtml(d.headsign)}</span>${iconsHTML}${platformHTML}${vehicleChip}${trainInfo || (showStop ? `<span class="stop-name">${escapeHtml(cleanStopName)}</span>` : "")}</span>
        <div class="time-col">${timeHTML}</div>
      </div>`;
    }).join("");
  }
}

if (!customElements.get("mzkzg-transport-card")) {
  customElements.define("mzkzg-transport-card", MzkzgTransportCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "mzkzg-transport-card",
  name: "MZKZG Transport Card",
  description: "Tablica odjazdów ZTM Gdańsk + ZKM Gdynia (dane z integracji mzkzg_transport)",
  preview: true,
  documentationURL: "https://github.com/toczke/mzkzg-transport-card",
});

console.info(
  `%c MZKZG-TRANSPORT %c v${MZKZG_VERSION} `,
  "background:#005eb8;color:#fff;padding:2px 6px;border-radius:4px 0 0 4px;font-weight:bold",
  "background:#1f2937;color:#fff;padding:2px 6px;border-radius:0 4px 4px 0"
);
