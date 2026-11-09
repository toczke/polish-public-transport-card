import { css } from "lit";

export const styles = css`
:host {
  display: block;
  --ptc-bg: var(--card-background-color, #fff);
  --ptc-text: var(--primary-text-color, #111);
  --ptc-muted: var(--secondary-text-color, #888);
  --ptc-divider: var(--divider-color, #e5e5e5);
  --ptc-focus: var(--primary-color, #3b82f6);
  --ptc-chip-bg: var(--chip-background, #e5e7eb);
  --ptc-chip-text: var(--chip-color, #374151);
  --ptc-header-text: #fff;
  --ptc-header-muted: rgba(255, 255, 255, 0.72);
  --ptc-live-dot: #10b981;
}
ha-card[data-theme="light"] {
  color-scheme: light;
  --ptc-bg: #fff;
  --ptc-text: #111827;
  --ptc-muted: #6b7280;
  --ptc-divider: #e5e7eb;
  --ptc-chip-bg: #eef1f5;
  --ptc-chip-text: #374151;
}
ha-card[data-theme="dark"] {
  color-scheme: dark;
  --ptc-bg: #1c1c1e;
  --ptc-text: #f2f2f7;
  --ptc-muted: #a1a1aa;
  --ptc-divider: #3a3a3c;
  --ptc-chip-bg: #2c2c2e;
  --ptc-chip-text: #f2f2f7;
  --ptc-header-text: #fff;
  --ptc-header-muted: rgba(255, 255, 255, 0.72);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
ha-card {
  display: block;
  overflow: hidden;
  font-family: var(--ha-card-header-font-family, inherit);
  background: var(--ptc-bg);
  color: var(--ptc-text);
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: var(--ha-card-box-shadow, none);
}
.header {
  padding: 8px 12px; display: flex; align-items: center; gap: 8px; user-select: none;
}
.header-icon { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 24px; height: 24px; color: var(--ptc-header-text); }
.header-icon svg { width: 18px; height: 18px; }
.header-body { flex: 1; min-width: 0; }
.header-title { color: var(--ptc-header-text); font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-sub { color: var(--ptc-header-muted); font-size: 10px; margin-top: 1px; }
.header-clock { color: var(--ptc-header-text); font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; opacity: 0.9; white-space: nowrap; }
.header-refresh {
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0; padding: 4px; border: none; border-radius: 50%;
  background: transparent; color: var(--ptc-header-text);
  cursor: pointer; opacity: 0.85; transition: background 0.2s, opacity 0.2s;
}
.header-refresh:hover { background: rgba(255, 255, 255, 0.16); opacity: 1; }
.header-refresh:focus-visible { outline: 2px solid var(--ptc-focus); outline-offset: 1px; }
.header-refresh.spinning ha-icon { animation: ptc-spin 1s linear infinite; }
@keyframes ptc-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.dep-list.columns-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.dep-list.columns-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.dep-list.columns-2 > .provider-header,
.dep-list.columns-3 > .provider-header { grid-column: 1 / -1; }
.dep-list.columns-2 > .dep-row,
.dep-list.columns-3 > .dep-row { border-right: 1px solid var(--ptc-divider); }
.dep-list.columns-2 > .dep-row:nth-child(even),
.dep-list.columns-3 > .dep-row:nth-child(3n) { border-right: none; }
.provider-header.line-header { text-transform: none; letter-spacing: 0; font-size: 12px; font-weight: 600; }
.dep-list { list-style: none; }
.alerts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--ptc-divider);
  background: rgba(255, 152, 0, 0.08);
}
.alert-item { display: flex; align-items: flex-start; gap: 8px; }
.alert-item ha-icon {
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--warning-color, #ff9800);
  --mdc-icon-size: 18px;
}
.alert-content { min-width: 0; }
.alert-title { font-size: 12px; font-weight: 600; color: var(--ptc-text); }
.alert-lines {
  display: inline-block;
  margin-right: 2px;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgba(255, 152, 0, 0.18);
  color: #b45309;
  font-size: 10px;
  font-weight: 700;
}
.alert-text {
  margin-top: 2px;
  color: var(--ptc-muted);
  font-size: 11px;
  line-height: 1.35;
  white-space: pre-line;
}
.dep-row { transition: opacity 0.4s, max-height 0.4s, padding 0.4s; max-height: 120px; overflow: hidden; }
.dep-row.departing { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
ha-card.e-ink .dep-row { transition: none; }
.tabs { display: flex; overflow-x: auto; scrollbar-width: none; border-bottom: 1px solid var(--divider-color, #e5e5e5); }
.tabs::-webkit-scrollbar { display: none; }
.tab { flex: 1 0 auto; min-width: max-content; padding: 8px 14px; font-size: 12px; font-weight: 600; color: var(--ptc-muted); cursor: pointer; white-space: nowrap; border-bottom: 2px solid transparent; text-align: center; }
.tab.active { color: var(--ptc-text); border-bottom-color: var(--primary-color, #005eb8); }
.tab:hover { color: var(--ptc-text); }
.tab:focus-visible { outline: 2px solid var(--ptc-focus); outline-offset: -2px; }
.provider-header { padding: 4px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; background: var(--secondary-background-color, rgba(0, 0, 0, 0.04)); color: var(--ptc-muted); border-bottom: 1px solid var(--ptc-divider); border-top: 1px solid var(--ptc-divider); margin-top: -1px; }
.dep-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-bottom: 1px solid var(--ptc-divider); min-height: 52px;
}
.dep-row.interactive { cursor: pointer; }
.dep-row.interactive:hover { background: var(--secondary-background-color, rgba(0, 0, 0, 0.03)); }
.dep-row:focus-visible { outline: 2px solid var(--ptc-focus); outline-offset: -2px; }
.dep-row:last-child { border-bottom: none; }
.dep-row.imminent { }
.dep-row.dimmed { opacity: 0.35; }
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 7px; border-radius: 6px; font-size: 13px; font-weight: 700;
  color: #fff; min-width: 40px; flex-shrink: 0;
}
.headsign {
  font-size: 13px; font-weight: 500; color: var(--ptc-text);
  flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px;
}
.head-main { display: inline-flex; align-items: center; gap: 6px; width: 100%; min-width: 0; }
.headsign-text { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; white-space: normal; overflow: hidden; line-height: 1.2; flex: 0 1 auto; min-width: 0; max-width: 100%; }
.icons { display: inline-flex; gap: 3px; align-items: center; flex-shrink: 0; white-space: nowrap; flex-basis: 100%; width: 100%; margin-left: 0; }
.icons svg { color: var(--ptc-muted); opacity: 0.75; }
.platform { display: inline-flex; align-items: center; justify-content: center; background: var(--ptc-chip-bg); color: var(--ptc-chip-text); border-radius: 6px; padding: 1px 6px; font-size: 10px; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap; flex-shrink: 0; }
.vehicle-no {
  display: inline-flex; align-items: center; flex-shrink: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 10px; font-weight: 600; letter-spacing: 0;
  color: var(--ptc-muted); background: var(--ptc-chip-bg);
  border-radius: 4px; padding: 0 4px; white-space: nowrap;
}
.meta-row { display: flex; align-items: center; justify-content: flex-start; gap: 2px 6px; flex-wrap: wrap; width: 100%; margin-top: 2px; }
.meta-chips { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.meta-pill { display: inline-flex; align-items: center; background: var(--ptc-chip-bg); color: var(--ptc-chip-text); border-radius: 6px; padding: 1px 6px; font-size: 10px; font-weight: 600; letter-spacing: 0.01em; white-space: nowrap; }
.train-info { display: inline-flex; align-items: center; font-size: 10px; font-weight: 500; color: var(--ptc-muted); white-space: nowrap; }
.stop-name { display: block; font-size: 10px; color: var(--ptc-muted); font-weight: 400; margin-top: 1px; width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
ha-card.minimal .header,
ha-card.minimal .footer,
ha-card.minimal .stop-name,
ha-card.minimal .icons,
ha-card.minimal .platform,
ha-card.minimal .vehicle-no,
ha-card.minimal .meta-row { display: none; }
ha-card.minimal .dep-row { min-height: 34px; padding: 5px 10px; gap: 8px; }
ha-card.minimal .badge { min-width: 32px; padding: 2px 5px; font-size: 11px; }
ha-card.minimal .headsign { font-size: 12px; }
ha-card.minimal .time-main { font-size: 13px; }
ha-card.minimal .time-sub { font-size: 10px; }
ha-card.compact .stop-name { display: none; }
ha-card.compact .icons { display: none; }
ha-card.compact .meta-row { display: none; }
ha-card.compact .platform { display: none; }
ha-card.compact .footer { display: none; }
.dep-row.cancelled .headsign { text-decoration: line-through; opacity: 0.6; }
.dep-row.cancelled .badge { opacity: 0.5; }
.time-main.cancelled { font-size: 12px; color: #dc2626; font-weight: 600; }
.provider-header { color: var(--ptc-muted); }

.time-col { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 1px; min-width: 76px; font-variant-numeric: tabular-nums; }
.time-main { font-size: 15px; font-weight: 600; color: var(--ptc-text); white-space: nowrap; }
.time-struck { text-decoration: line-through; opacity: 0.5; font-size: 13px; font-weight: 400; }
.time-sub { font-size: 11px; color: var(--ptc-muted); white-space: nowrap; display: flex; align-items: center; gap: 4px; }
.time-sub .dot { color: var(--ptc-live-dot); font-weight: 700; display: inline-block; animation: live-dot-pulse 2s ease-in-out infinite; transform-origin: center; }
@keyframes live-dot-pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.72); } }
@media (prefers-reduced-motion: reduce) { .time-sub .dot { animation: none; } }
.delay-badge { font-size: 11px; font-weight: 600; }
.delay-badge.late { color: #dc2626; }
.delay-badge.early { color: #0369a1; }
.state-msg { padding: 24px 16px; text-align: center; color: var(--ptc-muted); font-size: 13px; }
.state-msg .state-icon { --mdc-icon-size: 32px; color: var(--ptc-muted); display: block; margin: 0 auto 8px; }
.footer { padding: 5px 14px; font-size: 10px; color: var(--ptc-muted); text-align: right; border-top: 1px solid var(--ptc-divider); }
.skel { background: var(--divider-color, #e5e5e5); border-radius: 4px; }
@keyframes shimmer { 0%,100%{opacity:.5} 50%{opacity:1} }
.skel { animation: shimmer 1.4s ease-in-out infinite; }

/* Vehicle map modal */
.map-overlay {
  position: fixed; top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.5); z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.map-wrap {
  position: relative; width: 90%; max-width: 500px; height: 60vh; max-height: 400px;
  background: #fff; border-radius: 12px; overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.map-wrap .leaflet-container { border-radius: 12px; }
.map-close {
  position: absolute; top: 8px; right: 8px; z-index: 1001;
  background: rgba(255,255,255,0.9); border: none; border-radius: 50%;
  width: 32px; height: 32px; cursor: pointer; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
  color: #333; box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}
.map-close:hover { background: #fff; }

/* Home Assistant native look */
ha-card.native {
  background: var(--ha-card-background, var(--card-background-color));
  color: var(--primary-text-color);
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: var(--ha-card-box-shadow, none);
}
ha-card.native .header {
  background: transparent !important;
  color: var(--primary-text-color);
  border-bottom: 1px solid var(--divider-color);
  padding: 12px 16px;
}
ha-card.native .header-title { color: var(--primary-text-color); font-size: 16px; font-weight: 500; }
ha-card.native .header-sub { color: var(--secondary-text-color); }
ha-card.native .header-icon { color: var(--primary-color); }
ha-card.native .header-icon svg { color: var(--primary-color); }
ha-card.native .header-clock { color: var(--secondary-text-color); }
ha-card.native .badge {
  background: var(--secondary-background-color);
  color: var(--primary-text-color);
  border: 1px solid var(--divider-color);
  font-weight: 600;
}
ha-card.native .dep-row { padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
ha-card.native .dep-row.interactive:hover { background: var(--secondary-background-color); }
ha-card.native .vehicle-no { background: var(--secondary-background-color); color: var(--secondary-text-color); }
ha-card.native .meta-pill { background: var(--secondary-background-color); color: var(--secondary-text-color); }
ha-card.native .train-info { color: var(--secondary-text-color); }
ha-card.native .time-main { font-weight: 500; }
ha-card.native .platform { background: var(--secondary-background-color); color: var(--secondary-text-color); }
ha-card.native .tabs { border-bottom: 1px solid var(--divider-color); }
ha-card.native .tab.active { color: var(--primary-color); border-bottom-color: var(--primary-color); }
ha-card.native .footer { border-top: 1px solid var(--divider-color); }
ha-card.native .header-refresh { color: var(--secondary-text-color); }
ha-card.native .header-refresh:hover { background: var(--secondary-background-color); }
ha-card.native .state-msg { color: var(--secondary-text-color); }
ha-card.native .delay-badge.late { color: var(--error-color, #db4437); }
ha-card.native .delay-badge.early { color: var(--info-color, #039be5); }

/* e-ink */
ha-card.e-ink { background: #fff; color: #000; border: 0; border-radius: 0; box-shadow: none; }
ha-card.e-ink .header { background: #fff !important; border-bottom: 2px solid #000; }
ha-card.e-ink .header-title, ha-card.e-ink .header-sub, ha-card.e-ink .header-icon { color: #000; }
ha-card.e-ink .header-icon ha-icon { color: #000 !important; --mdc-icon-size: 20px; }
ha-card.e-ink .stop-name, ha-card.e-ink .platform, ha-card.e-ink .icons, ha-card.e-ink .time-sub, ha-card.e-ink .footer,
ha-card.e-ink .meta-row, ha-card.e-ink .vehicle-no { display: none; }
ha-card.e-ink .dep-row.interactive:hover { background: #fff; }
ha-card.e-ink .dep-row { border-bottom-color: #000; }
ha-card.e-ink .badge { background: #fff !important; border: 2px solid #000; color: #000; }
ha-card.e-ink .dep-row.imminent { background: #fff; }
ha-card.e-ink .headsign, ha-card.e-ink .time-main, ha-card.e-ink .state-msg { color: #000; }
ha-card.e-ink .time-sub .dot, ha-card.e-ink .delay-badge, ha-card.e-ink .delay-badge.late, ha-card.e-ink .delay-badge.early { color: #000; }
ha-card.e-ink .skel { animation: none; }

/* compact */
ha-card.compact .header { padding: 9px 12px; gap: 8px; }
ha-card.compact .header-icon { width: 24px; height: 24px; }
ha-card.compact .header-icon svg { width: 19px; height: 19px; }
ha-card.compact .header-title { font-size: 14px; }
ha-card.compact .header-sub { font-size: 10px; }
ha-card.compact .dep-list { padding-top: 4px; }
ha-card.compact .dep-row { min-height: 40px; padding: 6px 12px; gap: 8px; }
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
  .dep-row { padding: 8px 10px; gap: 8px; min-height: 40px; }
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
