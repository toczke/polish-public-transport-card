import { test, expect } from '@playwright/test';
import * as path from 'path';

test('map marker uses one compact popup and no tooltip', async ({ page }) => {
  const scriptPath = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');
  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const result = await page.evaluate(async () => {
    document.documentElement.lang = 'pl';
    const state: any = {
      popupContent: '',
      popupOpen: false,
      tooltipBound: false,
      icon: null,
      handlers: {},
    };
    const map = {
      setView() { return this; },
      remove() {},
      invalidateSize() {},
      removeLayer() {},
      getZoom() { return 16; },
      attributionControl: { options: { prefix: '' }, setPrefix() {} },
    };
    const marker = {
      addTo() { return this; },
      bindPopup(content: string) { state.popupContent = content; return this; },
      bindTooltip() { state.tooltipBound = true; return this; },
      off() { state.handlers = {}; return this; },
      on(evt: string, fn: any) { state.handlers[evt] = fn; return this; },
      openPopup() { state.popupOpen = true; return this; },
      isPopupOpen() { return state.popupOpen; },
      setIcon(icon: any) { state.icon = icon; return this; },
      setLatLng() { return this; },
      getLatLng() { return { lat: 54.35, lng: 18.65 }; },
      bringToFront() {},
    };
    (window as any).L = {
      map: () => map,
      tileLayer: () => ({ addTo() { return this; }, on() {}, setUrl() {} }),
      circleMarker: () => ({ addTo() {} }),
      divIcon: (opts: any) => { state.icon = opts; return opts; },
      marker: () => marker,
      DomEvent: { stopPropagation() {} },
    };
    const card = document.createElement('mzkzg-transport-card') as any;
    card.hass = {
      states: {
        'sensor.x': {
          attributes: {
            departures: [
              { route: '6', headsign: 'Jelitkowo', vehicle_lat: 54.35, vehicle_lng: 18.65, vehicle_code: '100' },
            ],
          },
        },
      },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };
    document.body.appendChild(card);
    card.vehicleMap.showVehicleMap(54.35, 18.65, {
      entityId: 'sensor.x', code: '100', route: '6', headsign: 'Jelitkowo', provider: 'ztm_gdansk',
    });
    for (let i = 0; i < 100; i += 1) {
      if (document.querySelector('[role="dialog"]') && state.handlers.click) break;
      await new Promise((r) => setTimeout(r, 50));
    }

    const beforeClick = { ...state };
    state.handlers.click?.({ originalEvent: null });
    const afterClick = { ...state };
    const overlay = document.body.lastElementChild as HTMLElement;
    return {
      beforeClick,
      afterClick,
      overlayRole: overlay.getAttribute('role'),
      overlayLabel: overlay.getAttribute('aria-label'),
      closeLabel: overlay.querySelector('button')?.getAttribute('aria-label'),
      activeIsClose: document.activeElement === overlay.querySelector('button'),
    };
  });

  expect(result.beforeClick.tooltipBound).toBe(false);
  expect(result.beforeClick.popupOpen).toBe(false);
  expect(result.afterClick.popupOpen).toBe(true);
  expect(result.afterClick.popupContent).toContain('6');
  expect(result.afterClick.popupContent).toContain('Jelitkowo');
  expect(result.afterClick.popupContent).toContain('#100');
  expect(result.afterClick.popupContent).not.toMatch(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u);
  expect(result.afterClick.icon.iconSize).toEqual([50, 50]);
  expect(result.afterClick.icon.iconAnchor).toEqual([25, 25]);
  expect(result.overlayRole).toBe('dialog');
  expect(result.overlayLabel).toContain('Mapa pojazdu');
  expect(result.closeLabel).toBe('Zamknij');
  expect(result.activeIsClose).toBe(true);
});
