import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');
const PRESETS = ['standard', 'compact', 'minimal', 'native', 'e_ink'];
const TIME = '2026-11-06T21:22:00';

test.describe('visual presets', () => {
  for (const preset of PRESETS) {
    test(`preset ${preset}`, async ({ page }) => {
      await page.setViewportSize({ width: 460, height: 900 });
      await page.goto('about:blank');
      await page.addScriptTag({ path: SCRIPT });
      await page.evaluate(async ({ preset, time }) => {
        document.documentElement.lang = 'pl';
        const vars: Record<string, string> = {
          '--primary-text-color': '#111827',
          '--secondary-text-color': '#6b7280',
          '--card-background-color': '#ffffff',
          '--secondary-background-color': '#f4f5f7',
          '--divider-color': '#e5e7eb',
          '--primary-color': '#005eb8',
          '--chip-background': '#eef1f5',
          '--chip-color': '#374151',
          '--ha-card-header-font-family': 'Arial, sans-serif',
        };
        for (const [key, value] of Object.entries(vars)) {
          document.documentElement.style.setProperty(key, value);
        }

        const wrapper = document.createElement('div');
        wrapper.id = 'visual-wrapper';
        wrapper.style.cssText = 'width:420px;display:flex;flex-direction:column;gap:12px;padding:8px;background:#fff;font-family:Arial,sans-serif;';
        document.body.appendChild(wrapper);

        const ztm = document.createElement('polish-transport-card') as any;
        ztm.setConfig({
          entities: ['sensor.ztm'],
          title: 'Płocka',
          display_preset: preset,
          header_style: 'provider',
          show_clock: false,
          show_countdown: false,
          show_delays: false,
          hide_departed: false,
          hide_terminus: false,
          max_departures: 5,
        });
        ztm.hass = {
          locale: { language: 'pl' },
          states: {
            'sensor.ztm': {
              attributes: {
                provider: 'ztm_gdansk',
                stop_name: 'Płocka',
                departures: [
                  { route: '6', headsign: 'Jelitkowo', theoretical_time: time, estimated_time: time, realtime: true, vehicle_code: '1015', platform: '5', bike_allowed: true, wheelchair_accessible: true, vehicle_lat: 54.4, vehicle_lng: 18.6 },
                  { route: '175', headsign: 'Siedlce', theoretical_time: time, estimated_time: time, realtime: false, air_conditioning: true },
                  { route: 'N1', headsign: 'Lotnisko', theoretical_time: time, estimated_time: time, realtime: false },
                ],
              },
            },
          },
        };

        const plk = document.createElement('polish-transport-card') as any;
        plk.setConfig({
          entities: ['sensor.plk'],
          title: 'Gdańsk Śródmieście',
          display_preset: preset,
          header_style: 'provider',
          show_clock: false,
          show_footer: false,
          hide_departed: false,
          hide_terminus: false,
          max_departures: 5,
        });
        plk.hass = {
          locale: { language: 'pl' },
          states: {
            'sensor.plk': {
              attributes: {
                provider: 'plk_rail',
                stop_name: 'Gdańsk Śródmieście',
                departures: [
                  { route: 'S1', headsign: 'Wejherowo', theoretical_time: time, estimated_time: time, realtime: false, platform: '1', track: '501', train_number: '95695', carrier: 'PKP Szybka Kolej Miejska w Trójmieście' },
                  { route: 'S1', headsign: 'Gdynia Cisowa', theoretical_time: time, estimated_time: time, realtime: false, platform: '1', track: '502', train_number: '95489', carrier: 'PKM' },
                ],
              },
            },
          },
        };

        wrapper.append(ztm, plk);
        await new Promise((resolve) => requestAnimationFrame(resolve));
      }, { preset, time: TIME });

      const wrapper = page.locator('#visual-wrapper');
      await expect(wrapper).toHaveScreenshot(`preset-${preset}.png`, {
        animations: 'disabled',
        caret: 'hide',
        maxDiffPixelRatio: 0.12,
        threshold: 0.3,
      });
    });
  }
});
