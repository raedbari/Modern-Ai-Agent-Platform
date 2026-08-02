import { test, expect } from '@playwright/test';

test.describe('Widget browser presentation', () => {
  test('launcher uses the chat-bubble shape', async ({ page }) => {
    await page.goto('/');
    const widget = page.locator('maap-widget');
    const launcher = widget.locator('.launcher-button');

    await expect(widget).toBeVisible();
    await expect(launcher).toBeVisible();
    await expect(launcher).toHaveAttribute('aria-expanded', 'false');
    await expect(launcher).toHaveCSS('width', '60px');
    await expect(launcher).toHaveCSS('height', '60px');

    const corners = await launcher.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        topLeft: style.borderTopLeftRadius,
        bottomRight: style.borderBottomRightRadius,
      };
    });
    expect(Number.parseFloat(corners.topLeft)).toBeGreaterThan(
      Number.parseFloat(corners.bottomRight),
    );
  });

  test('panel opens with the trusted greeting presentation', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => window.WidgetAPI?.open());
    const widget = page.locator('maap-widget');

    await expect(widget.locator('.chat-panel')).toBeVisible();
    await expect(widget.locator('.panel-header__title')).toHaveText(
      'MAAP Assistant',
    );
    await expect(widget.locator('.greeting-message')).toHaveText(
      'Hello! This is the local Widget preview.',
    );
    await expect(widget.locator('.greeting-screen')).toBeVisible();
    await expect(widget.locator('.message-list')).toBeHidden();
    await expect(widget.locator('.loading-indicator')).toBeHidden();
    await expect(widget.locator('.chat-panel')).toHaveCSS(
      'border-radius',
      '24px',
    );
  });

  test('message bubbles render with opposite logical tails', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => window.WidgetAPI?.open());
    const widget = page.locator('maap-widget');
    await widget.locator('textarea').fill('Hello!');
    await widget.locator('.input-bar__send').click();
    const userMessage = widget.locator('.message-bubble--user');
    const assistantMessage = widget.locator('.message-bubble--assistant');

    await expect(userMessage).toHaveText('Hello!');
    await expect(assistantMessage).toContainText(
      "Sure, I'd be happy to help you with that!",
    );
    await expect(widget.locator('.greeting-screen')).toBeHidden();
    await expect(widget.locator('.message-list')).toBeVisible();
    await expect(widget.locator('.loading-indicator')).toBeHidden();

    const radii = await Promise.all([
      userMessage.evaluate(
        (element) => getComputedStyle(element).borderBottomRightRadius,
      ),
      assistantMessage.evaluate(
        (element) => getComputedStyle(element).borderBottomLeftRadius,
      ),
    ]);
    expect(radii.map(Number.parseFloat)).toEqual([5.6, 5.6]);
  });

  test('host direction changes are reflected in the isolated widget', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      document.documentElement.setAttribute('dir', 'rtl');
      window.WidgetAPI?.open();
    });
    await expect(page.locator('maap-widget')).toHaveAttribute('dir', 'rtl');
  });

  test('dark appearance applies the dark surface tokens', async ({ page }) => {
    await page.addInitScript(() => {
      window.WidgetConfig = {
        transport: 'mock',
        mock: {
          appearance: 'dark',
          theme: {
            primary: '#60A5FA',
            onPrimary: '#FFFFFF',
            launcherBg: '#2563EB',
            headerBg: '#1D4ED8',
            userBubbleBg: '#2563EB',
          },
        },
      };
    });
    await page.goto('/');
    await page.evaluate(() => window.WidgetAPI?.open());
    const widget = page.locator('maap-widget');

    await expect(widget).toHaveAttribute('data-appearance', 'dark');
    await expect(widget.locator('.chat-panel')).toHaveCSS(
      'background-color',
      'rgb(17, 24, 39)',
    );
  });
});
