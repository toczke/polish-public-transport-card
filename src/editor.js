import { LitElement, html, css, nothing } from 'lit';
import { normalizeEntityEntry, normalizeList, PROVIDER_LABELS } from './utils.js';

const SELECT = (options) => ({ select: { options } });
const MULTI_SELECT = (options) => ({ select: { multiple: true, options } });
const PROVIDER_OPTIONS = Object.entries(PROVIDER_LABELS)
  .map(([value, label]) => ({ value, label }))
  .sort((a, b) => a.label.localeCompare(b.label, "pl"));

const SCHEMA = [
  { name: "entities", selector: { entity: { multiple: true, domain: "sensor" } } },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "title", selector: { text: {} } },
      { name: "icon", selector: { icon: {} } },
    ],
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "display_preset", selector: SELECT([
        { value: "standard", label: "preset_standard" },
        { value: "compact", label: "preset_compact" },
        { value: "minimal", label: "preset_minimal" },
        { value: "native", label: "preset_native" },
        { value: "e_ink", label: "preset_eink" },
      ]) },
      { name: "view_mode", selector: SELECT([
        { value: "mixed", label: "view_mixed" },
        { value: "tabs", label: "view_tabs" },
        { value: "grouped", label: "view_grouped" },
      ]) },
      { name: "columns", selector: { number: { min: 1, max: 3, mode: "box" } } },
    ],
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "header_style", selector: SELECT([
        { value: "provider", label: "header_provider" },
        { value: "theme", label: "header_theme" },
        { value: "custom", label: "header_custom" },
      ]) },
      { name: "header_color", selector: { text: { type: "color" } } },
      { name: "show_header", selector: { boolean: {} } },
      { name: "show_clock", selector: { boolean: {} } },
      { name: "show_refresh", selector: { boolean: {} } },
    ],
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "max_departures", selector: { number: { min: 1, max: 100, mode: "box" } } },
      { name: "min_departures", selector: { number: { min: 0, max: 100, mode: "box" } } },
      { name: "refresh_interval", selector: { number: { min: 10, max: 600, mode: "box", unit_of_measurement: "s" } } },
      { name: "time_format", selector: SELECT([
        { value: "auto", label: "time_auto" },
        { value: "24h", label: "time_24h" },
        { value: "12h", label: "time_12h" },
      ]) },
    ],
  },
  {
    type: "expandable",
    title: "section_rows",
    schema: [
      { name: "show_delays", selector: { boolean: {} } },
      { name: "show_countdown", selector: { boolean: {} } },
      { name: "show_vehicle", selector: { boolean: {} } },
      { name: "show_platform", selector: { boolean: {} } },
      { name: "show_accessibility", selector: { boolean: {} } },
      { name: "show_alerts", selector: { boolean: {} } },
      { name: "show_stop_name", selector: { boolean: {} } },
      { name: "show_footer", selector: { boolean: {} } },
      { name: "show_last_update", selector: { boolean: {} } },
      { name: "show_bike", selector: { boolean: {} } },
      { name: "show_wheelchair", selector: { boolean: {} } },
      { name: "show_ac", selector: { boolean: {} } },
      { name: "show_ticket_machine", selector: { boolean: {} } },
    ],
  },
  {
    type: "expandable",
    title: "section_filters",
    schema: [
      { name: "filter_routes", selector: { text: { multiple: true } } },
      { name: "exclude_routes", selector: { text: { multiple: true } } },
      { name: "destination_filter", selector: { text: { multiple: true } } },
      { name: "exclude_destinations", selector: { text: { multiple: true } } },
      { name: "filter_vehicle_types", selector: { text: { multiple: true } } },
      { name: "filter_providers", selector: MULTI_SELECT(PROVIDER_OPTIONS) },
      { name: "filter_platform", selector: { text: {} } },
      { name: "filter_track", selector: { text: {} } },
      { name: "highlight_mode", selector: { boolean: {} } },
      { name: "hide_terminus", selector: { boolean: {} } },
      { name: "hide_cancelled", selector: { boolean: {} } },
      { name: "realtime_only", selector: { boolean: {} } },
      { name: "max_minutes", selector: { number: { min: 0, max: 1440, mode: "box", unit_of_measurement: "min" } } },
      { name: "hide_departed", selector: { boolean: {} } },
      { name: "departed_grace_minutes", selector: { number: { min: 0, max: 60, mode: "box", unit_of_measurement: "min" } } },
      { name: "only_low_floor", selector: { boolean: {} } },
      { name: "only_bike", selector: { boolean: {} } },
      { name: "only_ac", selector: { boolean: {} } },
      { name: "only_ticket_machine", selector: { boolean: {} } },
    ],
  },
  {
    type: "expandable",
    title: "section_interactions",
    schema: [
      { name: "tap_action", selector: { ui_action: {} } },
      { name: "hold_action", selector: { ui_action: {} } },
      { name: "double_tap_action", selector: { ui_action: {} } },
    ],
  },
];

const OVERRIDE_SCHEMA = [
  {
    type: "grid",
    name: "",
    schema: [
      { name: "max_departures", selector: { number: { min: 1, max: 100, mode: "box" } } },
    ],
  },
  {
    type: "expandable",
    title: "section_filters",
    schema: [
      { name: "filter_routes", selector: { text: { multiple: true } } },
      { name: "exclude_routes", selector: { text: { multiple: true } } },
      { name: "destination_filter", selector: { text: { multiple: true } } },
      { name: "exclude_destinations", selector: { text: { multiple: true } } },
      { name: "filter_vehicle_types", selector: { text: { multiple: true } } },
      { name: "filter_providers", selector: MULTI_SELECT(PROVIDER_OPTIONS) },
      { name: "filter_platform", selector: { text: {} } },
      { name: "filter_track", selector: { text: {} } },
      { name: "highlight_mode", selector: { boolean: {} } },
      { name: "hide_terminus", selector: { boolean: {} } },
      { name: "hide_cancelled", selector: { boolean: {} } },
      { name: "realtime_only", selector: { boolean: {} } },
      { name: "max_minutes", selector: { number: { min: 0, max: 1440, mode: "box", unit_of_measurement: "min" } } },
      { name: "hide_departed", selector: { boolean: {} } },
      { name: "departed_grace_minutes", selector: { number: { min: 0, max: 60, mode: "box", unit_of_measurement: "min" } } },
      { name: "only_low_floor", selector: { boolean: {} } },
      { name: "only_bike", selector: { boolean: {} } },
      { name: "only_ac", selector: { boolean: {} } },
      { name: "only_ticket_machine", selector: { boolean: {} } },
    ],
  },
];

const LIST_KEYS = new Set([
  "filter_routes",
  "exclude_routes",
  "destination_filter",
  "exclude_destinations",
  "filter_vehicle_types",
  "filter_providers",
]);

export class PolishTransportCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
      _targetEntity: { state: true },
    };
  }

  static styles = css`
    :host { display: block; }
    .editor { display: flex; flex-direction: column; gap: 10px; }
    .override {
      border: 1px solid var(--divider-color, #e5e5e5);
      border-radius: 10px;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: var(--secondary-background-color, rgba(0, 0, 0, 0.02));
    }
    .override-title { font-size: 13px; font-weight: 600; }
    .override-label { font-size: 12px; color: var(--secondary-text-color); }
    select {
      width: 100%;
      padding: 8px;
      border: 1px solid var(--divider-color, #ccc);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
    }
    .override-actions { display: flex; flex-wrap: wrap; gap: 6px; }
    .override-actions button {
      padding: 4px 10px;
      border: 1px solid var(--divider-color, #ccc);
      border-radius: 6px;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      cursor: pointer;
      font-size: 12px;
    }
    .override-actions button:disabled { opacity: 0.4; cursor: default; }
    .validation {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--error-color, #db4437);
      color: var(--error-color, #db4437);
      background: color-mix(in srgb, var(--error-color, #db4437) 8%, transparent);
      font-size: 12px;
    }
    .validation ul { margin: 0; padding-left: 16px; }
    .preview { font-size: 12px; color: var(--secondary-text-color); }
    .preview strong { color: var(--primary-text-color); }
  `;

  setConfig(config) {
    this._config = { ...config };
    this._previewCache = null;
    const entries = this._entries();
    if (!this._targetEntity || !entries.some(e => e.entity === this._targetEntity)) {
      this._targetEntity = entries[0]?.entity || "";
    }
  }

  _entries() {
    return (this._config?.entities || [])
      .map(e => (typeof e === "string" ? { entity: e } : e))
      .filter(e => e && e.entity);
  }

  _formData() {
    return { ...this._config, entities: this._entries().map(e => e.entity) };
  }

  _selectedEntry() {
    return this._entries().find(e => e.entity === this._targetEntity) || null;
  }

  _lang() {
    return (this.hass?.language || document.documentElement.lang || "en").slice(0, 2);
  }

  _localizeSchema(schema) {
    return schema.map((item) => {
      if (item.type === "expandable") {
        return {
          ...item,
          title: this._label(item.title),
          schema: this._localizeSchema(item.schema || []),
        };
      }
      if (item.schema) {
        return { ...item, schema: this._localizeSchema(item.schema) };
      }
      const select = item.selector?.select;
      if (select?.options) {
        return {
          ...item,
          selector: {
            select: {
              ...select,
              options: select.options.map((opt) => ({ ...opt, label: this._label(opt.label) })),
            },
          },
        };
      }
      return item;
    });
  }

  _preview() {
    if (!this.hass || !this._config?.entities?.length) return null;
    const ids = this._entries().map((e) => e.entity);
    const statesKey = ids
      .map((id) => `${id}:${this.hass.states?.[id]?.last_updated || ""}`)
      .join("|");
    const key = JSON.stringify(this._config) + "|" + statesKey;
    if (this._previewCache?.key === key) return this._previewCache.value;
    let total = 0;
    for (const id of ids) {
      total += (this.hass.states?.[id]?.attributes?.departures || []).length;
    }
    let filtered = null;
    try {
      const card = document.createElement("polish-transport-card");
      card.vehicleMap.preloadLeaflet = () => Promise.resolve();
      card.setConfig({ ...this._config });
      card.hass = this.hass;
      filtered = card._getDepartures().length;
    } catch {
      // Keep null when the preview cannot be computed.
    }
    const value = { total, filtered };
    this._previewCache = { key, value };
    return value;
  }

  _valueChanged(ev) {
    if (!this._config || !this.hass) return;
    const value = { ...ev.detail.value };
    if (Array.isArray(value.entities)) {
      value.entities = this._mergeEntitySelection(value.entities);
    }
    for (const key of LIST_KEYS) {
      if (key in value) value[key] = normalizeList(value[key]);
    }
    this._config = { ...this._config, ...value };
    this._dispatch();
  }

  _mergeEntitySelection(selected) {
    const existing = new Map(this._entries().map(e => [e.entity, e]));
    return (Array.isArray(selected) ? selected : []).map(item => {
      const id = typeof item === "string" ? item : item?.entity;
      const previous = existing.get(id);
      return previous && Object.keys(previous).length > 1 ? previous : id;
    }).filter(Boolean);
  }

  _targetChanged(ev) {
    this._targetEntity = ev.target.value;
  }

  _clearOverrides() {
    if (!this._config || !this._targetEntity) return;
    const entries = this._entries().map(entry =>
      entry.entity === this._targetEntity ? entry.entity : entry
    );
    this._config = { ...this._config, entities: entries };
    this._dispatch();
  }

  _moveEntry(delta) {
    const entries = this._entries();
    const idx = entries.findIndex(e => e.entity === this._targetEntity);
    const next = idx + delta;
    if (idx < 0 || next < 0 || next >= entries.length) return;
    const copy = [...entries];
    [copy[idx], copy[next]] = [copy[next], copy[idx]];
    this._config = { ...this._config, entities: copy };
    this._dispatch();
  }

  _entryLabel(entry) {
    const state = this.hass?.states?.[entry.entity];
    const stop = state?.attributes?.stop_name;
    const shortId = entry.entity.replace("sensor.", "");
    return stop ? `${stop} — ${shortId}` : shortId;
  }

  _validation() {
    const errors = [];
    const config = this._config || {};
    const max = parseInt(config.max_departures, 10) || 10;
    const min = parseInt(config.min_departures, 10) || 0;
    if (min > max) errors.push(this._label("validation_departures"));
    const color = config.header_color;
    if (config.header_style === "custom" && color) {
      const valid = /^(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\)|hsla?\([^)]+\)|linear-gradient\([^;{}]+\)|[a-zA-Z]{3,20})$/.test(String(color).trim());
      if (!valid) errors.push(this._label("validation_color"));
    }
    return errors;
  }

  _overrideChanged(ev) {
    if (!this._config || !this._targetEntity) return;
    const value = { ...ev.detail.value };
    for (const key of LIST_KEYS) {
      if (key in value) value[key] = normalizeList(value[key]);
    }
    const entries = this._entries().map(entry => {
      if (entry.entity !== this._targetEntity) return entry;
      const merged = { ...entry, ...value, entity: entry.entity };
      return Object.keys(merged).length > 1 ? normalizeEntityEntry(merged) : entry.entity;
    });
    this._config = { ...this._config, entities: entries };
    this._dispatch();
  }

  _dispatch() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    if (!this.hass || !this._config) return nothing;
    const entries = this._entries();
    const errors = this._validation();
    const preview = this._preview();
    const schema = this._localizeSchema(SCHEMA);
    const overrideSchema = this._localizeSchema(OVERRIDE_SCHEMA);
    const targetIndex = entries.findIndex(e => e.entity === this._targetEntity);
    return html`
      <div class="editor">
        ${errors.length ? html`
          <div class="validation">
            <ul>${errors.map(e => html`<li>${e}</li>`)}</ul>
          </div>
        ` : nothing}
        ${preview ? html`
          <div class="preview">${this._label("preview_rows")}: <strong>${preview.filtered ?? "—"}</strong> / ${preview.total}</div>
        ` : nothing}
        <ha-form
          .hass=${this.hass}
          .data=${this._formData()}
          .schema=${schema}
          .computeLabel=${(schema) => this._computeLabel(schema)}
          @value-changed=${this._valueChanged}
        ></ha-form>
        ${entries.length ? html`
          <div class="override">
            <div class="override-title">${this._label("override_title")}</div>
            <div class="override-label">${this._label("override_hint")}</div>
            <select @change=${this._targetChanged} .value=${this._targetEntity}>
              ${entries.map(e => html`<option value=${e.entity} ?selected=${e.entity === this._targetEntity}>${this._entryLabel(e)}</option>`)}
            </select>
            <div class="override-actions">
              <button ?disabled=${targetIndex <= 0} @click=${() => this._moveEntry(-1)}>↑ ${this._label("move_up")}</button>
              <button ?disabled=${targetIndex < 0 || targetIndex >= entries.length - 1} @click=${() => this._moveEntry(1)}>↓ ${this._label("move_down")}</button>
              <button @click=${this._clearOverrides}>${this._label("clear_overrides")}</button>
            </div>
            <ha-form
              .hass=${this.hass}
              .data=${this._selectedEntry() || {}}
              .schema=${overrideSchema}
              .computeLabel=${(schema) => this._computeLabel(schema)}
              @value-changed=${this._overrideChanged}
            ></ha-form>
          </div>
        ` : nothing}
      </div>
    `;
  }

  _computeLabel(schema) {
    return this._label(schema.name);
  }

  _label(name) {
    const pl = {
      entities: "Encje (sensory)",
      title: "Tytuł",
      icon: "Ikona",
      display_preset: "Motyw karty",
      view_mode: "Widok",
      columns: "Kolumny",
      show_refresh: "Pokaż przycisk odświeżania",
      header_style: "Styl nagłówka",
      header_color: "Kolor nagłówka",
      show_header: "Pokaż nagłówek",
      show_clock: "Pokaż zegar",
      max_departures: "Maks. odjazdów",
      min_departures: "Min. odjazdów (puste wiersze)",
      refresh_interval: "Odświeżanie",
      time_format: "Format czasu",
      show_delays: "Pokaż opóźnienia",
      show_countdown: "Pokaż odliczanie",
      show_vehicle: "Pokaż numer pojazdu",
      show_platform: "Pokaż peron / stanowisko",
      show_accessibility: "Pokaż ikony dostępności",
      show_alerts: "Pokaż komunikaty ZTM",
      show_stop_name: "Pokaż nazwę przystanku",
      show_footer: "Pokaż stopkę",
      show_last_update: "Pokaż czas aktualizacji",
      show_bike: "Rower",
      show_wheelchair: "Wózek",
      show_ac: "Klimatyzacja",
      show_ticket_machine: "Biletomat",
      filter_routes: "Linie — tylko",
      exclude_routes: "Linie — wyklucz",
      destination_filter: "Kierunki — tylko",
      exclude_destinations: "Kierunki — wyklucz",
      filter_vehicle_types: "Typ pojazdu (bus/tram/train)",
      filter_providers: "Providerzy",
      filter_platform: "Peron",
      filter_track: "Tor",
      highlight_mode: "Podświetlaj zamiast ukrywać",
      hide_terminus: "Ukryj kończące trasę",
      hide_cancelled: "Ukryj odwołane",
      realtime_only: "Tylko realtime",
      max_minutes: "Maks. minut do odjazdu",
      only_low_floor: "Tylko niskopodłogowe",
      only_bike: "Tylko z rowerem",
      only_ac: "Tylko klimatyzowane",
      only_ticket_machine: "Tylko z biletomatem",
      tap_action: "Kliknięcie",
      hold_action: "Przytrzymanie",
      double_tap_action: "Podwójne kliknięcie",
      section_rows: "Wiersze",
      section_filters: "Filtry",
      section_interactions: "Interakcje",
      preset_standard: "Standard",
      preset_compact: "Kompaktowy",
      preset_minimal: "Minimalny",
      preset_native: "Home Assistant",
      preset_eink: "E-ink",
      view_mixed: "Mieszany",
      view_tabs: "Zakładki",
      view_grouped: "Grupuj po linii",
      header_provider: "Kolor przewoźnika",
      header_theme: "Motyw Home Assistant",
      header_custom: "Własny kolor",
      time_auto: "Automatyczny (Home Assistant)",
      time_24h: "24-godzinny",
      time_12h: "12-godzinny",
      hide_departed: "Ukryj odjazdy po czasie",
      departed_grace_minutes: "Bufor po odjeździe",
      preview_rows: "Widoczne odjazdy",
      override_title: "Nadpisania per sensor",
      override_hint: "Puste pola dziedziczą ustawienia globalne.",
      move_up: "W górę",
      move_down: "W dół",
      clear_overrides: "Wyczyść nadpisania",
      validation_departures: "Min. odjazdów nie może być większe niż maks. odjazdów.",
      validation_color: "Kolor nagłówka musi być poprawnym kolorem CSS.",
    };
    const en = {
      entities: "Entities (sensors)",
      title: "Title",
      icon: "Icon",
      display_preset: "Card theme",
      view_mode: "View mode",
      columns: "Columns",
      show_refresh: "Show refresh button",
      header_style: "Header style",
      header_color: "Header color",
      show_header: "Show header",
      show_clock: "Show clock",
      max_departures: "Max departures",
      min_departures: "Min departures (padding)",
      refresh_interval: "Refresh interval",
      time_format: "Time format",
      show_delays: "Show delays",
      show_countdown: "Show countdown",
      show_vehicle: "Show vehicle number",
      show_platform: "Show platform / stand",
      show_accessibility: "Show accessibility icons",
      show_alerts: "Show ZTM alerts",
      show_stop_name: "Show stop name",
      show_footer: "Show footer",
      show_last_update: "Show last update",
      show_bike: "Bike",
      show_wheelchair: "Wheelchair",
      show_ac: "A/C",
      show_ticket_machine: "Ticket machine",
      filter_routes: "Routes — include",
      exclude_routes: "Routes — exclude",
      destination_filter: "Destinations — include",
      exclude_destinations: "Destinations — exclude",
      filter_vehicle_types: "Vehicle type (bus/tram/train)",
      filter_providers: "Providers",
      filter_platform: "Platform",
      filter_track: "Track",
      highlight_mode: "Highlight instead of hiding",
      hide_terminus: "Hide terminus",
      hide_cancelled: "Hide cancelled",
      realtime_only: "Real-time only",
      max_minutes: "Max minutes to departure",
      only_low_floor: "Low-floor only",
      only_bike: "Bike space only",
      only_ac: "Air-conditioned only",
      only_ticket_machine: "Ticket machine only",
      tap_action: "Tap",
      hold_action: "Hold",
      double_tap_action: "Double tap",
      section_rows: "Rows",
      section_filters: "Filters",
      section_interactions: "Interactions",
      preset_standard: "Standard",
      preset_compact: "Compact",
      preset_minimal: "Minimal",
      preset_native: "Home Assistant",
      preset_eink: "E-ink",
      view_mixed: "Mixed",
      view_tabs: "Tabs",
      view_grouped: "Group by line",
      header_provider: "Provider color",
      header_theme: "Home Assistant theme",
      header_custom: "Custom color",
      time_auto: "Auto (Home Assistant)",
      time_24h: "24-hour",
      time_12h: "12-hour",
      hide_departed: "Hide departed",
      departed_grace_minutes: "Post-departure grace",
      preview_rows: "Visible departures",
      override_title: "Per-sensor overrides",
      override_hint: "Empty fields inherit the global settings.",
      move_up: "Move up",
      move_down: "Move down",
      clear_overrides: "Clear overrides",
      validation_departures: "Min departures cannot exceed max departures.",
      validation_color: "Header color must be a valid CSS color.",
    };
    const lang = (this.hass?.language || document.documentElement.lang || "en").slice(0, 2);
    return (lang === "pl" ? pl : en)[name] || name;
  }
}

customElements.define("polish-transport-card-editor", PolishTransportCardEditor);
