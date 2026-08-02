import { test, expect } from '@playwright/test';

test.describe('Widget Visual Regression Baselines', () => {
  test('1. Launcher closed baseline', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('maap-widget')).toBeVisible();
    await expect(page).toHaveScreenshot('launcher-closed.png');
  });

  test('2. ChatPanel Greeting baseline', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => window.WidgetAPI?.open());
    await expect(page).toHaveScreenshot('chatpanel-greeting.png');
  });

  test('3. ChatPanel with messages baseline', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.WidgetAPI?.open();
    });
    const widget = page.locator('maap-widget');
    await widget.locator('textarea').fill('Hello!');
    await widget.locator('.input-bar__send').click();
    await page.waitForTimeout(500);
    await expect(page).toHaveScreenshot('chatpanel-messages.png');
  });

  test('4. ChatPanel RTL baseline', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      document.documentElement.setAttribute('dir', 'rtl');
      window.WidgetAPI?.open();
    });
    await expect(page).toHaveScreenshot('chatpanel-rtl.png');
  });

  test('5. ChatPanel dark appearance baseline', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.WidgetAPI?.setConfig({
        theme: { primary: '#818cf8', text: '#f8fafc', headerBg: '#1e293b' },
      });
      window.WidgetAPI?.open();
    });
    await expect(page).toHaveScreenshot('chatpanel-dark.png');
  });
});
