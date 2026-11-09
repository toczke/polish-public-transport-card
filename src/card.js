import { LitElement, html, svg, nothing } from 'lit';
import { unsafeHTML } from 'lit/directives/unsafe-html.js';
import { t, minutesUntil, formatTime, formatMins, routeColor, parseVehiclePosition, normalizeList, normalizeEntityEntry, normalizeActionConfig, fireHassEvent, providerLabel, PROVIDER_HEADER_COLORS } from "./utils.js";
import { styles } from "./styles.js";
import { VehicleMap } from "./map.js";

const BUS_ICON_SVG = svg`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 16.01L16.01 15.99"/><path d="M6 16.01L6.01 15.99"/><path d="M20 22V15V8M20 8H18V2H22V8H20Z"/><path d="M4 20V22H6V20H4Z" fill="currentColor"/><path d="M14 20V22H16V20H14Z" fill="currentColor"/><path d="M16 20H2.6A.6.6 0 012 19.4V12.6c0-.33.27-.6.6-.6H16"/><path d="M14 8H6M14 2H6C3.79 2 2 3.79 2 6V8"/></svg>`;
const TRAIN_ICON_SVG = svg`<svg viewBox="0 0 24 24" width="20" height="20" style="color:#fff"><path fill="currentColor" d="M12,2C8,2 4,2.5 4,6V15.5A3.5,3.5 0 0,0 7.5,19L6,20.5V21H18V20.5L16.5,19A3.5,3.5 0 0,0 20,15.5V6C20,2.5 16,2 12,2M7.5,17A1.5,1.5 0 0,1 6,15.5A1.5,1.5 0 0,1 7.5,14A1.5,1.5 0 0,1 9,15.5A1.5,1.5 0 0,1 7.5,17M11,10H6V7H11V10M13,10V7H18V10H13M16.5,17A1.5,1.5 0 0,1 15,15.5A1.5,1.5 0 0,1 16.5,14A1.5,1.5 0 0,1 18,15.5A1.5,1.5 0 0,1 16.5,17Z"/></svg>`;
const BUS_STOP_ICON_SVG = svg`<svg viewBox="0 0 24 24" width="20" height="20" style="color:#fff"><path fill="currentColor" d="M14,14A2,2 0 0,1 12,16A2,2 0 0,1 10,14A2,2 0 0,1 12,12A2,2 0 0,1 14,14M12,19C10.74,19 9.38,18.42 8.44,17.44L10,15.93C10.55,16.29 11.23,16.5 12,16.5C12.77,16.5 13.45,16.29 14,15.93L15.56,17.44C14.62,18.42 13.26,19 12,19M20,6C20,4.89 19.11,4 18,4H6C4.89,4 4,4.89 4,6V18C4,19.11 4.89,20 6,20H18C19.11,20 20,19.11 20,18V6M12,10A4,4 0 0,0 8,14A4,4 0 0,0 12,18A4,4 0 0,0 16,14A4,4 0 0,0 12,10M17.5,7C17.22,7 17,6.78 17,6.5C17,6.22 17.22,6 17.5,6C17.78,6 18,6.22 18,6.5C18,6.78 17.78,7 17.5,7M15,7C14.72,7 14.5,6.78 14.5,6.5C14.5,6.22 14.72,6 15,6C15.28,6 15.5,6.22 15.5,6.5C15.5,6.78 15.28,7 15,7Z"/></svg>`;

const ICON_BIKE = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M5,20.5A3.5,3.5 0 0,1 1.5,17A3.5,3.5 0 0,1 5,13.5A3.5,3.5 0 0,1 8.5,17A3.5,3.5 0 0,1 5,20.5M5,12A5,5 0 0,0 0,17A5,5 0 0,0 5,22A5,5 0 0,0 10,17A5,5 0 0,0 5,12M14.8,10H19V8.2H15.8L13.86,4.93C13.57,4.43 13,4.1 12.4,4.1C11.93,4.1 11.5,4.29 11.2,4.6L7.5,8.29C7.19,8.6 7,9 7,9.5C7,10.13 7.33,10.66 7.85,10.97L11.2,13V18H13V11.5L10.75,9.85L13.07,7.5M19,20.5A3.5,3.5 0 0,1 15.5,17A3.5,3.5 0 0,1 19,13.5A3.5,3.5 0 0,1 22.5,17A3.5,3.5 0 0,1 19,20.5M19,12A5,5 0 0,0 14,17A5,5 0 0,0 19,22A5,5 0 0,0 24,17A5,5 0 0,0 19,12M16,4.8C17,4.8 17.8,4 17.8,3C17.8,2 17,1.2 16,1.2C15,1.2 14.2,2 14.2,3C14.2,4 15,4.8 16,4.8Z"/></svg>`;
const ICON_WHEELCHAIR = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M18.4,11.2L14.3,11.4L16.6,8.8C16.8,8.5 16.9,8 16.8,7.5C16.7,7.2 16.6,6.9 16.3,6.7L10.9,3.5C10.5,3.2 9.9,3.3 9.5,3.6L6.8,6.1C6.3,6.6 6.2,7.3 6.7,7.8C7.1,8.3 7.9,8.3 8.4,7.9L10.4,6.1L12.3,7.2L8.1,11.5C8,11.6 8,11.7 7.9,11.7C7.4,11.9 6.9,12.1 6.5,12.4L8,13.9C8.5,13.7 9,13.5 9.5,13.5C11.4,13.5 13,15.1 13,17C13,17.6 12.9,18.1 12.6,18.5L14.1,20C14.7,19.1 15,18.1 15,17C15,15.8 14.6,14.6 13.9,13.7L17.2,13.4L17,18.2C16.9,18.9 17.4,19.4 18.1,19.5H18.2C18.8,19.5 19.3,19 19.4,18.4L19.6,12.5C19.6,12.2 19.5,11.8 19.3,11.6C19,11.3 18.7,11.2 18.4,11.2M18,5.5A2,2 0 0,0 20,3.5A2,2 0 0,0 18,1.5A2,2 0 0,0 16,3.5A2,2 0 0,0 18,5.5M12.5,21.6C11.6,22.2 10.6,22.5 9.5,22.5C6.5,22.5 4,20 4,17C4,15.9 4.3,14.9 4.9,14L6.4,15.5C6.2,16 6,16.5 6,17C6,18.9 7.6,20.5 9.5,20.5C10.1,20.5 10.6,20.4 11,20.1L12.5,21.6Z"/></svg>`;
const ICON_AC = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M20.79,13.95L18.46,14.57L16.46,13.44V10.56L18.46,9.43L20.79,10.05L21.31,8.12L19.54,7.65L20,5.88L18.07,5.36L17.45,7.69L15.45,8.82L13,7.38V5.12L14.71,3.41L13.29,2L12,3.29L10.71,2L9.29,3.41L11,5.12V7.38L8.5,8.82L6.5,7.69L5.92,5.36L4,5.88L4.47,7.65L2.7,8.12L3.22,10.05L5.55,9.43L7.55,10.56V13.45L5.55,14.58L3.22,13.96L2.7,15.89L4.47,16.36L4,18.12L5.93,18.64L6.55,16.31L8.55,15.18L11,16.62V18.88L9.29,20.59L10.71,22L12,20.71L13.29,22L14.7,20.59L13,18.88V16.62L15.5,15.17L17.5,16.3L18.12,18.63L20,18.12L19.53,16.35L21.3,15.88L20.79,13.95M9.5,10.56L12,9.11L14.5,10.56V13.44L12,14.89L9.5,13.44V10.56Z"/></svg>`;
const ICON_TICKET = `<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M22,10V6A2,2 0 0,0 20,4H4A2,2 0 0,0 2,6V10A2,2 0 0,1 4,12A2,2 0 0,1 2,14V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V14A2,2 0 0,1 20,12A2,2 0 0,1 22,10M13,17H11V15H13V17M13,13H11V11H13V13M13,9H11V7H13V9Z"/></svg>`;

const stateIcon = (icon) => html`<ha-icon class="state-icon" icon=${icon}></ha-icon>`;

export class PolishTransportCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { state: true },
      _activeTab: { state: true }
    };
  }

  static styles = styles;

  constructor() {
    super();
    this.vehicleMap = new VehicleMap(this);
    this._config = {};
    this._activeTab = 0;
    this._tickTimer = null;
  }

  static getStubConfig() {
    return { type: "custom:polish-transport-card", entities: [], max_departures: 10, min_departures: 5, show_delays: true, hide_terminus: true, show_bike: true, show_wheelchair: true, show_footer: true };
  }

  static getConfigElement() {
    return document.createElement("polish-transport-card-editor");
  }

  setConfig(config) {
    if (!config) throw new Error("No configuration provided");
    if (config.entities && !Array.isArray(config.entities)) throw new Error("entities must be an array");
    const preset = ["standard", "compact", "e_ink", "minimal", "native"].includes(config.display_preset)
      ? config.display_preset : "standard";
    const themeMode = ["auto", "light", "dark"].includes(config.theme_mode) ? config.theme_mode : "auto";
    const headerStyle = ["provider", "theme", "custom"].includes(config.header_style)
      ? config.header_style : (config.header_color ? "custom" : "provider");
    this._config = {
      ...config,
      entities: (Array.isArray(config.entities) ? config.entities : []).map(normalizeEntityEntry).filter(Boolean),
      max_departures: Math.max(1, Math.min(100, parseInt(config.max_departures) || 10)),
      min_departures: Math.min(
        Math.max(1, Math.min(100, parseInt(config.max_departures) || 10)),
        Math.max(0, Math.min(100, parseInt(config.min_departures) || 0))
      ),
      refresh_interval: Math.max(5, Math.min(600, parseInt(config.refresh_interval) || 60)),
      display_preset: preset,
      view_mode: ["mixed", "tabs", "grouped"].includes(config.view_mode) ? config.view_mode : "mixed",
      theme_mode: themeMode,
      header_style: headerStyle,
      show_header: config.show_header !== false,
      show_clock: config.show_clock === true,
      show_delays: config.show_delays !== false,
      hide_terminus: config.hide_terminus !== false,
      hide_cancelled: config.hide_cancelled === true,
      realtime_only: config.realtime_only === true,
      highlight_mode: config.highlight_mode === true,
      show_countdown: config.show_countdown !== false,
      show_vehicle: config.show_vehicle !== false,
      show_platform: config.show_platform !== false,
      show_accessibility: config.show_accessibility !== false,
      show_alerts: config.show_alerts !== false,
      alerts_scope: ["matching", "city"].includes(config.alerts_scope) ? config.alerts_scope : "matching",
      show_bike: config.show_bike !== false,
      show_wheelchair: config.show_wheelchair !== false,
      show_ac: config.show_ac !== false,
      show_ticket_machine: config.show_ticket_machine !== false,
      show_stop_name: config.show_stop_name === true,
      show_last_update: config.show_last_update !== false,
      show_refresh: config.show_refresh === true,
      columns: Math.max(1, Math.min(3, parseInt(config.columns) || 1)),
      max_minutes: Math.max(0, Math.min(1440, parseInt(config.max_minutes) || 0)),
      hide_departed: config.hide_departed !== false,
      departed_grace_minutes: Math.max(
        0,
        Math.min(60, Number.isFinite(parseInt(config.departed_grace_minutes, 10))
          ? parseInt(config.departed_grace_minutes, 10)
          : 1)
      ),
      only_low_floor: config.only_low_floor === true,
      only_bike: config.only_bike === true,
      only_ac: config.only_ac === true,
      only_ticket_machine: config.only_ticket_machine === true,
      filter_routes: normalizeList(config.filter_routes),
      exclude_routes: normalizeList(config.exclude_routes),
      destination_filter: normalizeList(config.destination_filter),
      exclude_destinations: normalizeList(config.exclude_destinations),
      filter_vehicle_types: normalizeList(config.filter_vehicle_types).map(v => v.toLowerCase()),
      filter_providers: normalizeList(config.filter_providers),
      filter_platform: config.filter_platform || "",
      filter_track: config.filter_track || "",
      time_format: ["auto", "24h", "12h"].includes(config.time_format) ? config.time_format : "auto",
      icon: config.icon || "",
      show_footer: config.show_footer !== false,
      tap_action: normalizeActionConfig(config.tap_action, "more-info"),
      hold_action: normalizeActionConfig(config.hold_action, "none"),
      double_tap_action: normalizeActionConfig(config.double_tap_action, "none"),
    };
    this._depCache = null;
  }

  getCardSize() { return (this._config.max_departures || 10) + 1; }

  connectedCallback() {
    super.connectedCallback();
    this._startTick();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._tickTimer) {
      clearInterval(this._tickTimer);
      this._tickTimer = null;
    }
    this.vehicleMap.destroy();
  }

  _startTick() {
    if (this._tickTimer) clearInterval(this._tickTimer);
    this._tickTimer = setInterval(() => {
      this.requestUpdate();
    }, 10000);
  }

  _getEntityIds() {
    if (!this.hass || !this._config.entities?.length) return [];
    return this._config.entities.map(e => typeof e === "string" ? e : e.entity).filter(e => this.hass.states[e]);
  }

  _getAllDepartures() {
    if (!this.hass || !this._config.entities?.length) return [];
    const all = [];
    for (const eid of this._getEntityIds()) {
      const s = this.hass.states[eid];
      if (s?.attributes?.departures) {
        const entry = this._config.entities.find(e => (typeof e === "string" ? e : e.entity) === eid);
        for (const d of s.attributes.departures) {
          all.push({ ...d, _entityId: eid, _entityConfig: entry, _stopName: s.attributes.stop_name, _provider: s.attributes.provider });
        }
      }
    }
    return all.sort((a, b) => new Date(a.estimated_time || a.theoretical_time) - new Date(b.estimated_time || b.theoretical_time));
  }

  _departuresCacheKey() {
    const ids = this._getEntityIds();
    const states = ids.map(eid => {
      const s = this.hass.states[eid];
      return `${eid}:${s?.state || ""}:${s?.last_updated || ""}`;
    }).join("|");
    const bucket = Math.floor(Date.now() / 15000);
    return `${states}|tab:${this._activeTab}|t:${bucket}`;
  }

  _getDepartures() {
    if (!this.hass || !this._config.entities?.length) return [];
    const cacheKey = this._departuresCacheKey();
    if (this._depCache?.key === cacheKey) return this._depCache.value;
    const c = this._config;
    let all = [];
    const entities = this._getEntityIds();

    if (c.view_mode === "tabs" && entities.length > 1) {
      const eid = entities[this._activeTab];
      const s = eid ? this.hass.states[eid] : null;
      if (s?.attributes?.departures) {
        const entry = this._config.entities.find(e => (typeof e === "string" ? e : e.entity) === eid);
        all = s.attributes.departures.map(d => ({ ...d, _entityId: eid, _entityConfig: entry, _stopName: s.attributes.stop_name, _provider: s.attributes.provider }));
      }
    } else {
      all = this._getAllDepartures();
    }

    // Resolve a value from the per-sensor override first, then the card default.
    const cfg = (d, key, fallback) => {
      const ec = d._entityConfig && typeof d._entityConfig === "object" ? d._entityConfig : {};
      return key in ec ? ec[key] : fallback;
    };
    const includesText = (value, filters) =>
      Array.isArray(filters) && filters.length > 0 &&
      filters.some(f => String(value || "").toLowerCase().includes(String(f).toLowerCase()));

    all = all.filter(d => {
      if (cfg(d, "realtime_only", c.realtime_only) && !d.realtime) return false;

      const routes = cfg(d, "filter_routes", c.filter_routes);
      if (Array.isArray(routes) && routes.length &&
          !routes.some(r => String(r).toUpperCase() === String(d.route || "").toUpperCase())) return false;
      const excludedRoutes = cfg(d, "exclude_routes", c.exclude_routes);
      if (Array.isArray(excludedRoutes) && excludedRoutes.length &&
          excludedRoutes.some(r => String(r).toUpperCase() === String(d.route || "").toUpperCase())) return false;

      const destinations = cfg(d, "destination_filter", c.destination_filter);
      if (Array.isArray(destinations) && destinations.length && !includesText(d.headsign, destinations)) return false;
      if (includesText(d.headsign, cfg(d, "exclude_destinations", c.exclude_destinations))) return false;

      const vehicleTypes = cfg(d, "filter_vehicle_types", c.filter_vehicle_types);
      if (Array.isArray(vehicleTypes) && vehicleTypes.length &&
          !vehicleTypes.some(v => String(v).toLowerCase() === String(d.vehicle_type || "").toLowerCase())) return false;

      const providers = cfg(d, "filter_providers", c.filter_providers);
      if (Array.isArray(providers) && providers.length &&
          !providers.includes(d._provider || d.provider || "")) return false;

      const platform = cfg(d, "filter_platform", c.filter_platform);
      if (platform && String(d.platform || "") !== String(platform)) return false;
      const track = cfg(d, "filter_track", c.filter_track);
      if (track && String(d.track || "") !== String(track)) return false;

      if (cfg(d, "hide_terminus", c.hide_terminus) && d.headsign && d._stopName &&
          d.headsign.toLowerCase() === d._stopName.toLowerCase()) return false;
      if (cfg(d, "hide_cancelled", c.hide_cancelled) && d.cancelled) return false;

      const maxMinutes = parseInt(cfg(d, "max_minutes", c.max_minutes), 10) || 0;
      if (maxMinutes > 0) {
        const mins = minutesUntil(d.estimated_time || d.theoretical_time);
        if (mins === null || mins > maxMinutes) return false;
      }
      if (cfg(d, "only_low_floor", c.only_low_floor) &&
          !(d.wheelchair_accessible === true || (d.floor_height && d.floor_height !== "Pojazd wysokopodłogowy"))) return false;
      if (cfg(d, "only_bike", c.only_bike) && d.bike_allowed !== true) return false;
      if (cfg(d, "only_ac", c.only_ac) && d.air_conditioning !== true) return false;
      if (cfg(d, "only_ticket_machine", c.only_ticket_machine) && d.ticket_machine !== true) return false;

      if (cfg(d, "hide_departed", c.hide_departed)) {
        const mins = minutesUntil(d.estimated_time || d.theoretical_time);
        const grace = parseInt(cfg(d, "departed_grace_minutes", c.departed_grace_minutes), 10);
        if (mins !== null && mins < -(Number.isFinite(grace) ? grace : 1)) return false;
      }

      return true;
    });

    all = this._dedupeDepartures(all);

    if (c.highlight_mode) {
      const byRoute = {};
      for (const d of all) {
        const key = d.route + "|" + d.headsign;
        if (!byRoute[key]) byRoute[key] = [];
        byRoute[key].push(d);
      }
      for (const k in byRoute) {
        byRoute[k].sort((a,b) => new Date(a.estimated_time || a.theoretical_time) - new Date(b.estimated_time || b.theoretical_time));
        byRoute[k].forEach((d, i) => { if (i > 0) d._dimmed = true; });
      }
    }

    // Per-sensor row caps, applied after all filters so a route filter does not
    // consume the cap with rows that are hidden anyway.
    const perEntityCounts = {};
    all = all.filter(d => {
      const cap = parseInt(cfg(d, "max_departures", c.max_departures)) || c.max_departures;
      perEntityCounts[d._entityId] = (perEntityCounts[d._entityId] || 0) + 1;
      return perEntityCounts[d._entityId] <= cap;
    });

    const result = all.slice(0, c.max_departures);
    this._depCache = { key: cacheKey, value: result };
    return result;
  }

  _getAlerts() {
    if (!this.hass || !this._config.entities?.length) return [];
    const alerts = [];
    const seen = new Set();
    const city = this._config.alerts_scope === "city";
    for (const entityId of this._getEntityIds()) {
      const attributes = this.hass.states[entityId]?.attributes || {};
      let list = city ? attributes.alerts_city : attributes.alerts;
      if (city && !Array.isArray(list)) list = attributes.alerts;
      if (!Array.isArray(list)) continue;
      for (const alert of list) {
        const alertId = alert?.id || `${alert?.title || ""}|${alert?.content || ""}`;
        if (seen.has(alertId)) continue;
        seen.add(alertId);
        alerts.push(alert);
      }
    }
    return alerts;
  }

  _renderAlerts() {
    if (!this._config.show_alerts) return nothing;
    const alerts = this._getAlerts();
    if (!alerts.length) return nothing;
    return html`
      <div class="alerts" role="status">
        ${alerts.map((alert) => html`
          <div class="alert-item">
            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
            <div class="alert-content">
              <div class="alert-title">
                ${alert.lines?.length ? html`<span class="alert-lines">${alert.lines.join(", ")}</span> ` : nothing}
                ${alert.title || t("alert")}
              </div>
              ${alert.content ? html`<div class="alert-text">${alert.content}</div>` : nothing}
            </div>
          </div>
        `)}
      </div>
    `;
  }

  _headsignsCompatible(first, second) {
    const a = String(first || "").trim().toLowerCase();
    const b = String(second || "").trim().toLowerCase();
    if (!a || !b || a === b) return true;
    return a.startsWith(b) || b.startsWith(a);
  }

  _mergeDeparture(base, extra) {
    let primary = base;
    let secondary = extra;
    if (extra.realtime && !base.realtime) {
      primary = extra;
      secondary = base;
    }
    const merged = { ...primary };
    for (const [key, value] of Object.entries(secondary)) {
      if (key === "headsign") continue;
      const current = merged[key];
      if ((current === undefined || current === null || current === "") &&
          value !== undefined && value !== null && value !== "") {
        merged[key] = value;
      }
    }
    if (String(extra.headsign || "").length > String(primary.headsign || "").length) {
      merged.headsign = extra.headsign;
    }
    return merged;
  }

  _dedupeDepartures(departures) {
    const groups = [];
    for (const d of departures) {
      const time = String(d.theoretical_time || d.estimated_time || "").slice(0, 16);
      const key = `${d._entityId || ""}|${d.route}|${time}`;
      const group = groups.find(g =>
        g.key === key && this._headsignsCompatible(g.base.headsign, d.headsign)
      );
      if (group) {
        group.base = this._mergeDeparture(group.base, d);
      } else {
        groups.push({ key, base: d });
      }
    }
    return groups.map(g => g.base);
  }

  _getAutoIcon() {
    if (!this.hass || !this._config.entities?.length) return BUS_ICON_SVG;
    const providers = new Set();
    for (const eid of this._getEntityIds()) {
      const s = this.hass.states[eid];
      if (s?.attributes?.provider) providers.add(s.attributes.provider);
    }
    if (providers.size === 1 && providers.has("plk_rail")) return TRAIN_ICON_SVG;
    return BUS_STOP_ICON_SVG;
  }

  _getHeaderColor() {
    if (this._config.header_style === "theme") return "var(--primary-color, #005eb8)";
    if (this._config.header_style === "custom" && this._config.header_color) {
      const c = this._config.header_color;
      if (/^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|linear-gradient\([^;{}]+\)|[a-zA-Z]{3,20})$/.test(c.trim())) {
        return c.trim();
      }
      return "var(--primary-color, #005eb8)";
    }
    if (this._config.header_color) {
      const c = this._config.header_color;
      if (/^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|linear-gradient\([^;{}]+\)|[a-zA-Z]{3,20})$/.test(c.trim())) {
        return c.trim();
      }
      return "#005eb8";
    }
    const colors = {
      ztm_gdansk: "#DA2128",
      zkm_gdynia: "#005eb8",
      mzk_wejherowo: "#478AC9",
      plk_rail: "#1a1a2e",
      ...PROVIDER_HEADER_COLORS,
    };
    const providers = new Set();
    if (this.hass && this._config.entities?.length) {
      for (const eid of this._getEntityIds()) {
        const s = this.hass.states[eid];
        if (s?.attributes?.provider) providers.add(s.attributes.provider);
      }
    }
    const list = [...providers];
    if (list.length === 1) return colors[list[0]] || "#005eb8";
    if (list.length >= 2) {
      const cols = [...new Set(list.map(p => colors[p] || "#005eb8"))];
      if (cols.length === 1) return cols[0];
      return `linear-gradient(135deg, ${cols[0]} 0%, ${cols[1]} 100%)`;
    }
    return "#005eb8";
  }

  _getTitle() {
    if (this._config.title) return this._config.title;
    if (!this.hass || !this._config.entities?.length) return "Polish Transport";
    const firstId = this._getEntityIds()[0];
    const first = firstId ? this.hass.states[firstId] : null;
    return first?.attributes?.stop_name || first?.attributes?.friendly_name || "Polish Transport";
  }

  _getSubtitle() {
    if (!this.hass || !this._config.entities?.length) return t("select_entities");
    const providers = new Set();
    for (const eid of this._getEntityIds()) {
      const s = this.hass.states[eid];
      if (s?.attributes?.provider) {
        providers.add(s.attributes.provider);
      }
    }
    return [...providers].map(providerLabel).join(" • ") || "Polish Transport";
  }

  _getClock() {
    const locale = this.hass?.locale?.language || document.documentElement.lang || "pl-PL";
    const configured = this._config.time_format;
    const hour12 = configured === "12h" || (configured === "auto" && this.hass?.locale?.time_format === "12");
    return new Intl.DateTimeFormat(locale, {
      hour: "2-digit",
      minute: "2-digit",
      hour12,
    }).format(new Date());
  }

  _getLastUpdate() {
    if (!this.hass || !this._config.entities?.length) return "";
    let latest = null;
    for (const eid of this._getEntityIds()) {
      const s = this.hass.states[eid];
      const lu = s?.attributes?.last_update;
      if (lu && (!latest || lu > latest)) latest = lu;
    }
    if (!latest) return "";
    const d = new Date(latest);
    const locale = this.hass?.locale?.language || document.documentElement.lang || "pl-PL";
    return `${t("last_update")}: ${d.toLocaleTimeString(locale, {hour:"2-digit", minute:"2-digit", second:"2-digit"})}`;
  }

  async _refresh(ev) {
    ev?.stopPropagation?.();
    if (!this.hass) return;
    const ids = this._getEntityIds();
    if (!ids.length) return;
    this._refreshing = true;
    this.requestUpdate();
    try {
      await this.hass.callService("homeassistant", "update_entity", { entity_id: ids });
    } finally {
      setTimeout(() => { this._refreshing = false; this.requestUpdate(); }, 1200);
    }
  }

  _resolveActionConfig(kind) {
    const c = this._config || {};
    if (kind === "tap") return normalizeActionConfig(c.tap_action, "more-info");
    if (kind === "hold") return normalizeActionConfig(c.hold_action, "none");
    return normalizeActionConfig(c.double_tap_action, "none");
  }

  async _handleRowAction(kind, d) {
    const actionCfg = this._resolveActionConfig(kind);
    const action = actionCfg.action || "none";
    if (action === "none") return;

    const entityId = d._entityId || this._config.entities[0];

    if (action === "more-info") {
      fireHassEvent(this, "hass-more-info", { entityId });
      return;
    }
    if (action === "navigate") {
      const path = actionCfg.navigation_path || "";
      if (!path) return;
      history.pushState(null, "", path);
      fireHassEvent(window, "location-changed", { replace: false });
      return;
    }
    if (action === "url") {
      const url = actionCfg.url_path || "";
      if (!url) return;
      window.open(url, "_blank", "noopener");
      return;
    }
    if (action === "toggle") {
      if (!this.hass || !entityId) return;
      await this.hass.callService("homeassistant", "toggle", { entity_id: entityId });
      return;
    }
    if (action === "perform-action" || action === "call-service") {
      if (!this.hass) return;
      const ref = actionCfg.perform_action || actionCfg.service || "";
      const [domain, service] = ref.split(".");
      if (!domain || !service) return;
      const data = { ...(actionCfg.data || {}) };
      if (actionCfg.target?.entity_id) data.entity_id = actionCfg.target.entity_id;
      await this.hass.callService(domain, service, data);
    }
  }

  _onRowClick(e, d) {
    const hasPos = parseVehiclePosition(d.vehicle_lat, d.vehicle_lng) !== null;
    if (hasPos) {
      const pos = parseVehiclePosition(d.vehicle_lat, d.vehicle_lng);
      this.vehicleMap.showVehicleMap(pos[0], pos[1], {
        route: d.route || "",
        code: d.vehicle_code || "",
        headsign: d.headsign || "",
        delay: Math.round((d.delay_seconds || 0) / 60),
        direction: parseFloat(d.vehicle_direction || d.direction) || null,
        provider: d._provider || d.provider || "",
        trip_id: d.trip_id,
        route_id_int: d.route_id_int,
        entityId: d._entityId,
        vehicleType: d.vehicle_type || "bus",
        lowFloor: d.floor_height && d.floor_height !== "Pojazd wysokopodłogowy",
        electric: d.drive_type === "elektryczny",
        articulated: d.articulated,
        historic: d.historic,
        vehicle_model: d.vehicle_model || "",
        vehicle_speed: d.vehicle_speed,
      });
      return;
    }

    const tapAction = this._resolveActionConfig("tap").action || "none";
    // Rows without a live vehicle position should behave like plain timetable
    // text; never open the entity more-info dialog for them.
    if (tapAction === "more-info") return;

    if (this._tapTimer) clearTimeout(this._tapTimer);
    this._tapTimer = setTimeout(() => this._handleRowAction("tap", d), 220);
  }

  _onRowDblClick(e, d) {
    if (this._tapTimer) clearTimeout(this._tapTimer);
    this._handleRowAction("double", d);
  }

  _onRowContext(e, d) {
    e.preventDefault();
    this._handleRowAction("hold", d);
  }

  _renderTabs() {
    const c = this._config;
    const entities = this._getEntityIds();
    if (c.view_mode !== "tabs" || entities.length <= 1) return nothing;
    return html`
      <div class="tabs" role="tablist">
        ${entities.map((eid, i) => {
          const s = this.hass?.states[eid];
          const name = s?.attributes?.stop_name || eid.replace("sensor.", "");
          return html`
            <span 
              class="tab ${i === this._activeTab ? 'active' : ''}" 
              role="tab" 
              tabindex=${i === this._activeTab ? "0" : "-1"}
              aria-selected=${i === this._activeTab ? "true" : "false"}
              @click=${() => { this._activeTab = i; }}
            >${name}</span>
          `;
        })}
      </div>
    `;
  }

  _renderDeps() {
    const c = this._config;
    if (!c.entities?.length) return html`<div class="state-msg">${stateIcon("mdi:map-marker-off")}${t("no_entities")}</div>`;

    if (!this.hass) {
      const skeletonCount = typeof c.min_departures !== 'undefined' && c.min_departures > 0 ? c.min_departures : Math.min(5, c.max_departures || 5);
      return Array.from({ length: skeletonCount }).map(() => html`
        <div class="dep-row">
          <div class="skel" style="height:26px;width:40px;border-radius:6px"></div>
          <div class="skel" style="height:13px;flex:1"></div>
          <div class="skel" style="height:13px;width:60px"></div>
        </div>
      `);
    }

    const deps = this._getDepartures();
    if (!deps.length) {
      const missing = this._getEntityIds().filter(eid => !this.hass.states[eid]);
      if (missing.length) {
        const names = missing.map(e => e.replace("sensor.", "")).join(", ");
        return html`<div class="state-msg">${stateIcon("mdi:alert-circle-outline")}${t("missing_entities")}<br><small>${names}</small></div>`;
      }
      const unavailable = this._getEntityIds().filter(eid => {
        const s = this.hass.states[eid];
        return s && (s.state === "unavailable" || s.state === "unknown");
      });
      if (unavailable.length) {
        const hasPlk = unavailable.some(eid => this.hass.states[eid]?.attributes?.provider === "plk_rail");
        const msg = hasPlk ? t("plk_rate_limit") : t("unavailable");
        return html`<div class="state-msg">${stateIcon(hasPlk ? "mdi:cloud-alert-outline" : "mdi:alert-outline")}${msg}</div>`;
      }
      const allDeps = this._getAllDepartures();
      if (allDeps.length) {
        const next = allDeps[0];
        const nextTime = next.estimated_time ? formatTime(next.estimated_time) : "";
        return html`<div class="state-msg">${stateIcon("mdi:clock-outline")}${t("no_departures")}<br><small>${nextTime ? `${t("next")}: ${next.route} → ${next.headsign} ${nextTime}` : ""}</small></div>`;
      }
      return html`<div class="state-msg">${stateIcon("mdi:timer-sand-empty")}${t("no_departures")}</div>`;
    }
    const tapAction = this._resolveActionConfig("tap").action || "none";
    const holdAction = this._resolveActionConfig("hold").action || "none";
    const doubleTapAction = this._resolveActionConfig("double").action || "none";
    const hasExplicitActions =
      (tapAction !== "none" && tapAction !== "more-info") ||
      holdAction !== "none" ||
      doubleTapAction !== "none";

    const renderRow = (d) => {
      const mins = minutesUntil(d.estimated_time);
      const imminent = d.realtime && mins !== null && mins <= 2;
      const delayMin = Math.round((d.delay_seconds || 0) / 60);
      const showDelay = c.show_delays && d.realtime && Math.abs(delayMin) >= 1;
      const cancelled = d.cancelled === true;

      let timeHTML;
      if (cancelled) {
        timeHTML = html`<div class="time-main cancelled">${t("cancelled")}</div>`;
      } else if (c.display_preset === "e_ink") {
        timeHTML = html`<div class="time-main">${formatTime(d.estimated_time || d.theoretical_time)}</div>`;
      } else if (d.realtime) {
        const delayPart = showDelay
          ? html` <span class="delay-badge ${delayMin > 0 ? 'late' : 'early'}">${delayMin > 0 ? "+" : ""}${delayMin}min</span>`
          : nothing;
        const mainTime = showDelay && formatTime(d.theoretical_time || d.estimated_time) !== formatTime(d.estimated_time)
          ? html`<span class="time-struck">${formatTime(d.theoretical_time || d.estimated_time)}</span> ${formatTime(d.estimated_time)}`
          : formatTime(d.estimated_time);
        const countdown = mins === null
          ? ""
          : mins <= 0
            ? t("departing")
            : `${t("in")} ${formatMins(mins)}`;
        timeHTML = c.show_countdown
          ? html`<div class="time-main">${mainTime}</div><div class="time-sub"><span class="dot">●</span> ${countdown}${delayPart}</div>`
          : html`<div class="time-main">${mainTime}${delayPart}</div>`;
      } else {
        timeHTML = html`<div class="time-main">${formatTime(d.theoretical_time || d.estimated_time)}</div>`;
      }

      const platformParts = [];
      if (c.show_platform && d._provider === "plk_rail") {
        if (d.platform) platformParts.push(`${t("platform")} ${d.platform}`);
        if (d.track) platformParts.push(`${t("track")} ${d.track}`);
      }
      const trainParts = [];
      if (d.train_number && d._provider === "plk_rail") {
        const shortCarrier = (d.carrier || "").replace(/^[„""'\s]+/, "").replace(/PKP\s*Szybka\s*Kolej\s*Miejska.*/i, "SKM").replace(/PKP\s*Intercity.*/i, "IC").replace(/POLREGIO.*/i, "Polregio").replace(/\s*sp\.?\s*z\s*o\.?\s*o\.?.*/i, "");
        trainParts.push(`${t("train_no")} ${d.train_number}`);
        if (shortCarrier) trainParts.push(shortCarrier);
      }

      const iconsHTML = [];
      if (c.show_accessibility) {
        if (c.show_bike && d.bike_allowed === true) iconsHTML.push(html`<span title=${t("bike")}>${unsafeHTML(ICON_BIKE)}</span>`);
        if (c.show_wheelchair && d.wheelchair_accessible === true) iconsHTML.push(html`<span title=${t("wheelchair")}>${unsafeHTML(ICON_WHEELCHAIR)}</span>`);
        if (c.show_ac && d.air_conditioning === true) iconsHTML.push(html`<span title=${t("ac")}>${unsafeHTML(ICON_AC)}</span>`);
        if (c.show_ticket_machine && d.ticket_machine === true) iconsHTML.push(html`<span title=${t("ticket_machine")}>${unsafeHTML(ICON_TICKET)}</span>`);
      }

      const vehicleChip = (c.show_vehicle && d._provider !== "plk_rail" && d.vehicle_code && d.realtime)
        ? html`<span class="vehicle-no" title=${t("show_vehicle")}>#${d.vehicle_code}</span>`
        : nothing;
      const platformText = (c.show_platform && d.platform && d._provider !== "plk_rail")
        ? html`<span class="platform" title=${t("platform")}>${d.platform}</span>`
        : nothing;
      const hasPos = parseVehiclePosition(d.vehicle_lat, d.vehicle_lng) !== null;

      const metaChips = [];
      if (platformParts.length) metaChips.push(html`<span class="meta-pill">${platformParts.join(" · ")}</span>`);
      if (platformText !== nothing) metaChips.push(platformText);
      const trainInfo = trainParts.length
        ? html`<span class="train-info">${trainParts.join(" · ")}</span>`
        : nothing;
      const metaRow = (iconsHTML.length > 0 || metaChips.length > 0 || trainInfo !== nothing)
        ? html`<span class="meta-row">
            ${iconsHTML.length ? html`<span class="icons">${iconsHTML}</span>` : nothing}
            ${metaChips.length || trainInfo !== nothing
              ? html`<span class="meta-chips">${metaChips}${trainInfo}</span>`
              : nothing}
          </span>`
        : nothing;

      const showStop = c.show_stop_name && c.entities.length > 1 && c.view_mode !== "tabs" && d._stopName;
      const cleanStopName = (d._stopName || "").replace(/\s*\(?(bus|tramwaj|tram|train|skm)\)?\s*/gi, " ").trim();

      const isInteractive = hasPos || hasExplicitActions;
      const rowTime = formatTime(d.estimated_time || d.theoretical_time);
      const rowLabel = `${d.route} → ${d.headsign || ""}${rowTime ? `, ${rowTime}` : ""}${hasPos ? `, ${t("show_on_map")}` : ""}`;

      return html`
        <div class="dep-row ${isInteractive ? 'interactive' : ''} ${imminent ? 'imminent' : ''} ${d._dimmed ? 'dimmed' : ''} ${cancelled ? 'cancelled' : ''}"
             tabindex=${isInteractive ? "0" : "-1"}
             role=${isInteractive ? "button" : nothing}
             aria-label=${isInteractive ? rowLabel : nothing}
             @click=${(e) => this._onRowClick(e, d)}
             @dblclick=${(e) => this._onRowDblClick(e, d)}
             @contextmenu=${(e) => this._onRowContext(e, d)}
             @keydown=${(e) => { if(e.key==="Enter" || e.key===" ") { e.preventDefault(); this._onRowClick(e, d); }}}>
          <span class="badge" style="background:${routeColor(d.route, d._provider || d.provider, d.route_color)}">${d.route}</span>
          <span class="headsign">
            <span class="head-main"><span class="headsign-text" title=${d.headsign}>${d.headsign}</span>${vehicleChip}</span>
            ${metaRow}
            ${showStop ? html`<span class="stop-name" title=${cleanStopName}>${cleanStopName}</span>` : nothing}
          </span>
          <div class="time-col">${timeHTML}</div>
        </div>
      `;
    };

    const rows = [];
    if (c.group_by_provider) {
      const grouped = {};
      deps.forEach(d => {
        const p = d._provider || "Inne";
        if (!grouped[p]) grouped[p] = [];
        grouped[p].push(d);
      });
      for (const p in grouped) {
        let pName;
        if (p === "plk_rail") pName = t("trains");
        else if (p === "Inne") pName = t("other");
        else pName = providerLabel(p);
        
        rows.push(html`<div class="provider-header">${pName}</div>`);
        grouped[p].forEach(d => rows.push(renderRow(d)));
      }
    } else if (c.view_mode === "grouped") {
      const groups = new Map();
      for (const d of deps) {
        const key = `${d.route}|${d.headsign || ""}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(d);
      }
      for (const [, group] of groups) {
        const first = group[0];
        rows.push(html`<div class="provider-header line-header">${first.route} → ${first.headsign || "—"}</div>`);
        group.forEach(d => rows.push(renderRow(d)));
      }
    } else {
      deps.forEach(d => rows.push(renderRow(d)));
    }

    const minDep = typeof this._config.min_departures !== "undefined" ? parseInt(this._config.min_departures) : 0;
    const rendered = deps.length;
    if (rendered > 0 && rendered < minDep) {
      const padCount = minDep - rendered;
      for (let i=0; i<padCount; i++) {
        rows.push(html`<div class="dep-row" style="visibility:hidden">&nbsp;</div>`);
      }
    }
    return rows;
  }

  render() {
    if (!this._config) return nothing;
    const c = this._config;
    const cardClass = c.display_preset === "e_ink" ? "e-ink"
      : c.display_preset === "compact" ? "compact"
      : c.display_preset === "minimal" ? "minimal"
      : c.display_preset === "native" ? "native" : "";

    return html`
      <ha-card class="${cardClass}" data-theme="${c.theme_mode}" data-header="${c.header_style}">
        ${c.show_header ? html`
          <div class="header" style="background:${this._getHeaderColor()}">
            <span class="header-icon">${c.icon ? html`<ha-icon icon="${c.icon}" style="color:var(--ptc-header-text, #fff);--mdc-icon-size:20px"></ha-icon>` : this._getAutoIcon()}</span>
            <div class="header-body">
              <div class="header-title">${this._getTitle()}</div>
              <div class="header-sub">${this._getSubtitle()}</div>
            </div>
            ${c.show_clock ? html`<div class="header-clock">${this._getClock()}</div>` : nothing}
            ${c.show_refresh ? html`<button class="header-refresh ${this._refreshing ? "spinning" : ""}" title=${t("refresh")} @click=${this._refresh}><ha-icon icon="mdi:refresh"></ha-icon></button>` : nothing}
          </div>
        ` : nothing}
        ${this._renderTabs()}
        ${this._renderAlerts()}
        <div class="dep-list ${c.columns > 1 ? `columns-${c.columns}` : ""}" aria-live="polite" aria-atomic="true">
          ${this._renderDeps()}
        </div>
        ${c.show_footer && c.show_last_update ? html`<div class="footer">${this._getLastUpdate()}</div>` : nothing}
      </ha-card>
    `;
  }
}
