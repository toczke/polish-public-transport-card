import { LitElement, html, css, nothing } from 'lit';
import { normalizeEntityEntry, normalizeList } from './utils.js';

const SELECT = (options) => ({ select: { options } });

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
        { value: "standard", label: "Standard" },
        { value: "compact", label: "Compact" },
        { value: "minimal", label: "Minimal" },
        { value: "native", label: "Home Assistant" },
        { value: "e_ink", label: "E-ink" },
      ]) },
      { name: "view_mode", selector: SELECT([
        { value: "mixed", label: "Mixed" },
        { value: "tabs", label: "Tabs" },
      ]) },
    ],
  },
  {
    type: "grid",
    name: "",
    schema: [
      { name: "header_style", selector: SELECT([
        { value: "provider", label: "Provider color" },
        { value: "theme", label: "Home Assistant theme" },
        { value: "custom", label: "Custom color" },
      ]) },
      { name: "header_color", selector: { text: { type: "color" } } },
      { name: "show_header", selector: { boolean: {} } },
      { name: "show_clock", selector: { boolean: {} } },
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
        { value: "auto", label: "Auto (Home Assistant)" },
        { value: "24h", label: "24-hour" },
        { value: "12h", label: "12-hour" },
      ]) },
    ],
  },
  {
    type: "expandable",
    title: "Rows",
    schema: [
      { name: "show_delays", selector: { boolean: {} } },
      { name: "show_countdown", selector: { boolean: {} } },
      { name: "show_vehicle", selector: { boolean: {} } },
      { name: "show_platform", selector: { boolean: {} } },
      { name: "show_accessibility", selector: { boolean: {} } },
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
    title: "Filters",
    schema: [
      { name: "filter_routes", selector: { text: { multiple: true } } },
      { name: "exclude_routes", selector: { text: { multiple: true } } },
      { name: "destination_filter", selector: { text: { multiple: true } } },
      { name: "exclude_destinations", selector: { text: { multiple: true } } },
      { name: "filter_vehicle_types", selector: { text: { multiple: true } } },
      { name: "filter_providers", selector: { text: { multiple: true } } },
      { name: "filter_platform", selector: { text: {} } },
      { name: "filter_track", selector: { text: {} } },
      { name: "highlight_mode", selector: { boolean: {} } },
      { name: "hide_terminus", selector: { boolean: {} } },
      { name: "hide_cancelled", selector: { boolean: {} } },
      { name: "realtime_only", selector: { boolean: {} } },
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
    title: "Filters",
    schema: [
      { name: "filter_routes", selector: { text: { multiple: true } } },
      { name: "exclude_routes", selector: { text: { multiple: true } } },
      { name: "destination_filter", selector: { text: { multiple: true } } },
      { name: "exclude_destinations", selector: { text: { multiple: true } } },
      { name: "filter_vehicle_types", selector: { text: { multiple: true } } },
      { name: "filter_providers", selector: { text: { multiple: true } } },
      { name: "filter_platform", selector: { text: {} } },
      { name: "filter_track", selector: { text: {} } },
      { name: "highlight_mode", selector: { boolean: {} } },
      { name: "hide_terminus", selector: { boolean: {} } },
      { name: "hide_cancelled", selector: { boolean: {} } },
      { name: "realtime_only", selector: { boolean: {} } },
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

export class MzkzgTransportCardEditor extends LitElement {
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
  `;

  setConfig(config) {
    this._config = { ...config };
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
    return html`
      <div class="editor">
        <ha-form
          .hass=${this.hass}
          .data=${this._formData()}
          .schema=${SCHEMA}
          .computeLabel=${(schema) => this._computeLabel(schema)}
          @value-changed=${this._valueChanged}
        ></ha-form>
        ${entries.length ? html`
          <div class="override">
            <div class="override-title">${this._label("override_title")}</div>
            <div class="override-label">${this._label("override_hint")}</div>
            <select @change=${this._targetChanged} .value=${this._targetEntity}>
              ${entries.map(e => html`<option value=${e.entity} ?selected=${e.entity === this._targetEntity}>${e.entity.replace("sensor.", "")}</option>`)}
            </select>
            <ha-form
              .hass=${this.hass}
              .data=${this._selectedEntry() || {}}
              .schema=${OVERRIDE_SCHEMA}
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
      override_title: "Nadpisania per sensor",
      override_hint: "Puste pola dziedziczą ustawienia globalne.",
    };
    const en = {
      entities: "Entities (sensors)",
      title: "Title",
      icon: "Icon",
      display_preset: "Card theme",
      view_mode: "View mode",
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
      override_title: "Per-sensor overrides",
      override_hint: "Empty fields inherit the global settings.",
    };
    const lang = (this.hass?.language || document.documentElement.lang || "en").slice(0, 2);
    return (lang === "pl" ? pl : en)[name] || name;
  }
}

customElements.define("mzkzg-transport-card-editor", MzkzgTransportCardEditor);
customElements.define("polish-transport-card-editor", class extends MzkzgTransportCardEditor {});
