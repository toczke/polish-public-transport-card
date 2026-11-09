import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

test('route badge text contrast follows the badge background', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await page.evaluate(async () => {
    await customElements.whenDefined('polish-transport-card');
    const now = Date.now();
    const hass = {
      states: {
        'sensor.x': {
          attributes: {
            provider: 'ztm_gdansk',
            departures: [
              { route: '65', headsign: 'Centrum', estimated_time: new Date(now + 60000).toISOString(), theoretical_time: new Date(now + 60000).toISOString() },
              { route: '195', headsign: 'Siedlce', estimated_time: new Date(now + 120000).toISOString(), theoretical_time: new Date(now + 120000).toISOString() },
            ],
          },
        },
      },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };
    const card: any = document.createElement('polish-transport-card');
    card.setConfig({ type: 'custom:polish-transport-card', entities: ['sensor.x'] });
    card.hass = hass;
    document.body.appendChild(card);
    await new Promise((resolve) => setTimeout(resolve, 100));
    return [...card.shadowRoot.querySelectorAll('.badge')].map((badge: any) => {
      const style = getComputedStyle(badge);
      return { text: badge.textContent.trim(), color: style.color, background: style.backgroundColor };
    });
  });

  const light = result.find((badge) => badge.text === '65');
  const dark = result.find((badge) => badge.text === '195');
  expect(light?.background).toBe('rgb(245, 158, 11)');
  expect(light?.color).toBe('rgb(17, 24, 39)');
  expect(dark?.background).toBe('rgb(218, 33, 40)');
  expect(dark?.color).toBe('rgb(255, 255, 255)');
});
