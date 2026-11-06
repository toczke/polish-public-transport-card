import { css } from "lit";

export const styles = css`
:host {
  display: block;
  --mzkzg-text: var(--primary-text-color, #111);
  --mzkzg-muted: var(--secondary-text-color, #888);
  --mzkzg-divider: var(--divider-color, #e5e5e5);
  --mzkzg-focus: var(--primary-color, #3b82f6);
  --mzkzg-live-dot: #10b981;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
ha-card {
  display: block;
  overflow: hidden;
  font-family: var(--ha-card-header-font-family, inherit);
  background: var(--card-background-color, #fff);
  color: var(--primary-text-color, #111);
  border-radius: var(--ha-card-border-radius, 12px);
  box-shadow: var(--ha-card-box-shadow, none);
}
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
.tabs { display: flex; overflow-x: auto; scrollbar-width: none; border-bottom: 1px solid var(--divider-color, #e5e5e5); }
.tabs::-webkit-scrollbar { display: none; }
.tab { flex: 1 0 auto; min-width: max-content; padding: 8px 14px; font-size: 12px; font-weight: 600; color: var(--mzkzg-muted); cursor: pointer; white-space: nowrap; border-bottom: 2px solid transparent; text-align: center; }
.tab.active { color: var(--mzkzg-text); border-bottom-color: var(--primary-color, #005eb8); }
.tab:hover { color: var(--mzkzg-text); }
.tab:focus-visible { outline: 2px solid var(--mzkzg-focus); outline-offset: -2px; }
.provider-header { padding: 4px 14px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; background: rgba(0, 0, 0, 0.04); color: var(--mzkzg-muted); border-bottom: 1px solid var(--divider-color, #e5e5e5); border-top: 1px solid var(--divider-color, #e5e5e5); margin-top: -1px; }
.dep-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-bottom: 1px solid var(--mzkzg-divider); min-height: 52px;
}
.dep-row.interactive { cursor: pointer; }
.dep-row:focus-visible { outline: 2px solid var(--mzkzg-focus); outline-offset: -2px; }
.dep-row:last-child { border-bottom: none; }
.dep-row.imminent { }
.dep-row.dimmed { opacity: 0.35; }
.badge {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 3px 7px; border-radius: 6px; font-size: 13px; font-weight: 700;
  color: #fff; min-width: 40px; flex-shrink: 0;
}
.headsign {
  font-size: 13px; font-weight: 500; color: var(--mzkzg-text);
  flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 2px 6px;
}
.head-main { display: inline-flex; align-items: center; gap: 6px; width: 100%; min-width: 0; }
.headsign-text { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 0 1 auto; min-width: 0; max-width: 100%; }
.icons { display: inline-flex; gap: 3px; align-items: center; flex-shrink: 0; white-space: nowrap; flex-basis: 100%; width: 100%; margin-top: 1px; }
.icons svg { color: var(--mzkzg-muted); opacity: 0.8; }
.platform { display: inline-flex; align-items: center; justify-content: center; background: var(--chip-background, #e5e7eb); color: var(--chip-color, #374151); border-radius: 6px; padding: 1px 6px; font-size: 10px; font-weight: 600; letter-spacing: 0.02em; white-space: nowrap; flex-shrink: 0; }
.meta-row { display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; width: 100%; margin-top: 1px; }
.stop-name { display: block; font-size: 10px; color: var(--mzkzg-muted); font-weight: 400; margin-top: 1px; width: 100%; }
ha-card.compact .stop-name { display: none; }
ha-card.compact .icons { display: none; }
ha-card.compact .meta-row { display: none; }
ha-card.compact .platform { display: none; }
ha-card.compact .footer { display: none; }
.dep-row.cancelled .headsign { text-decoration: line-through; opacity: 0.6; }
.dep-row.cancelled .badge { opacity: 0.5; }
.time-main.cancelled { font-size: 12px; color: #dc2626; font-weight: 600; }
.platform { display: inline-block; font-size: 10px; color: var(--mzkzg-muted); background: var(--mzkzg-divider); border-radius: 3px; padding: 1px 5px; vertical-align: middle; flex-shrink: 0; }

.time-col { text-align: right; flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.time-main { font-size: 15px; font-weight: 600; color: var(--mzkzg-text); white-space: nowrap; }
.time-struck { text-decoration: line-through; opacity: 0.5; font-size: 13px; font-weight: 400; }
.time-sub { font-size: 11px; color: var(--mzkzg-muted); white-space: nowrap; display: flex; align-items: center; gap: 4px; }
.time-sub .dot { color: var(--mzkzg-live-dot); font-weight: 700; display: inline-block; animation: live-dot-pulse 2s ease-in-out infinite; transform-origin: center; }
@keyframes live-dot-pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.72); } }
@media (prefers-reduced-motion: reduce) { .time-sub .dot { animation: none; } }
.delay-badge { font-size: 11px; font-weight: 600; }
.delay-badge.late { color: #dc2626; }
.delay-badge.early { color: #0369a1; }
.state-msg { padding: 24px 16px; text-align: center; color: var(--mzkzg-muted); font-size: 13px; }
.state-msg .icon { font-size: 28px; display: block; margin-bottom: 8px; }
.footer { padding: 5px 14px; font-size: 10px; color: var(--mzkzg-muted); text-align: right; border-top: 1px solid var(--mzkzg-divider); }
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

/* e-ink */
ha-card.e-ink { background: #fff; color: #000; border: 0; border-radius: 0; box-shadow: none; }
ha-card.e-ink .header { background: #fff !important; border-bottom: 2px solid #000; }
ha-card.e-ink .header-title, ha-card.e-ink .header-sub, ha-card.e-ink .header-icon { color: #000; }
ha-card.e-ink .header-icon ha-icon { color: #000 !important; --mdc-icon-size: 20px; }
ha-card.e-ink .stop-name, ha-card.e-ink .platform, ha-card.e-ink .icons, ha-card.e-ink .time-sub, ha-card.e-ink .footer { display: none; }
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
