import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

async function installCard(page) {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  await page.evaluate(() => {
    const map = {
      setView() { return this; },
      remove() {},
      invalidateSize() {},
      removeLayer() {},
      getZoom() { return 16; },
      attributionControl: { options: { prefix: '' }, setPrefix() {} },
    };
    (window as any).L = {
      map: () => map,
      tileLayer: () => ({ addTo() { return this; }, on() {}, setUrl() {} }),
      circleMarker: () => ({ addTo() {} }),
      divIcon: (opts: any) => opts,
      marker: () => ({
        addTo() { return this; }, bindPopup() { return this; }, off() { return this; },
        on() { return this; }, openPopup() { return this; }, setIcon() { return this; },
        setLatLng() { return this; }, getLatLng() { return { lat: 54.35, lng: 18.65 }; },
        bringToFront() {},
      }),
      polyline: () => ({ addTo() {} }),
      DomEvent: { stopPropagation() {} },
    };
    (window as any).ResizeObserver = class {
      observe() {}
      disconnect() {}
    };
  });
}

async function heapUsed(page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Runtime.enable');
  await client.send('HeapProfiler.enable');
  await client.send('HeapProfiler.collectGarbage');
  const { usedSize } = await client.send('Runtime.getHeapUsage');
  await client.detach();
  return usedSize as number;
}

test('repeated card and map lifecycles leave no DOM nodes behind', async ({ page }) => {
  test.setTimeout(120000);
  await installCard(page);
  const result = await page.evaluate(async () => {
    await customElements.whenDefined('polish-transport-card');
    const departures = Array.from({ length: 40 }, (_, index) => ({
      route: String(index % 3 + 1), headsign: 'Centrum',
      estimated_time: new Date(Date.now() + (index + 1) * 60000).toISOString(),
      theoretical_time: new Date(Date.now() + (index + 1) * 60000).toISOString(),
      vehicle_lat: 54.35, vehicle_lng: 18.65, vehicle_code: String(100 + index),
    }));
    const card: any = document.createElement('polish-transport-card');
    card.hass = {
      states: { 'sensor.x': { attributes: { departures } } },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };
    document.body.appendChild(card);

    for (let index = 0; index < 20; index += 1) {
      card.vehicleMap.showVehicleMap(54.35, 18.65, {
        entityId: 'sensor.x', code: String(index), route: '1', headsign: 'Centrum',
        provider: 'ztm_gdansk',
      });
      for (let wait = 0; wait < 40 && !document.querySelector('[role="dialog"] button'); wait += 1) {
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
      (document.querySelector('[role="dialog"] button') as HTMLButtonElement | null)?.click();
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
    card.remove();
    await new Promise((resolve) => setTimeout(resolve, 20));
    return {
      dialogs: document.querySelectorAll('[role="dialog"]').length,
      cards: document.querySelectorAll('polish-transport-card').length,
    };
  });

  expect(result.dialogs).toBe(0);
  expect(result.cards).toBe(0);
});

test('repeated card and map lifecycles keep the JS heap bounded', async ({ page }) => {
  test.setTimeout(180000);
  test.skip(!process.env.RUN_PERF, 'set RUN_PERF=1 to run the heap measurement');
  await installCard(page);
  const baseline = await heapUsed(page);

  await page.evaluate(async () => {
    await customElements.whenDefined('polish-transport-card');
    const departures = Array.from({ length: 100 }, (_, index) => ({
      route: String(index % 5 + 1), headsign: 'Centrum',
      estimated_time: new Date(Date.now() + (index + 1) * 60000).toISOString(),
      theoretical_time: new Date(Date.now() + (index + 1) * 60000).toISOString(),
      vehicle_lat: 54.35, vehicle_lng: 18.65, vehicle_code: String(1000 + index),
    }));
    for (let index = 0; index < 30; index += 1) {
      const card: any = document.createElement('polish-transport-card');
      card.hass = {
        states: { 'sensor.x': { attributes: { departures } } },
        callWS: async () => ({ token: null }),
        auth: { data: {} },
      };
      document.body.appendChild(card);
      card.requestUpdate();
      card.vehicleMap.showVehicleMap(54.35, 18.65, {
        entityId: 'sensor.x', code: String(index), route: '1', headsign: 'Centrum',
        provider: 'ztm_gdansk',
      });
      for (let wait = 0; wait < 40 && !document.querySelector('[role="dialog"] button'); wait += 1) {
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
      (document.querySelector('[role="dialog"] button') as HTMLButtonElement | null)?.click();
      card.remove();
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
  });

  const after = await heapUsed(page);
  console.log('HEAP usedSize baseline', baseline, 'after', after, 'delta', after - baseline);
  // Generous bound: noisy Chromium heap, but catches a per-card/per-map leak.
  expect(after - baseline).toBeLessThan(4 * 1024 * 1024);
});
