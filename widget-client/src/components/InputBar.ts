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
    this.#counter.setAttribute('aria-live', 'polite');
    this.#counter.setAttribute('aria-atomic', 'true');
    this.#counter.hidden = true;

    // ── Send button ───────────────────────────────────────────────────────
    this.#sendBtn = document.createElement('button');
    this.#sendBtn.className = 'input-bar__send';
    this.#sendBtn.type = 'button';
    this.#sendBtn.setAttribute('aria-label', 'Send message');
    this.#sendBtn.textContent = '➤';
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

  static styles(): string {
    return `
      .input-bar {
        border-block-start: 1px solid #e2e8f0;
        padding: 0.75rem;
        background: #fff;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }
      .input-bar__row {
        display: flex;
        align-items: flex-end;
        gap: 0.5rem;
      }
      .input-bar__textarea {
        flex: 1;
        resize: none;
        border: 1px solid #cbd5e1;
        border-radius: 0.5rem;
        padding: 0.5rem 0.75rem;
        font-size: 0.9rem;
        font-family: inherit;
        line-height: 1.5;
        max-block-size: 8rem;
        overflow-y: auto;
        outline: none;
        transition: border-color 0.15s;
      }
      .input-bar__textarea:focus {
        border-color: var(--wc-primary, #6366f1);
      }
      .input-bar__send {
        flex-shrink: 0;
        inline-size: 2.5rem;
        block-size: 2.5rem;
        border: none;
        border-radius: 50%;
        background: var(--wc-primary, #6366f1);
        color: #fff;
        cursor: pointer;
        font-size: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: opacity 0.15s, transform 0.1s;
      }
      .input-bar__send:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .input-bar__send:not(:disabled):hover {
        transform: scale(1.05);
      }
      .input-bar__counter {
        font-size: 0.75rem;
        color: #f59e0b;
        text-align: end;
      }
      .input-bar__counter--critical {
        color: #dc2626;
        font-weight: 600;
      }
    `;
  }
}
