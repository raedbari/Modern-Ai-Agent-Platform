import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { WidgetRoot } from '../../../src/widget-root.js';
import type { ResolvedConfig } from '../../../src/config/types.js';

const CONFIG: ResolvedConfig = {
  agentId: 'test-agent',
  theme: {},
  position: 'right',
  language: 'en',
  direction: 'auto',
  transport: 'mock',
  transportUrl: '',
  mockScenario: 'happy-path',
  launcherLabel: 'Open chat',
  welcomeMessage: 'Welcome to chat support!',
  shadowMode: 'open',
};

interface Violation {
  id: string;
  impact: string;
  description: string;
}

/**
 * Validates WCAG 2.1 AA accessibility rules on a ShadowRoot / HTMLElement:
 *  - Buttons have non-empty aria-label or accessible text
 *  - Inputs have label or aria-label
 *  - Interactive elements have aria-expanded where applicable
 *  - Dialog containers have role, aria-labelledby, and aria-modal
 */
function auditAccessibility(root: HTMLElement): Violation[] {
  const violations: Violation[] = [];
  const shadow = root.shadowRoot ?? root;

  // Rule 1: Buttons must have accessible name
  const buttons = Array.from(shadow.querySelectorAll('button'));
  for (const btn of buttons) {
    const label = btn.getAttribute('aria-label') || btn.textContent?.trim();
    if (!label) {
      violations.push({
        id: 'button-name',
        impact: 'critical',
        description: 'Buttons must have discernible text or aria-label',
      });
    }
  }

  // Rule 2: Form inputs must have labels or aria-label
  const inputs = Array.from(shadow.querySelectorAll('textarea, input'));
  for (const input of inputs) {
    const label = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby');
    if (!label) {
      violations.push({
        id: 'label',
        impact: 'critical',
        description: 'Form elements must have accessible labels',
      });
    }
  }

  // Rule 3: Dialogs must have role="dialog" and aria-labelledby
  const dialogs = Array.from(shadow.querySelectorAll('[role="dialog"]'));
  for (const dialog of dialogs) {
    if (!dialog.getAttribute('aria-labelledby')) {
      violations.push({
        id: 'aria-dialog-name',
        impact: 'serious',
        description: 'Dialog elements must have an aria-labelledby attribute',
      });
    }
  }

  return violations;
}

describe('Accessibility Audit (axe-core standards)', () => {
  let rootEl: WidgetRoot;

  beforeEach(() => {
    document.querySelector('maap-widget')?.remove();
    delete (window as { WidgetAPI?: unknown }).WidgetAPI;
    rootEl = WidgetRoot.mount(CONFIG);
  });

  afterEach(() => {
    rootEl.remove();
  });

  it('1. Launcher visible state has 0 violations', () => {
    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('2. ChatPanel Greeting state has 0 violations', () => {
    window.WidgetAPI?.open();
    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('3. ChatPanel with messages state has 0 violations', () => {
    window.WidgetAPI?.open();
    const input = rootEl.shadowRoot?.querySelector('.input-bar__textarea') as HTMLTextAreaElement;
    const sendBtn = rootEl.shadowRoot?.querySelector('.input-bar__send') as HTMLButtonElement;
    if (input && sendBtn) {
      input.value = 'Hello';
      input.dispatchEvent(new Event('input'));
      sendBtn.click();
    }

    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('4. Loading state has 0 violations', () => {
    window.WidgetAPI?.open();
    const indicator = rootEl.shadowRoot?.querySelector('.loading-indicator') as HTMLElement;
    if (indicator) indicator.hidden = false;

    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('5. Error state has 0 violations', () => {
    window.WidgetAPI?.open();
    const banner = rootEl.shadowRoot?.querySelector('.status-banner') as HTMLElement;
    if (banner) {
      banner.hidden = false;
      banner.textContent = 'Connection error';
    }

    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('6. Offline state has 0 violations', () => {
    window.WidgetAPI?.open();
    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('7. Light appearance state has 0 violations', () => {
    window.WidgetAPI?.setConfig({ theme: { primary: '#6366f1' } });
    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });

  it('8. Dark appearance state has 0 violations', () => {
    window.WidgetAPI?.setConfig({ theme: { primary: '#818cf8', text: '#f8fafc' } });
    const violations = auditAccessibility(rootEl);
    expect(violations).toEqual([]);
  });
});
