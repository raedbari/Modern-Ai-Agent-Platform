import { createIcon, ICON_PATHS } from '../utils/icons.js';

const MAX_CHARS = 4_000;
const WARN_CHARS = 3_200;

export interface InputBarCallbacks {
  onSend(text: string): void;
}

/**
 * InputBar — chat input area with send button.
 *
 * Features:
 *  - Textarea is always editable (inputEditable is always true per spec)
 *  - Send button is disabled when sendDisabled is true or input is empty
 *  - Enter sends, Shift+Enter inserts newline
 *  - Hard 4000-character limit with warning display at >3200 chars
 *  - Exposes part="input-bar" for host CSS customisation
 */
export class InputBar {
  readonly #root: HTMLElement;
  readonly #textarea: HTMLTextAreaElement;
  readonly #sendBtn: HTMLButtonElement;
  readonly #counter: HTMLElement;
  readonly #callbacks: InputBarCallbacks;
  #sendDisabled = false;

  constructor(callbacks: InputBarCallbacks, placeholder = 'Type a message…') {
    this.#callbacks = callbacks;

    this.#root = document.createElement('div');
    this.#root.className = 'input-bar';
    this.#root.setAttribute('part', 'input-bar');

    // ── Textarea ──────────────────────────────────────────────────────────
    this.#textarea = document.createElement('textarea');
    this.#textarea.className = 'input-bar__textarea';
    this.#textarea.placeholder = placeholder;
    this.#textarea.rows = 1;
    this.#textarea.maxLength = MAX_CHARS;
    this.#textarea.setAttribute('aria-label', 'Message');
    this.#textarea.setAttribute('aria-multiline', 'true');

    this.#textarea.addEventListener('input', () => this.#onInput());
    this.#textarea.addEventListener('keydown', (e) => this.#onKeydown(e));

    // ── Character counter ─────────────────────────────────────────────────
    this.#counter = document.createElement('span');
    this.#counter.className = 'input-bar__counter';
    this.#counter.hidden = true;

    // ── Send button ───────────────────────────────────────────────────────
    this.#sendBtn = document.createElement('button');
    this.#sendBtn.className = 'input-bar__send';
    this.#sendBtn.type = 'button';
    this.#sendBtn.setAttribute('aria-label', 'Send message');
    this.#sendBtn.appendChild(
      createIcon('input-bar__send-icon', [...ICON_PATHS.send]),
    );
    this.#sendBtn.disabled = true; // Enabled only when there's text and send is allowed

    this.#sendBtn.addEventListener('click', () => this.#submit());

    // ── Layout ────────────────────────────────────────────────────────────
    const inputRow = document.createElement('div');
    inputRow.className = 'input-bar__row';
    inputRow.appendChild(this.#textarea);
    inputRow.appendChild(this.#sendBtn);

    this.#root.appendChild(this.#counter);
    this.#root.appendChild(inputRow);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  /** Update whether the send button should be blocked. */
  setSendDisabled(disabled: boolean): void {
    this.#sendDisabled = disabled;
    this.#updateSendButton();
  }

  focus(): void {
    this.#textarea.focus();
  }

  // ─── Private ─────────────────────────────────────────────────────────────

  #onInput(): void {
    const len = this.#textarea.value.length;

    // Auto-resize textarea
    this.#textarea.style.blockSize = 'auto';
    this.#textarea.style.blockSize = `${this.#textarea.scrollHeight}px`;

    // Character counter
    if (len > WARN_CHARS) {
      const remaining = MAX_CHARS - len;
      this.#counter.textContent = `${remaining} character${remaining === 1 ? '' : 's'} remaining`;
      this.#counter.hidden = false;
      this.#counter.classList.toggle('input-bar__counter--critical', remaining <= 100);
    } else {
      this.#counter.hidden = true;
    }

    this.#updateSendButton();
  }

  #onKeydown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.#submit();
    }
  }

  #submit(): void {
    const text = this.#textarea.value.trim();
    if (!text || this.#sendDisabled) return;

    this.#callbacks.onSend(text);
    this.#textarea.value = '';
    this.#textarea.style.blockSize = 'auto';
    this.#counter.hidden = true;
    this.#updateSendButton();
  }

  #updateSendButton(): void {
    const hasText = this.#textarea.value.trim().length > 0;
    this.#sendBtn.disabled = this.#sendDisabled || !hasText;
  }
}
