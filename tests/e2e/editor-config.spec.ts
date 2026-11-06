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

test('editor exposes actions, new filters and per-sensor controls', async ({ page }) => {
  await page.goto('about:blank');
  await page.addScriptTag({ path: SCRIPT });
  const result = await page.evaluate(async () => {
    const editor: any = document.createElement('polish-transport-card-editor');
    editor.setConfig({
      entities: [
        { entity: 'sensor.one', max_departures: 3 },
        { entity: 'sensor.two' },
      ],
      min_departures: 20,
      max_departures: 10,
      header_style: 'custom',
      header_color: 'not-a-color',
    });
    editor.hass = { language: 'pl', states: { 'sensor.one': { attributes: { stop_name: 'Dworzec Główny' } } } };
    document.body.appendChild(editor);
    await editor.updateComplete;
    await new Promise((r) => setTimeout(r, 50));
    const forms = [...editor.shadowRoot.querySelectorAll('ha-form')];
    const names = (form: any) => (form?.schema || []).flatMap((s: any) => s.schema || [s]).map((s: any) => s.name);
    const globalNames = names(forms[0]);
    const overrideNames = names(forms[1]);
    return {
      globalNames,
      overrideNames,
      options: [...editor.shadowRoot.querySelectorAll('select option')].map((o: any) => o.textContent.trim()),
      buttons: [...editor.shadowRoot.querySelectorAll('.override-actions button')].map((b: any) => b.textContent.trim()),
      validation: editor.shadowRoot.querySelector('.validation')?.textContent.trim() || '',
    };
  });
  expect(result.globalNames).toEqual(expect.arrayContaining([
    'tap_action', 'hold_action', 'double_tap_action', 'columns', 'show_refresh',
    'max_minutes', 'only_low_floor', 'only_bike', 'only_ac', 'only_ticket_machine',
    'view_mode',
  ]));
  expect(result.overrideNames).toEqual(expect.arrayContaining([
    'max_minutes', 'only_low_floor', 'only_bike', 'only_ac', 'only_ticket_machine',
  ]));
  expect(result.options[0]).toBe('Dworzec Główny — one');
  expect(result.buttons.length).toBe(3);
  expect(result.validation).toContain('Min. odjazdów');
  expect(result.validation).toContain('Kolor nagłówka');
});
