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

test('native preset is reflected in the card DOM', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await makeCard(page, {
    entities: ['sensor.test'],
    header_style: 'theme',
    display_preset: 'native',
  }, {
    locale: { language: 'pl', time_format: '24' },
    states: { 'sensor.test': { attributes: { departures: [], stop_name: 'Test' } } },
  });
  expect(result.classes).toContain('native');
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

test('grouped view adds a line header per route and headsign', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const now = new Date(Date.now() + 300000).toISOString();
  const later = new Date(Date.now() + 900000).toISOString();
  const result = await page.evaluate(async ({ now, later }) => {
    const card: any = document.createElement('polish-transport-card');
    card.setConfig({ entities: ['sensor.test'], view_mode: 'grouped' });
    document.body.appendChild(card);
    card.hass = {
      locale: { language: 'pl' },
      states: { 'sensor.test': { attributes: { provider: 'ztm_gdansk', stop_name: 'Test', departures: [
        { route: '6', headsign: 'Jelitkowo', estimated_time: now, theoretical_time: now, realtime: true },
        { route: '6', headsign: 'Jelitkowo', estimated_time: later, theoretical_time: later, realtime: true },
        { route: '7', headsign: 'Nowy Port', estimated_time: later, theoretical_time: later, realtime: true },
      ] } } },
    };
    await card.updateComplete;
    return {
      headers: [...card.shadowRoot.querySelectorAll('.line-header')].map((e: any) => e.textContent.trim()),
      rows: card.shadowRoot.querySelectorAll('.dep-row').length,
    };
  }, { now, later });
  expect(result.headers).toEqual(['6 → Jelitkowo', '7 → Nowy Port']);
  expect(result.rows).toBe(3);
});

test('columns and refresh button are rendered from config', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const now = new Date(Date.now() + 300000).toISOString();
  const result = await page.evaluate(async (now) => {
    const card: any = document.createElement('polish-transport-card');
    let serviceCall = null;
    card.setConfig({ entities: ['sensor.test'], columns: 3, show_refresh: true });
    document.body.appendChild(card);
    card.hass = {
      locale: { language: 'pl' },
      states: { 'sensor.test': { state: 'ok', attributes: { provider: 'ztm_gdansk', stop_name: 'Test', departures: [
        { route: '6', headsign: 'Jelitkowo', estimated_time: now, theoretical_time: now, realtime: true },
      ] } } },
      callService: (domain: string, service: string, data: any) => { serviceCall = { domain, service, data }; return Promise.resolve(); },
    };
    await card.updateComplete;
    const list = card.shadowRoot.querySelector('.dep-list');
    const button = card.shadowRoot.querySelector('.header-refresh');
    button?.click();
    await new Promise((r) => setTimeout(r, 50));
    return {
      columns: list?.className,
      hasButton: Boolean(button),
      serviceCall,
    };
  }, now);
  expect(result.columns).toContain('columns-3');
  expect(result.hasButton).toBe(true);
  expect(result.serviceCall).toEqual({ domain: 'homeassistant', service: 'update_entity', data: { entity_id: ['sensor.test'] } });
});

test('time and vehicle feature filters are applied', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const soon = new Date(Date.now() + 300000).toISOString();
  const late = new Date(Date.now() + 3600000).toISOString();
  const departures = [
    { route: '6', headsign: 'A', estimated_time: soon, theoretical_time: soon, realtime: true, wheelchair_accessible: true },
    { route: '7', headsign: 'B', estimated_time: late, theoretical_time: late, realtime: true, wheelchair_accessible: true },
    { route: '8', headsign: 'C', estimated_time: soon, theoretical_time: soon, realtime: true, wheelchair_accessible: false, floor_height: 'Pojazd wysokopodłogowy' },
  ];
  const result = await page.evaluate(async ({ departures }) => {
    const card: any = document.createElement('polish-transport-card');
    card.setConfig({ entities: ['sensor.test'], max_minutes: 30, only_low_floor: true });
    document.body.appendChild(card);
    card.hass = {
      locale: { language: 'pl' },
      states: { 'sensor.test': { attributes: { provider: 'ztm_gdansk', stop_name: 'Test', departures } } },
    };
    await card.updateComplete;
    return [...card.shadowRoot.querySelectorAll('.badge')].map((e: any) => e.textContent.trim());
  }, { departures });
  expect(result).toEqual(['6']);
});
