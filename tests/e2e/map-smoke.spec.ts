import { test, expect } from '@playwright/test';
import * as path from 'path';

test('map opens and closes', async ({ page }) => {
  const scriptPath = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');
  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const result = await page.evaluate(async () => {
    const card = document.createElement('polish-transport-card') as any;
    card.hass = {
      states: { 'sensor.x': { attributes: { departures: [] } } },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };
    const map = {
      setView() { return this; },
      remove() {},
      invalidateSize() {},
      removeLayer() {},
      attributionControl: { options: { prefix: '' }, setPrefix() {} },
    };
    (window as any).L = {
      map: () => map,
      tileLayer: () => ({ addTo() { return this; }, on() {}, setUrl() {} }),
      circleMarker: () => ({ addTo() {} }),
      divIcon: () => ({}),
      marker: () => ({ addTo() {}, setIcon() {} }),
    };
    (window as any).ResizeObserver = class {
      observe() {}
      disconnect() {}
    };
    document.body.appendChild(card);
    card.vehicleMap.showVehicleMap(54.35, 18.65, {
      entityId: 'sensor.x', code: '1', route: '1', provider: 'ztm_gdansk',
    });
    await new Promise((r) => setTimeout(r, 100));
    const overlay = document.body.lastElementChild as HTMLElement;
    const before = Boolean(overlay && overlay.querySelector('button'));
    (overlay.querySelector('button') as HTMLButtonElement).click();
    await new Promise((r) => setTimeout(r, 50));
    return { before, after: document.body.lastElementChild === overlay, mapCtx: Boolean(card.vehicleMap.mapCtx) };
  });

  expect(result.before).toBe(true);
  expect(result.after).toBe(false);
  expect(result.mapCtx).toBe(false);
});
