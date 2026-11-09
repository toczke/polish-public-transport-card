import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

test('card renders matching and city-wide ZTM alerts', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await page.evaluate(async () => {
    await customElements.whenDefined('polish-transport-card');
    const matching = {
      id: '11936',
      title: 'Awaryjna zmiana trasy linii 195',
      content: 'Objazd przez Al. Havla. Nieobsługiwane: Świętokrzyska 01.',
      lines: ['195'],
      url: 'https://ztm.gda.pl/komunikaty/awaryjna-zmiana-trasy-linii-195,a,11936',
    };
    const cityOnly = {
      id: '11994',
      title: 'Linie 117, 122, 143: zmiany na trasie w Sopocie',
      content: 'Objazd w Sopocie.',
      lines: ['117', '122', '143'],
      url: 'https://ztm.gda.pl/komunikaty/linie-117-122-143,a,11994',
    };
    const hass = {
      states: {
        'sensor.x': {
          attributes: { departures: [], alerts: [matching], alerts_city: [matching, cityOnly] },
        },
      },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };

    const make = async (config: any) => {
      const card: any = document.createElement('polish-transport-card');
      card.setConfig({ type: 'custom:polish-transport-card', entities: ['sensor.x'], ...config });
      card.hass = hass;
      document.body.appendChild(card);
      await new Promise((resolve) => setTimeout(resolve, 50));
      return card.shadowRoot?.querySelector('.alerts')?.textContent || '';
    };

    return {
      matching: await make({}),
      city: await make({ alerts_scope: 'city' }),
      hidden: await make({ show_alerts: false }),
    };
  });

  expect(result.matching).toContain('Awaryjna zmiana trasy linii 195');
  expect(result.matching).not.toContain('Linie 117');
  expect(result.city).toContain('Awaryjna zmiana trasy linii 195');
  expect(result.city).toContain('Linie 117');
  expect(result.hidden).toBe('');
});
