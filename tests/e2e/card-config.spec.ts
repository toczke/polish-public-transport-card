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
  expect(result.mapPins).toBe(0);
});

test('rows without live position are not clickable', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const soon = new Date(Date.now() + 300000).toISOString();
  const departures = [
    { route: '6', headsign: 'Live', estimated_time: soon, theoretical_time: soon, realtime: true, vehicle_lat: 54.4, vehicle_lng: 18.6, vehicle_code: '100' },
    { route: '7', headsign: 'Static', estimated_time: soon, theoretical_time: soon, realtime: false },
  ];
  const result = await page.evaluate(async ({ departures }) => {
    const card: any = document.createElement('polish-transport-card');
    card.setConfig({ entities: ['sensor.test'] });
    document.body.appendChild(card);
    card.hass = {
      locale: { language: 'pl' },
      states: { 'sensor.test': { attributes: { provider: 'ztm_gdansk', stop_name: 'Test', departures } } },
    };
    await card.updateComplete;
    let moreInfo = 0;
    card.addEventListener('hass-more-info', () => { moreInfo += 1; });
    const rows = [...card.shadowRoot.querySelectorAll('.dep-row')] as HTMLElement[];
    const staticRow = rows.find((r) => r.textContent.includes('Static')) as HTMLElement;
    const liveRow = rows.find((r) => r.textContent.includes('Live')) as HTMLElement;
    staticRow.click();
    await new Promise((r) => setTimeout(r, 300));
    return {
      moreInfo,
      staticInteractive: staticRow.classList.contains('interactive'),
      staticTabindex: staticRow.getAttribute('tabindex'),
      liveInteractive: liveRow.classList.contains('interactive'),
      liveTabindex: liveRow.getAttribute('tabindex'),
    };
  }, { departures });
  expect(result.moreInfo).toBe(0);
  expect(result.staticInteractive).toBe(false);
  expect(result.staticTabindex).toBe('-1');
  expect(result.liveInteractive).toBe(true);
  expect(result.liveTabindex).toBe('0');
});

test('prefix headsign duplicates are merged in the card', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const time = '2026-11-06T21:22:00+01:00';
  const departures = [
    { route: '3', headsign: 'Brzeźno', estimated_time: time, theoretical_time: time, realtime: false, trip_id: 102, route_id_int: 3, vehicle_code: '' },
    { route: '3', headsign: 'Brzeźno Dom Zdrojowy', estimated_time: time, theoretical_time: time, realtime: false },
    { route: '3', headsign: 'Nowy Port', estimated_time: time, theoretical_time: time, realtime: false },
  ];
  const result = await page.evaluate(async ({ departures }) => {
    const card: any = document.createElement('polish-transport-card');
    card.setConfig({ entities: ['sensor.test'], hide_terminus: false });
    document.body.appendChild(card);
    card.hass = {
      locale: { language: 'pl' },
      states: { 'sensor.test': { attributes: { provider: 'ztm_gdansk', stop_name: 'Test', departures } } },
    };
    await card.updateComplete;
    return {
      rows: card.shadowRoot.querySelectorAll('.dep-row').length,
      headsigns: [...card.shadowRoot.querySelectorAll('.headsign-text')].map((e: any) => e.textContent.trim()),
    };
  }, { departures });
  expect(result.rows).toBe(2);
  expect(result.headsigns).toEqual(['Brzeźno Dom Zdrojowy', 'Nowy Port']);
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
