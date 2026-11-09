import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';
const REF = process.env.HA_REF || '41d435d400156ca4a29ff4cc52a0e31f57582438';

test('deploy city alert scope and inspect attributes', async ({ page, request }) => {
  test.setTimeout(420000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  const headers = { Authorization: `Bearer ${TOKEN}` };
  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });
  await page.goto(`${HA_URL}/a0d7b954_ssh`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const frame = page.frames().find((f) => f.url().includes('hassio_ingress'));
  if (!frame) throw new Error('no terminal frame');
  await frame.locator('.xterm-screen').click();
  const cmd = [
    'cd /config',
    'rm -rf /tmp/pptc /tmp/pptc.zip',
    `wget -q -O /tmp/pptc.zip https://github.com/toczke/polish-public-transport-card/archive/${REF}.zip`,
    'unzip -q -o /tmp/pptc.zip -d /tmp/pptc',
    `cp -a /tmp/pptc/polish-public-transport-card-${REF}/custom_components/mzkzg_transport/. /config/custom_components/mzkzg_transport/`,
    'ha core restart',
  ].join(' && ');
  await page.keyboard.type(cmd);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(12000);
  let up = false;
  for (let i = 0; i < 120; i += 1) {
    try {
      const ping = await request.get(`${HA_URL}/api/`, { headers, timeout: 5000 });
      if (ping.ok()) { up = true; break; }
    } catch { /* restarting */ }
    await new Promise((r) => setTimeout(r, 2000));
  }
  expect(up).toBe(true);
  await page.waitForTimeout(20000);

  const resp = await request.get(`${HA_URL}/api/states/sensor.plocka_01_odjazdy`, { headers, timeout: 30000 });
  const state = await resp.json();
  const attrs = state.attributes || {};
  console.log('ALERTS', JSON.stringify(attrs.alerts || []));
  console.log('CITY_ALERTS', JSON.stringify(attrs.alerts_city || []));
  expect(Array.isArray(attrs.alerts_city)).toBe(true);
  expect(attrs.alerts_city.some((alert: any) => (alert.lines || []).includes('195'))).toBe(true);
});
