import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

async function makeCard(page: any, config: any, hass: any) {
  return await page.evaluate(async ({ config, hass }) => {
    const card: any = document.createElement('polish-transport-card');
    card.setConfig(config);
    document.body.appendChild(card);
    card.hass = hass;
    await card.updateComplete;
    return {
      theme: card.shadowRoot.querySelector('ha-card')?.getAttribute('data-theme'),
      classes: card.shadowRoot.querySelector('ha-card')?.className,
      depotCount: card.shadowRoot.querySelectorAll('.dep-row').length,
      routes: [...card.shadowRoot.querySelectorAll('.badge')].map((e: any) => e.textContent.trim()),
      mapPins: card.shadowRoot.querySelectorAll('.map-pin').length,
    };
  }, { config, hass });
}

test('theme mode and header style are reflected in the card DOM', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await makeCard(page, {
    entities: ['sensor.test'],
    theme_mode: 'dark',
    header_style: 'theme',
    display_preset: 'minimal',
  }, {
    locale: { language: 'pl', time_format: '24' },
    states: { 'sensor.test': { attributes: { departures: [], stop_name: 'Test' } } },
  });
  expect(result.theme).toBe('dark');
  expect(result.classes).toContain('minimal');
});

test('global and per-sensor filters are applied', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const now = new Date(Date.now() + 600000).toISOString();
  const departures = [
    { route: '6', headsign: 'Jelitkowo', estimated_time: now, theoretical_time: now, realtime: true, vehicle_type: 'bus', vehicle_lat: 54.4, vehicle_lng: 18.6 },
    { route: '7', headsign: 'Nowy Port', estimated_time: now, theoretical_time: now, realtime: true, vehicle_type: 'bus' },
    { route: '175', headsign: 'Siedlce', estimated_time: now, theoretical_time: now, realtime: true, vehicle_type: 'bus' },
  ];
  const result = await makeCard(page, {
    entities: [
      { entity: 'sensor.one', filter_routes: ['6'] },
      { entity: 'sensor.two', exclude_destinations: ['Siedlce'] },
    ],
    filter_vehicle_types: ['bus'],
  }, {
    locale: { language: 'pl', time_format: '24' },
    states: {
      'sensor.one': { attributes: { provider: 'ztm_gdansk', stop_name: 'One', departures } },
      'sensor.two': { attributes: { provider: 'ztm_gdansk', stop_name: 'Two', departures } },
    },
  });
  expect(result.routes).toEqual(['6', '6', '7']);
  expect(result.mapPins).toBe(2);
});
