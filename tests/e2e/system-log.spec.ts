import { test } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';

test('system log migration', async ({ page }) => {
  test.setTimeout(120000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });
  await page.goto(`${HA_URL}/lovelace/transport`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  const logs = await page.evaluate(async () => {
    const hass: any = (document.querySelector('home-assistant') as any)?.hass;
    const result = await hass.connection.sendMessagePromise({ type: 'system_log/list' });
    return result
      .filter((e: any) => /migration|mzkzg|PolishTransport|migrate/i.test(`${e.name} ${e.message} ${e.exception || ''}`))
      .slice(-30)
      .map((e: any) => ({ level: e.level, name: e.name, message: e.message, exception: e.exception, source: e.source }));
  });
  console.log(JSON.stringify(logs, null, 2));
});
