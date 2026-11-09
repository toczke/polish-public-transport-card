import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

test('card renders ZTM alerts and can hide them', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await page.evaluate(async () => {
    await customElements.whenDefined('polish-transport-card');
    const alerts = [{
      id: '11936',
      title: 'Awaryjna zmiana trasy linii 195',
      content: 'Objazd przez Al. Havla. Nieobsługiwane: Świętokrzyska 01.',
      lines: ['195'],
      url: 'https://ztm.gda.pl/komunikaty/awaryjna-zmiana-trasy-linii-195,a,11936',
    }];
    const hass = {
      states: { 'sensor.x': { attributes: { departures: [], alerts } } },
      callWS: async () => ({ token: null }),
      auth: { data: {} },
    };

    const visible: any = document.createElement('polish-transport-card');
    visible.setConfig({ type: 'custom:polish-transport-card', entities: ['sensor.x'] });
    visible.hass = hass;
    document.body.appendChild(visible);
    await new Promise((resolve) => setTimeout(resolve, 50));
    const enabled = visible.shadowRoot?.querySelector('.alerts')?.textContent || '';

    const hidden: any = document.createElement('polish-transport-card');
    hidden.setConfig({ type: 'custom:polish-transport-card', entities: ['sensor.x'], show_alerts: false });
    hidden.hass = hass;
    document.body.appendChild(hidden);
    await new Promise((resolve) => setTimeout(resolve, 50));
    const disabled = Boolean(hidden.shadowRoot?.querySelector('.alerts'));

    return { enabled, disabled };
  });

  expect(result.enabled).toContain('195');
  expect(result.enabled).toContain('Awaryjna zmiana trasy linii 195');
  expect(result.enabled).toContain('Nieobsługiwane');
  expect(result.disabled).toBe(false);
});
