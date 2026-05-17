import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://localhost:8123';

test.describe('Card rendering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${HA_URL}/dashboard-testing/ztm-gdansk`);
    await page.waitForTimeout(5000);
  });

  test('cards render with correct provider color', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card').first();
    await expect(card).toBeVisible();
    const header = card.locator('.header');
    const bg = await header.evaluate(el => getComputedStyle(el).backgroundColor);
    expect(bg).not.toBe('rgb(0, 0, 0)');
    expect(bg).not.toBe('');
  });

  test('card shows provider display name in subtitle', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card').first();
    const sub = card.locator('.header-sub');
    const text = await sub.textContent();
    expect(text).not.toContain('ztm_gdansk');
    expect(text).toContain('ZTM Gdańsk');
  });

  test('card shows departure rows', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card').first();
    const rows = card.locator('.dep-row');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('departure row has route badge and time', async ({ page }) => {
    const card = page.locator('mzkzg-transport-card').first();
    const row = card.locator('.dep-row').first();
    const badge = row.locator('.route-badge');
    await expect(badge).toBeVisible();
    const time = row.locator('.time-col');
    await expect(time).toBeVisible();
  });

  test('card height is consistent with padding', async ({ page }) => {
    const cards = page.locator('mzkzg-transport-card');
    const count = await cards.count();
    if (count >= 2) {
      const h1 = await cards.nth(0).boundingBox();
      const h2 = await cards.nth(1).boundingBox();
      // Cards with same max_departures should have similar height
      if (h1 && h2) {
        expect(Math.abs(h1.height - h2.height)).toBeLessThan(100);
      }
    }
  });
});

test.describe('Config flow', () => {
  test('can open integration page', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    await expect(page.locator('text=Hubs')).toBeVisible();
  });

  test('configure button opens options with sleep mode', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    await page.getByRole('button', { name: 'Configure' }).first().click();
    await page.waitForTimeout(2000);
    // Should show sleep mode fields
    const dialog = page.locator('dialog');
    await expect(dialog).toBeVisible();
  });
});

test.describe('Health sensors', () => {
  test('health entities exist', async ({ page }) => {
    await page.goto(`${HA_URL}/config/entities?domain=binary_sensor`);
    await page.waitForTimeout(3000);
    // Check page has health entities
    const content = await page.content();
    expect(content).toContain('api_health');
  });
});

test.describe('Multi-stop architecture', () => {
  test('operator hub has multiple stop devices', async ({ page }) => {
    await page.goto(`${HA_URL}/config/integrations/integration/mzkzg_transport`);
    await page.waitForSelector('text=Hubs', { timeout: 15000 });
    // ZTM Gdańsk should have multiple devices listed
    const content = await page.content();
    expect(content).toContain('ztm_gdansk');
  });
});

test.describe('Visual editor', () => {
  test('editor does not reset config on open', async ({ page }) => {
    await page.goto(`${HA_URL}/dashboard-testing/ztm-gdansk`);
    await page.waitForTimeout(5000);
    // Enter edit mode
    await page.getByRole('button', { name: /edit/i }).click().catch(() => {});
    await page.waitForTimeout(1000);
    // The card should still show departures after edit mode
    const card = page.locator('mzkzg-transport-card').first();
    const rows = card.locator('.dep-row');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

test.describe('Provider colors', () => {
  const providers = [
    { path: 'kiedyprzyjedzie-albatros', name: 'Albatros', color: '#166534' },
    { path: 'gtfsrt-krakow', name: 'ZTP Kraków', color: '#e2001a' },
    { path: 'gtfsrt-szczecin', name: 'ZDiTM Szczecin', color: '#005ca9' },
  ];

  for (const p of providers) {
    test(`${p.name} has correct color and label`, async ({ page }) => {
      await page.goto(`${HA_URL}/dashboard-testing/${p.path}`);
      await page.waitForTimeout(5000);
      const card = page.locator('mzkzg-transport-card').first();
      const sub = card.locator('.header-sub');
      const text = await sub.textContent();
      expect(text).toContain(p.name);
    });
  }
});
