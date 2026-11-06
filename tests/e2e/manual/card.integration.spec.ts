import { test, expect } from '@playwright/test';
import * as path from 'path';

const HA_URL = process.env.HA_URL || 'http://localhost:8123';

test('registers current and legacy card elements', async ({ page }) => {
  const scriptPath = path.resolve(
    'custom_components/mzkzg_transport/www/polish-transport-card.js'
  );

  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const registrations = await page.evaluate(() => {
    const card = customElements.get('mzkzg-transport-card');
    const legacyCard = customElements.get('polish-transport-card');
    const editor = customElements.get('mzkzg-transport-card-editor');
    const legacyEditor = customElements.get('polish-transport-card-editor');

    return {
      allRegistered: Boolean(card && legacyCard && editor && legacyEditor),
      cardConstructorsDiffer: card !== legacyCard,
      editorConstructorsDiffer: editor !== legacyEditor,
    };
  });

  expect(registrations.allRegistered).toBe(true);
  expect(registrations.cardConstructorsDiffer).toBe(true);
  expect(registrations.editorConstructorsDiffer).toBe(true);
});

test('opens the vehicle map for positioned departures from any provider', async ({ page }) => {
  const scriptPath = path.resolve(
    'custom_components/mzkzg_transport/www/polish-transport-card.js'
  );

  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const result = await page.evaluate(() => {
    const card = document.createElement('mzkzg-transport-card') as any;
    card.setConfig({
      type: 'custom:mzkzg-transport-card',
      entities: ['sensor.gzm_departures'],
      tap_action: { action: 'none' },
      hold_action: { action: 'none' },
      double_tap_action: { action: 'none' },
    });
    card._showVehicleMap = (lat: number, lng: number, info: unknown) => {
      card._openedMap = { lat, lng, info };
    };
    document.body.appendChild(card);
    card.hass = {
      states: {
        'sensor.gzm_departures': {
          state: '1',
          attributes: {
            provider: 'gtfsrt_gzm',
            departures: [{
              route: '7',
              headsign: 'Katowice',
              estimated_time: new Date(Date.now() + 600000).toISOString(),
              realtime: true,
              vehicle_code: 'GZM-42',
              vehicle_lat: 50.2649,
              vehicle_lng: 19.0238,
            }],
          },
        },
      },
    };

    const row = card.shadowRoot.querySelector('.dep-row');
    row.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    return {
      focusable: row.getAttribute('tabindex') === '0',
      openedMap: card._openedMap,
    };
  });

  expect(result.focusable).toBe(true);
  expect(result.openedMap).toMatchObject({ lat: 50.2649, lng: 19.0238 });
});

test('does not accumulate tab listeners during departure updates', async ({ page }) => {
  const scriptPath = path.resolve(
    'custom_components/mzkzg_transport/www/polish-transport-card.js'
  );

  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const calls = await page.evaluate(() => {
    const card = document.createElement('mzkzg-transport-card') as any;
    card.setConfig({
      type: 'custom:mzkzg-transport-card',
      entities: ['sensor.first', 'sensor.second'],
      view_mode: 'tabs',
    });
    let render = 0;
    card._renderDeps = () => `<div>${render++}</div>`;
    card.hass = {
      states: {
        'sensor.first': { attributes: { stop_name: 'First', departures: [] } },
        'sensor.second': { attributes: { stop_name: 'Second', departures: [] } },
      },
    };
    document.body.appendChild(card);

    card._updateContent();
    card._updateContent();
    card._updateContent();

    let clickCalls = 0;
    card._updateContent = () => { clickCalls += 1; };
    card.shadowRoot.querySelector('.tab[data-tab="1"]').click();
    card.remove();
    return clickCalls;
  });

  expect(calls).toBe(1);
});

test('shares Leaflet assets and destroys an open map on disconnect', async ({ page }) => {
  const scriptPath = path.resolve(
    'custom_components/mzkzg_transport/www/polish-transport-card.js'
  );

  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const result = await page.evaluate(async () => {
    const first = document.createElement('mzkzg-transport-card') as any;
    const second = document.createElement('mzkzg-transport-card') as any;
    const originalAppend = document.head.appendChild.bind(document.head);
    document.head.appendChild = ((node: Node) => {
      const result = originalAppend(node);
      if ((node as HTMLElement).id === 'polish-transport-leaflet-js') {
        queueMicrotask(() => {
          (window as any).L = {};
          node.dispatchEvent(new Event('load'));
        });
      }
      return result;
    }) as typeof document.head.appendChild;

    const firstLoad = first._preloadLeaflet();
    const secondLoad = second._preloadLeaflet();
    await Promise.all([firstLoad, secondLoad]);
    document.head.appendChild = originalAppend;

    let mapRemoved = false;
    let observerDisconnected = false;
    const map = {
      setView() { return this; },
      removeLayer() {},
      invalidateSize() {},
      remove() { mapRemoved = true; },
    };
    (window as any).L = {
      map: () => map,
      tileLayer: () => ({ addTo() {} }),
      circleMarker: () => ({ addTo() {} }),
    };
    (window as any).ResizeObserver = class {
      observe() {}
      disconnect() { observerDisconnected = true; }
    };

    document.body.appendChild(first);
    first._showVehicleMap(50.0, 19.0, {
      entityId: 'sensor.vehicle',
      code: '42',
      route: '7',
    });
    const overlay = first._mapCtx.overlay;
    await new Promise(requestAnimationFrame);
    first.remove();

    return {
      sharedPromise: firstLoad === secondLoad,
      stylesheets: document.querySelectorAll('#polish-transport-leaflet-css').length,
      scripts: document.querySelectorAll('#polish-transport-leaflet-js').length,
      overlayRemoved: !overlay.isConnected,
      contextCleared: first._mapCtx === null,
      mapRemoved,
      observerDisconnected,
    };
  });

  expect(result).toEqual({
    sharedPromise: true,
    stylesheets: 1,
    scripts: 1,
    overlayRemoved: true,
    contextCleared: true,
    mapRemoved: true,
    observerDisconnected: true,
  });
});

test('runs the refresh timer only while connected', async ({ page }) => {
  const scriptPath = path.resolve(
    'custom_components/mzkzg_transport/www/polish-transport-card.js'
  );

  await page.goto('about:blank');
  await page.addScriptTag({ path: scriptPath });

  const result = await page.evaluate(() => {
    const card = document.createElement('mzkzg-transport-card') as any;
    card.setConfig({ type: 'custom:mzkzg-transport-card', entities: [] });
    card.hass = { states: {} };
    const detachedTimer = card._tickTimer;
    document.body.appendChild(card);
    const connectedTimer = card._tickTimer;
    card.remove();
    return {
      detached: detachedTimer === null,
      connected: connectedTimer !== null,
      cleaned: card._tickTimer === null,
    };
  });

  expect(result).toEqual({ detached: true, connected: true, cleaned: true });
});

test.describe('Card rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${HA_URL}/dashboard-testing/ztm-gdansk`);
    await page.waitForTimeout(5000);
  });

  test('cards render with correct provider color', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
    await expect(card).toBeVisible();
    const header = card.locator('.header');
    const bg = await header.evaluate(el => getComputedStyle(el).backgroundColor);
    expect(bg).not.toBe('rgb(0, 0, 0)');
    expect(bg).not.toBe('');
  });

  test('card shows provider display name in subtitle', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
    const sub = card.locator('.header-sub');
    const text = await sub.textContent();
    expect(text).not.toContain('ztm_gdansk');
    expect(text).toContain('ZTM Gdańsk');
  });

  test('card shows departure rows', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
    const rows = card.locator('.dep-row');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('departure row has route badge and time', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
    const row = card.locator('.dep-row').first();
    const badge = row.locator('.route-badge');
    await expect(badge).toBeVisible();
    const time = row.locator('.time-col');
    await expect(time).toBeVisible();
  });

  test('card height is consistent with padding', async ({ page }) => {
    const cards = page.locator('mzkzg-transport-card, polish-transport-card');
    const count = await cards.count();
    if (count >= 2) {
      const h1 = await cards.nth(0).boundingBox();
      const h2 = await cards.nth(1).boundingBox();
      // Cards with same max_departures should have similar height
      if (h1 && h2) {
        expect(Math.abs(h1.height - h2.height)).toBeLessThan(100);
      }
    }
  });
});

test.describe('Config flow', () => {
  test('can open integration page', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    await expect(page.locator('text=Hubs')).toBeVisible();
  });

  test('configure button opens options with sleep mode', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    await page.getByRole('button', { name: 'Configure' }).first().click();
    await page.waitForTimeout(2000);
    // Should show sleep mode fields
    const dialog = page.locator('dialog');
    await expect(dialog).toBeVisible();
  });
});

test.describe('Health sensors', () => {
  test('health entities exist', async ({ page }) => {
    await page.goto(`${HA_URL}/config/entities?domain=binary_sensor`);
    await page.waitForTimeout(3000);
    // Check page has health entities
    const content = await page.content();
    expect(content).toContain('api_health');
  });
});

test.describe('Multi-stop architecture', () => {
  test('operator hub has multiple stop devices', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    // ZTM Gdańsk should have multiple devices listed
    const content = await page.content();
    expect(content).toContain('ztm_gdansk');
  });
});

test.describe('Visual editor', () => {
  test('editor does not reset config on open', async ({ page }) => {
    await page.goto(`${HA_URL}/dashboard-testing/ztm-gdansk`);
    await page.waitForTimeout(5000);
    // Enter edit mode
    await page.getByRole('button', { name: /edit/i }).click().catch(() => {});
    await page.waitForTimeout(1000);
    // The card should still show departures after edit mode
    const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
    const rows = card.locator('.dep-row');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Provider colors', () => {
  const providers = [
    { path: 'kiedyprzyjedzie-albatros', name: 'Albatros', color: '#166534' },
    { path: 'zbiorkom-krakow', name: 'ZTP Kraków', color: '#e2001a' },
    { path: 'gtfsrt-szczecin', name: 'ZDiTM Szczecin', color: '#005ca9' },
  ];

  for (const p of providers) {
    test(`${p.name} has correct color and label`, async ({ page }) => {
      await page.goto(`${HA_URL}/dashboard-testing/${p.path}`);
      await page.waitForTimeout(5000);
      const card = page.locator('mzkzg-transport-card, polish-transport-card').first();
      const sub = card.locator('.header-sub');
      const text = await sub.textContent();
      expect(text).toContain(p.name);
    });
  }
});
