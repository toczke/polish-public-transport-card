import { test } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';

test('inspect after 2.0 migration', async ({ page }) => {
  test.setTimeout(120000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });
  await page.goto(`${HA_URL}/lovelace/transport`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(5000);
  const info = await page.evaluate(async () => {
    const hass: any = (document.querySelector('home-assistant') as any)?.hass;
    const entries = await hass.connection.sendMessagePromise({ type: 'config_entries/get' });
    const devices = await hass.connection.sendMessagePromise({ type: 'config/device_registry/list' });
    const entities = await hass.connection.sendMessagePromise({ type: 'config/entity_registry/list' });
    const ours = entries.filter((e: any) => e.domain === 'mzkzg_transport');
    const ids = new Set(ours.map((e: any) => e.entry_id));
    const ourDevices = devices.filter((d: any) => (d.config_entries || []).some((id: string) => ids.has(id)));
    const ourEntities = entities.filter((e: any) => e.config_entry_id && ids.has(e.config_entry_id));
    return {
      entries: ours.map((e: any) => ({ id: e.entry_id, title: e.title, version: e.version, unique_id: e.unique_id, stops: (e.data?.stops || []).length, state: e.state })),
      operatorDevices: ourDevices.filter((d: any) => !d.via_device_id).map((d: any) => ({ name: d.name, identifiers: d.identifiers })),
      stopDeviceCount: ourDevices.filter((d: any) => d.via_device_id).length,
      entities: ourEntities.map((e: any) => ({ id: e.entity_id, unique_id: e.unique_id, platform: e.platform })),
      hasMzkzgEntity: ourEntities.some((e: any) => e.entity_id.includes('mzkzg')),
    };
  });
  console.log(JSON.stringify(info, null, 2));
});
