import { test } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';

test('backup, deploy 2.0 migration, verify', async ({ page, request }) => {
  test.setTimeout(420000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  const headers = { Authorization: `Bearer ${TOKEN}` };

  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });
  await page.goto(`${HA_URL}/a0d7b954_ssh`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const frame = page.frames().find(f => f.url().includes('hassio_ingress'));
  if (!frame) throw new Error('no terminal frame');
  await frame.locator('.xterm-screen').click();
  const stamp = Date.now();
  const cmd = [
    'cd /config',
    `mkdir -p /config/backup-2.0-${stamp}`,
    `cp .storage/core.config_entries .storage/core.device_registry .storage/core.entity_registry .storage/core.restore_state /config/backup-2.0-${stamp}/`,
    'rm -rf /tmp/pptc /tmp/pptc.zip',
    'wget -q -O /tmp/pptc.zip https://github.com/toczke/polish-public-transport-card/archive/refs/heads/release/2.0.0.zip',
    'unzip -q -o /tmp/pptc.zip -d /tmp/pptc',
    'cp -a /tmp/pptc/polish-public-transport-card-release-2.0.0/custom_components/mzkzg_transport/. /config/custom_components/mzkzg_transport/',
    'ha core restart',
  ].join(' && ');
  await page.keyboard.type(cmd);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(12000);

  let up = false;
  for (let i = 0; i < 100; i += 1) {
    try {
      const ping = await request.get(`${HA_URL}/api/`, { headers, timeout: 5000 });
      if (ping.ok()) { up = true; break; }
    } catch { /* restarting */ }
    await new Promise((r) => setTimeout(r, 2000));
  }
  console.log('UP', up, 'BACKUP', `/config/backup-2.0-${stamp}`);
  if (!up) return;

  await page.goto(`${HA_URL}/lovelace/transport`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(6000);
  const info = await page.evaluate(async () => {
    const hass: any = (document.querySelector('home-assistant') as any)?.hass;
    const entries = await hass.connection.sendMessagePromise({ type: 'config_entries/get' });
    const devices = await hass.connection.sendMessagePromise({ type: 'config/device_registry/list' });
    const entities = await hass.connection.sendMessagePromise({ type: 'config/entity_registry/list' });
    const ours = entries.filter((e: any) => e.domain === 'mzkzg_transport');
    const ids = new Set(ours.map((e: any) => e.entry_id));
    const ourDevices = devices.filter((d: any) => (d.config_entries || []).some((id: string) => ids.has(id)));
    const ourEntities = entities.filter((e: any) => e.config_entry_id && ids.has(e.config_entry_id));
    const operatorDevices = ourDevices.filter((d: any) => !d.via_device_id);
    const stopDevices = ourDevices.filter((d: any) => d.via_device_id);
    return {
      entries: ours.map((e: any) => ({ id: e.entry_id, title: e.title, version: e.version, unique_id: e.unique_id, stops: (e.data?.stops || []).length })),
      operatorDevices: operatorDevices.map((d: any) => ({ id: d.id, name: d.name, identifiers: d.identifiers })),
      stopDevices: stopDevices.map((d: any) => ({ name: d.name, identifiers: d.identifiers, via: d.via_device_id })),
      entities: ourEntities.map((e: any) => ({ id: e.entity_id, unique_id: e.unique_id, device: e.device_id, platform: e.platform })),
      hasMzkzgEntity: ourEntities.some((e: any) => e.entity_id.includes('mzkzg')),
    };
  });
  console.log(JSON.stringify(info, null, 2));
  await page.screenshot({ path: 'test-results/2.0-migration.png' });
});
