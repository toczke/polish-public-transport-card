import { test } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';

test('check deployed 2.0 files', async ({ page }) => {
  test.setTimeout(120000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });
  await page.goto(`${HA_URL}/a0d7b954_ssh`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const frame = page.frames().find(f => f.url().includes('hassio_ingress'));
  if (!frame) throw new Error('no terminal frame');
  await frame.locator('.xterm-screen').click();
  await page.keyboard.type("grep -E 'version|CONFIG_ENTRY_VERSION|ENTITY_UNIQUE_PREFIX' /config/custom_components/mzkzg_transport/manifest.json /config/custom_components/mzkzg_transport/const.py; ls -l /config/custom_components/mzkzg_transport/migration.py; echo CHECK_DONE");
  await page.keyboard.press('Enter');
  await page.waitForTimeout(5000);
  const text = await frame.locator('.xterm-rows').innerText().catch(() => 'no rows');
  console.log(text);
  await page.screenshot({ path: 'test-results/deployed-2.0-files.png' });
});
