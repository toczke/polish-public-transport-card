import { test, expect } from '@playwright/test';
import { createHash } from 'crypto';

const HA_URL = process.env.HA_URL || 'http://192.168.0.11:8123';
const TOKEN = process.env.HA_TOKEN || '';

test('deploy non-clickable static rows and verify', async ({ page, request }) => {
  test.setTimeout(180000);
  test.skip(!TOKEN, 'HA_TOKEN not set');
  await page.addInitScript(({ token, base }) => {
    localStorage.setItem('hassTokens', JSON.stringify({ access_token: token, token_type: 'Bearer', refresh_token: '', expires_in: 315360000, expires: Date.now() + 315360000000, hassUrl: base, clientId: `${base}/` }));
  }, { token: TOKEN, base: HA_URL });

  await page.goto(`${HA_URL}/a0d7b954_ssh`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(5000);
  const frame = page.frames().find(f => f.url().includes('hassio_ingress'));
  if (!frame) throw new Error('no terminal frame');
  await frame.locator('.xterm-screen').click();
  const cmd = [
    'cd /config',
    'rm -rf /tmp/pptc /tmp/pptc.zip',
    'wget -q -O /tmp/pptc.zip https://github.com/toczke/polish-public-transport-card/archive/refs/heads/release/1.7.0.zip',
    'unzip -q -o /tmp/pptc.zip -d /tmp/pptc',
    'cp -a /tmp/pptc/polish-public-transport-card-release-1.7.0/custom_components/mzkzg_transport/. /config/custom_components/mzkzg_transport/',
    'echo STATIC_ROWS_DEPLOY_DONE',
  ].join(' && ');
  await page.keyboard.type(cmd);
  await page.keyboard.press('Enter');
  await page.waitForTimeout(18000);

  const bundle = await request.get(`${HA_URL}/polish_transport/polish-transport-card.js`);
  const hash = createHash('sha1').update(await bundle.body()).digest('hex').slice(0, 10);
  const url = `/polish_transport/polish-transport-card.js?v=1.7.0-${hash}`;
  await page.goto(`${HA_URL}/lovelace/transport`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.evaluate(async ({ url }) => {
    const hass: any = (document.querySelector('home-assistant') as any)?.hass;
    const list = await hass.connection.sendMessagePromise({ type: 'lovelace/resources/list' });
    const item = list.find((r: any) => (r.url || '').includes('/polish_transport/polish-transport-card.js'));
    if (item && item.url !== url) {
      await hass.connection.sendMessagePromise({ type: 'lovelace/resources/update', resource_id: item.id, res_type: 'module', url });
    }
  }, { url });

  await page.reload({ waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(4000);

  const data = await page.evaluate(async () => {
    const deepAll = (root: Document | ShadowRoot, selector: string): any[] => {
      const out = [...root.querySelectorAll(selector)];
      for (const el of root.querySelectorAll('*')) if ((el as any).shadowRoot) out.push(...deepAll((el as any).shadowRoot, selector));
      return out;
    };
    const card = deepAll(document, 'polish-transport-card')[0] as any;
    const deps = card._getDepartures();
    const rows = [...card.shadowRoot.querySelectorAll('.dep-row')] as HTMLElement[];
    let mismatches = 0;
    let staticRows = 0;
    let staticUnclickable = 0;
    for (let i = 0; i < Math.min(rows.length, deps.length); i += 1) {
      const d = deps[i];
      const hasPos = d.vehicle_lat != null && d.vehicle_lng != null &&
        Number.isFinite(Number(d.vehicle_lat)) && Number.isFinite(Number(d.vehicle_lng));
      const interactive = rows[i].classList.contains('interactive');
      if (hasPos) {
        if (!interactive) mismatches += 1;
      } else {
        staticRows += 1;
        if (!interactive && rows[i].getAttribute('tabindex') === '-1') staticUnclickable += 1;
        if (interactive) mismatches += 1;
      }
    }
    let moreInfo = 0;
    card.addEventListener('hass-more-info', () => { moreInfo += 1; });
    const firstStatic = rows.find((r, i) => {
      const d = deps[i];
      return !(d?.vehicle_lat != null && d?.vehicle_lng != null);
    });
    firstStatic?.click();
    await new Promise((r) => setTimeout(r, 350));
    return { resource: null, rows: rows.length, staticRows, staticUnclickable, mismatches, moreInfo };
  });
  console.log(JSON.stringify(data));
  await page.screenshot({ path: 'test-results/deployed-static-rows.png' });
  expect(data.mismatches).toBe(0);
  expect(data.staticRows).toBeGreaterThan(0);
  expect(data.staticUnclickable).toBe(data.staticRows);
  expect(data.moreInfo).toBe(0);
});
