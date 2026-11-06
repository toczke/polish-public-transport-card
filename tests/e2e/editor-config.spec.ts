import { test, expect } from '@playwright/test';
import * as path from 'path';

const SCRIPT = path.resolve('custom_components/mzkzg_transport/www/polish-transport-card.js');

test('editor shows global form and per-sensor override form', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await page.evaluate(async () => {
    const editor: any = document.createElement('polish-transport-card-editor');
    editor.setConfig({
      entities: [
        { entity: 'sensor.one', filter_routes: ['6'] },
        'sensor.two',
      ],
    });
    editor.hass = { language: 'pl', states: {} };
    document.body.appendChild(editor);
    await editor.updateComplete;
    await new Promise((r) => setTimeout(r, 50));
    return {
      forms: editor.shadowRoot.querySelectorAll('ha-form').length,
      options: [...editor.shadowRoot.querySelectorAll('select option')].map((o: any) => o.value),
      selected: editor.shadowRoot.querySelector('select')?.value,
      globalEntities: editor.shadowRoot.querySelector('ha-form')?.data?.entities,
    };
  });
  expect(result.forms).toBe(2);
  expect(result.options).toEqual(['sensor.one', 'sensor.two']);
  expect(result.selected).toBe('sensor.one');
  expect(result.globalEntities).toEqual(['sensor.one', 'sensor.two']);
});
