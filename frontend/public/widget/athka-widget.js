(() => {
  "use strict";

  const script =
    document.currentScript ||
    Array.from(
      document.querySelectorAll(
        "script[data-widget-id]",
      ),
    ).at(-1);

  if (!(script instanceof HTMLScriptElement)) {
    console.error(
      "[Athkachatbots] Loader script element was not found.",
    );
    return;
  }

  const widgetId =
    script.dataset.widgetId?.trim();

  if (
    !widgetId ||
    !/^wgt_[A-Za-z0-9_-]{20,60}$/.test(
      widgetId,
    )
  ) {
    console.error(
      "[Athkachatbots] A valid data-widget-id is required.",
    );
    return;
  }

  const apiBase = (
    script.dataset.apiBase ||
    "https://api.athkachatbots.com"
  ).replace(/\/+$/, "");

  const pairingCode =
    script.dataset.pairingCode
      ?.trim()
      .toUpperCase() || null;

  const instanceId =
    `athka-widget-${widgetId}`;

  if (document.getElementById(instanceId)) {
    return;
  }

  const storageKey =
    `athka-widget-conversation:${widgetId}`;

  const host = document.createElement("div");
  host.id = instanceId;
  host.setAttribute(
    "data-athka-widget",
    widgetId,
  );

  const root = host.attachShadow({
    mode: "open",
  });

  const style =
    document.createElement("style");

  style.textContent = `
    :host {
      --athka-primary: #2563EB;
      --athka-text: #FFFFFF;
      --athka-launcher: #2563EB;
      --athka-header: #2563EB;
      --athka-user: #2563EB;
      --athka-panel: #FFFFFF;
      --athka-surface: #F8FAFC;
      --athka-border: #E2E8F0;
      --athka-input: #FFFFFF;
      --athka-input-text: #111827;
      --athka-bot: #EEF2F7;
      --athka-bot-text: #1F2937;
      all: initial;
      position: fixed;
      z-index: 2147483000;
      font-family:
        Inter,
        "Segoe UI",
        Tahoma,
        Arial,
        sans-serif;
    }

    *,
    *::before,
    *::after {
      box-sizing: border-box;
    }

    button,
    input {
      font: inherit;
    }

    .athka-shell {
      position: fixed;
      right: 22px;
      bottom: 22px;
      z-index: 2147483000;
      direction: rtl;
    }

    .athka-shell.is-left {
      right: auto;
      left: 22px;
    }

    .athka-launcher {
      display: none;
      width: 62px;
      height: 62px;
      place-items: center;
      border: 1px solid rgba(255,255,255,.26);
      border-radius: 999px;
      padding: 0;
      color: var(--athka-text);
      background: var(--athka-launcher);
      box-shadow:
        0 18px 42px rgba(15,23,42,.30);
      cursor: pointer;
      transition:
        transform 160ms ease,
        box-shadow 160ms ease;
    }

    .athka-launcher.is-ready {
      display: grid;
    }

    .athka-launcher:hover {
      transform: translateY(-2px);
      box-shadow:
        0 22px 48px rgba(15,23,42,.34);
    }

    .athka-launcher:focus-visible,
    .athka-close:focus-visible,
    .athka-send:focus-visible,
    .athka-input:focus-visible {
      outline: 3px solid rgba(99,102,241,.28);
      outline-offset: 2px;
    }

    .athka-launcher svg {
      width: 29px;
      height: 29px;
    }

    .athka-panel {
      position: absolute;
      right: 0;
      bottom: 76px;
      display: none;
      width: min(390px, calc(100vw - 28px));
      height: min(620px, calc(100vh - 116px));
      overflow: hidden;
      border: 1px solid var(--athka-border);
      border-radius: 24px;
      background: var(--athka-panel);
      box-shadow:
        0 30px 85px rgba(15,23,42,.28);
      transform-origin: bottom right;
    }

    .athka-shell.is-left .athka-panel {
      right: auto;
      left: 0;
      transform-origin: bottom left;
    }

    .athka-panel.is-open {
      display: grid;
      grid-template-rows: auto minmax(0,1fr) auto;
      animation:
        athka-open 170ms ease-out;
    }

    @keyframes athka-open {
      from {
        opacity: 0;
        transform:
          translateY(8px)
          scale(.985);
      }

      to {
        opacity: 1;
        transform:
          translateY(0)
          scale(1);
      }
    }

    .athka-header {
      display: flex;
      min-height: 72px;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      color: var(--athka-text);
      background: var(--athka-header);
    }

    .athka-identity {
      display: flex;
      min-width: 0;
      align-items: center;
      gap: 11px;
    }

    .athka-avatar {
      display: grid;
      width: 42px;
      height: 42px;
      flex: 0 0 auto;
      place-items: center;
      border-radius: 14px;
      background: rgba(255,255,255,.17);
    }

    .athka-avatar svg {
      width: 22px;
      height: 22px;
    }

    .athka-identity-copy {
      min-width: 0;
    }

    .athka-name,
    .athka-status {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .athka-name {
      font-size: 14px;
      font-weight: 800;
    }

    .athka-status {
      margin-top: 4px;
      font-size: 11px;
      opacity: .86;
    }

    .athka-status::before {
      display: inline-block;
      width: 7px;
      height: 7px;
      margin-inline-end: 5px;
      border-radius: 999px;
      background: #6FF1C2;
      content: "";
    }

    .athka-close {
      display: grid;
      width: 38px;
      height: 38px;
      flex: 0 0 auto;
      place-items: center;
      border: 0;
      border-radius: 11px;
      padding: 0;
      color: inherit;
      background: rgba(255,255,255,.14);
      cursor: pointer;
    }

    .athka-close svg {
      width: 20px;
      height: 20px;
    }

    .athka-messages {
      display: flex;
      min-height: 0;
      flex-direction: column;
      gap: 12px;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 18px 16px;
      background: var(--athka-surface);
      scrollbar-width: thin;
    }

    .athka-message {
      max-width: 86%;
      border-radius: 17px;
      padding: 11px 13px;
      font-size: 14px;
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .athka-message.is-assistant {
      align-self: flex-start;
      border-bottom-left-radius: 5px;
      color: var(--athka-bot-text);
      background: var(--athka-bot);
    }

    .athka-message.is-user {
      align-self: flex-end;
      border-bottom-right-radius: 5px;
      color: var(--athka-text);
      background: var(--athka-user);
    }

    .athka-message.is-error {
      align-self: center;
      max-width: 94%;
      border: 1px solid rgba(239,68,68,.22);
      color: #B91C1C;
      background: #FEF2F2;
      font-size: 12px;
      text-align: center;
    }

    .athka-typing {
      display: inline-flex;
      gap: 4px;
      align-items: center;
      min-height: 12px;
    }

    .athka-typing i {
      width: 6px;
      height: 6px;
      border-radius: 999px;
      background: currentColor;
      opacity: .62;
      animation:
        athka-dot 900ms infinite alternate;
    }

    .athka-typing i:nth-child(2) {
      animation-delay: 140ms;
    }

    .athka-typing i:nth-child(3) {
      animation-delay: 280ms;
    }

    @keyframes athka-dot {
      to {
        opacity: .2;
        transform: translateY(-2px);
      }
    }

    .athka-form {
      display: flex;
      min-height: 72px;
      align-items: center;
      gap: 10px;
      margin: 0;
      padding: 12px;
      border-top: 1px solid var(--athka-border);
      background: var(--athka-panel);
    }

    .athka-input {
      width: 100%;
      min-width: 0;
      height: 46px;
      flex: 1 1 auto;
      border: 1px solid var(--athka-border);
      border-radius: 14px;
      padding: 0 13px;
      color: var(--athka-input-text);
      background: var(--athka-input);
      outline: 0;
      text-align: start;
    }

    .athka-input::placeholder {
      color: #94A3B8;
    }

    .athka-send {
      display: grid;
      width: 46px;
      height: 46px;
      flex: 0 0 46px;
      place-items: center;
      border: 0;
      border-radius: 14px;
      padding: 0;
      color: var(--athka-text);
      background: var(--athka-primary);
      cursor: pointer;
    }

    .athka-send:disabled,
    .athka-input:disabled {
      cursor: wait;
      opacity: .58;
    }

    .athka-send svg {
      width: 19px;
      height: 19px;
    }

    @media (max-width: 520px) {
      .athka-shell {
        right: 14px;
        bottom: 14px;
      }

      .athka-shell.is-left {
        right: auto;
        left: 14px;
      }

      .athka-panel {
        right: 0;
        bottom: 72px;
        width: calc(100vw - 28px);
        height: min(660px, calc(100vh - 100px));
        border-radius: 20px;
      }

      .athka-shell.is-left .athka-panel {
        right: auto;
        left: 0;
      }

      .athka-launcher {
        width: 58px;
        height: 58px;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      *,
      *::before,
      *::after {
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
      }
    }
  `;

  root.appendChild(style);

  const shell =
    document.createElement("div");
  shell.className = "athka-shell";

  const launcher =
    document.createElement("button");
  launcher.className = "athka-launcher";
  launcher.type = "button";
  launcher.setAttribute(
    "aria-label",
    "فتح المحادثة",
  );
  launcher.setAttribute(
    "aria-expanded",
    "false",
  );
  launcher.innerHTML = `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path
        d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"
      ></path>
    </svg>
  `;

  const panel =
    document.createElement("section");
  panel.className = "athka-panel";
  panel.setAttribute(
    "role",
    "dialog",
  );
  panel.setAttribute(
    "aria-label",
    "محادثة المساعد",
  );

  const header =
    document.createElement("header");
  header.className = "athka-header";

  const identity =
    document.createElement("div");
  identity.className = "athka-identity";

  const avatar =
    document.createElement("span");
  avatar.className = "athka-avatar";
  avatar.innerHTML = `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <rect
        x="4"
        y="7"
        width="16"
        height="12"
        rx="3"
      ></rect>
      <path d="M9 11h.01"></path>
      <path d="M15 11h.01"></path>
      <path d="M9 15h6"></path>
      <path d="M12 3v4"></path>
    </svg>
  `;

  const identityCopy =
    document.createElement("span");
  identityCopy.className =
    "athka-identity-copy";

  const name =
    document.createElement("strong");
  name.className = "athka-name";
  name.textContent = "Athkachatbots";

  const status =
    document.createElement("small");
  status.className = "athka-status";
  status.textContent = "جارٍ الاتصال";

  identityCopy.append(
    name,
    status,
  );
  identity.append(
    avatar,
    identityCopy,
  );

  const close =
    document.createElement("button");
  close.className = "athka-close";
  close.type = "button";
  close.setAttribute(
    "aria-label",
    "إغلاق المحادثة",
  );
  close.innerHTML = `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      aria-hidden="true"
    >
      <path d="M18 6 6 18"></path>
      <path d="m6 6 12 12"></path>
    </svg>
  `;

  header.append(
    identity,
    close,
  );

  const messages =
    document.createElement("div");
  messages.className = "athka-messages";
  messages.setAttribute(
    "aria-live",
    "polite",
  );

  const form =
    document.createElement("form");
  form.className = "athka-form";

  const input =
    document.createElement("input");
  input.className = "athka-input";
  input.type = "text";
  input.dir = "auto";
  input.maxLength = 8000;
  input.autocomplete = "off";
  input.placeholder = "اكتب رسالتك...";
  input.setAttribute(
    "aria-label",
    "رسالة المحادثة",
  );
  input.disabled = true;

  const send =
    document.createElement("button");
  send.className = "athka-send";
  send.type = "submit";
  send.setAttribute(
    "aria-label",
    "إرسال",
  );
  send.disabled = true;
  send.innerHTML = `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
    >
      <path d="m22 2-7 20-4-9-9-4Z"></path>
      <path d="M22 2 11 13"></path>
    </svg>
  `;

  form.append(
    input,
    send,
  );
  panel.append(
    header,
    messages,
    form,
  );
  shell.append(
    panel,
    launcher,
  );
  root.appendChild(shell);

  if (document.body) {
    document.body.appendChild(host);
  } else {
    window.addEventListener(
      "DOMContentLoaded",
      () => {
        document.body.appendChild(host);
      },
      { once: true },
    );
  }

  let sessionToken = null;
  let conversationId = null;
  let bootstrapPromise = null;
  let busy = false;
  let configRefreshTimer = null;

  const CONFIG_REFRESH_MS = 15000;

  try {
    conversationId =
      window.sessionStorage.getItem(
        storageKey,
      );
  } catch {
    conversationId = null;
  }

  function setConversationId(value) {
    conversationId = value;

    try {
      if (value) {
        window.sessionStorage.setItem(
          storageKey,
          value,
        );
      } else {
        window.sessionStorage.removeItem(
          storageKey,
        );
      }
    } catch {
      // Session storage is optional.
    }
  }

  function setBusy(value) {
    busy = value;
    input.disabled = value;
    send.disabled = value;

    if (!value) {
      input.focus();
    }
  }

  function scrollMessages() {
    messages.scrollTop =
      messages.scrollHeight;
  }

  function addMessage(role, text) {
    const item =
      document.createElement("div");

    item.className =
      `athka-message is-${role}`;
    item.dir = "auto";
    item.textContent = text;

    messages.appendChild(item);
    scrollMessages();

    return item;
  }

  function addTyping() {
    const item =
      document.createElement("div");

    item.className =
      "athka-message is-assistant";
    item.setAttribute(
      "aria-label",
      "جارٍ إنشاء الرد",
    );

    const typing =
      document.createElement("span");
    typing.className = "athka-typing";

    for (let index = 0; index < 3; index += 1) {
      typing.appendChild(
        document.createElement("i"),
      );
    }

    item.appendChild(typing);
    messages.appendChild(item);
    scrollMessages();

    return item;
  }

  async function readError(response) {
    const payload = await response
      .json()
      .catch(() => null);

    if (
      payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }

    return `HTTP ${response.status}`;
  }

  function themeValue(
    theme,
    camelName,
    snakeName,
    fallback,
  ) {
    const value =
      theme?.[camelName] ??
      theme?.[snakeName];

    return (
      typeof value === "string" &&
      value
    )
      ? value
      : fallback;
  }

  function applyTheme(theme) {
    const primary = themeValue(
      theme,
      "primaryColor",
      "primary_color",
      "#2563EB",
    );

    const textColor = themeValue(
      theme,
      "textColor",
      "text_color",
      "#FFFFFF",
    );

    const launcherColor = themeValue(
      theme,
      "launcherColor",
      "launcher_color",
      primary,
    );

    const headerColor = themeValue(
      theme,
      "headerColor",
      "header_color",
      primary,
    );

    const userColor = themeValue(
      theme,
      "userMessageColor",
      "user_message_color",
      primary,
    );

    const appearance =
      theme?.appearance === "dark"
        ? "dark"
        : "light";

    const position =
      theme?.position === "left"
        ? "left"
        : "right";

    host.style.setProperty(
      "--athka-primary",
      primary,
    );
    host.style.setProperty(
      "--athka-text",
      textColor,
    );
    host.style.setProperty(
      "--athka-launcher",
      launcherColor,
    );
    host.style.setProperty(
      "--athka-header",
      headerColor,
    );
    host.style.setProperty(
      "--athka-user",
      userColor,
    );

    shell.classList.toggle(
      "is-left",
      position === "left",
    );

    if (appearance === "dark") {
      host.style.setProperty(
        "--athka-panel",
        "#171A24",
      );
      host.style.setProperty(
        "--athka-surface",
        "#11141D",
      );
      host.style.setProperty(
        "--athka-border",
        "#2B3040",
      );
      host.style.setProperty(
        "--athka-input",
        "#202432",
      );
      host.style.setProperty(
        "--athka-input-text",
        "#F8FAFC",
      );
      host.style.setProperty(
        "--athka-bot",
        "#272C3A",
      );
      host.style.setProperty(
        "--athka-bot-text",
        "#F1F5F9",
      );
    } else {
      host.style.setProperty(
        "--athka-panel",
        "#FFFFFF",
      );
      host.style.setProperty(
        "--athka-surface",
        "#F8FAFC",
      );
      host.style.setProperty(
        "--athka-border",
        "#E2E8F0",
      );
      host.style.setProperty(
        "--athka-input",
        "#FFFFFF",
      );
      host.style.setProperty(
        "--athka-input-text",
        "#111827",
      );
      host.style.setProperty(
        "--athka-bot",
        "#EEF2F7",
      );
      host.style.setProperty(
        "--athka-bot-text",
        "#1F2937",
      );
    }
  }

  function applyWidgetConfig(widget) {
    if (!widget || typeof widget !== "object") {
      return;
    }

    name.textContent =
      typeof widget.display_name === "string" &&
      widget.display_name.trim()
        ? widget.display_name
        : "Athkachatbots";

    applyTheme(widget.theme);

    const greeting =
      typeof widget.greeting === "string" &&
      widget.greeting.trim()
        ? widget.greeting
        : "??????? ??? ?????? ??????? ??????";

    const hasUserMessage =
      messages.querySelector(
        ".athka-message.is-user",
      );

    if (!hasUserMessage) {
      const first =
        messages.firstElementChild;

      if (
        first &&
        messages.children.length === 1 &&
        first.classList.contains(
          "is-assistant",
        )
      ) {
        first.textContent = greeting;
      } else if (!messages.children.length) {
        addMessage(
          "assistant",
          greeting,
        );
      }
    }
  }

  function stopConfigRefresh() {
    if (configRefreshTimer !== null) {
      window.clearInterval(
        configRefreshTimer,
      );
      configRefreshTimer = null;
    }
  }

  function startConfigRefresh() {
    stopConfigRefresh();

    if (
      document.visibilityState === "hidden"
    ) {
      return;
    }

    configRefreshTimer =
      window.setInterval(
        () => {
          void refreshPublicConfig();
        },
        CONFIG_REFRESH_MS,
      );
  }

  function disableWidgetRuntime() {
    sessionToken = null;

    launcher.classList.remove(
      "is-ready",
    );

    panel.classList.remove(
      "is-open",
    );

    launcher.setAttribute(
      "aria-expanded",
      "false",
    );

    input.disabled = true;
    send.disabled = true;

    status.textContent =
      "??? ????";
  }

  async function loadPublicConfig() {
    const response = await fetch(
        `${apiBase}/api/widget/config`,
        {
          method: "POST",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            widget_id: widgetId,
          }),
        },
    );

    if (!response.ok) {
      const error = new Error(
        await readError(response),
      );
      error.status = response.status;
      throw error;
    }

    const configProof = response.headers.get(
      "X-Widget-Config-Proof",
    );
    if (!configProof) {
      throw new Error(
        "Public config returned no installation proof.",
      );
    }

    const widget = await response.json();
    applyWidgetConfig(widget);
    return {
      widget,
      configProof,
    };
  }

  async function refreshPublicConfig() {
    if (
      document.visibilityState === "hidden"
    ) {
      return;
    }

    try {
      await loadPublicConfig();
    } catch (error) {
      if (error?.status === 403) {
        disableWidgetRuntime();
        stopConfigRefresh();
      } else if (error?.status === 404) {
        disableWidgetRuntime();
      }

      const debug =
        script.dataset.debug === "true";

      if (debug) {
        console.warn(
          "[Athkachatbots] Config refresh failed.",
          error,
        );
      }
    }
  }

  async function bootstrap(force = false) {
    if (sessionToken && !force) {
      return sessionToken;
    }

    if (bootstrapPromise && !force) {
      return bootstrapPromise;
    }

    status.textContent = "جارٍ الاتصال";

    bootstrapPromise = fetch(
      `${apiBase}/api/widget/bootstrap`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type":
            "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          widget_id: widgetId,
        }),
      },
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(
            await readError(response),
          );
        }

        return response.json();
      })
      .then((payload) => {
        if (
          typeof payload.session_token !==
            "string" ||
          !payload.session_token
        ) {
          throw new Error(
            "Bootstrap returned no session token.",
          );
        }

        sessionToken =
          payload.session_token;

        const widget =
          payload.widget ?? {};

        name.textContent =
          typeof widget.display_name ===
            "string" &&
          widget.display_name.trim()
            ? widget.display_name
            : "Athkachatbots";

        applyTheme(widget.theme);

        if (!messages.children.length) {
          addMessage(
            "assistant",
            (
              typeof widget.greeting ===
                "string" &&
              widget.greeting.trim()
            )
              ? widget.greeting
              : "مرحبًا، كيف يمكنني مساعدتك اليوم؟",
          );
        }

        status.textContent = "متصل";
        launcher.classList.add(
          "is-ready",
        );
        input.disabled = false;
        send.disabled = false;

        startConfigRefresh();

        return sessionToken;
      })
      .catch((error) => {
        status.textContent =
          "تعذر الاتصال";

        const debug =
          script.dataset.debug === "true";

        if (debug) {
          console.error(
            "[Athkachatbots] Bootstrap failed.",
            error,
          );
        }

        throw error;
      })
      .finally(() => {
        bootstrapPromise = null;
      });

    return bootstrapPromise;
  }

  async function verifyInstallation(
    token,
    configProof,
  ) {
    if (!pairingCode) {
      return;
    }

    const response = await fetch(
      `${apiBase}/api/widget/connector/verify-installation`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Widget-Config-Proof": configProof,
          Accept: "application/json",
        },
        body: JSON.stringify({
          pairing_code: pairingCode,
        }),
      },
    );

    if (!response.ok) {
      throw new Error(
        `Installation verification failed: ${await readError(response)}`,
      );
    }
  }

  async function initialize() {
    const { configProof } =
      await loadPublicConfig();
    const token = await bootstrap();
    await verifyInstallation(
      token,
      configProof,
    );
  }

  async function sendRequest(
    token,
    message,
  ) {
    const body = {
      message,
    };

    if (conversationId) {
      body.conversation_id =
        conversationId;
    }

    return fetch(
      `${apiBase}/api/chat`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type":
            "application/json",
          Accept: "application/json",
          Authorization:
            `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      },
    );
  }

  async function chat(message) {
    let token = await bootstrap();
    let response =
      await sendRequest(token, message);

    if (response.status === 401) {
      sessionToken = null;
      token = await bootstrap(true);
      response =
        await sendRequest(token, message);
    }

    if (
      response.status === 404 &&
      conversationId
    ) {
      setConversationId(null);
      response =
        await sendRequest(token, message);
    }

    if (!response.ok) {
      throw new Error(
        await readError(response),
      );
    }

    const payload =
      await response.json();

    if (
      typeof payload.conversation_id ===
      "string"
    ) {
      setConversationId(
        payload.conversation_id,
      );
    }

    if (
      typeof payload.reply !== "string" ||
      !payload.reply.trim()
    ) {
      throw new Error(
        "Chat returned an empty reply.",
      );
    }

    return payload.reply;
  }

  function setOpen(open) {
    panel.classList.toggle(
      "is-open",
      open,
    );

    launcher.setAttribute(
      "aria-expanded",
      String(open),
    );

    if (open) {
      input.focus();
    } else {
      launcher.focus();
    }
  }

  launcher.addEventListener(
    "click",
    () => {
      setOpen(
        !panel.classList.contains(
          "is-open",
        ),
      );
    },
  );

  close.addEventListener(
    "click",
    () => {
      setOpen(false);
    },
  );

  form.addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();

      const message =
        input.value.trim();

      if (!message || busy) {
        return;
      }

      input.value = "";
      addMessage(
        "user",
        message,
      );
      setBusy(true);

      const typing = addTyping();

      try {
        const reply =
          await chat(message);

        typing.remove();
        addMessage(
          "assistant",
          reply,
        );
      } catch (error) {
        typing.remove();
        addMessage(
          "error",
          error instanceof Error
            ? error.message
            : "تعذر إرسال الرسالة.",
        );
      } finally {
        setBusy(false);
      }
    },
  );

  document.addEventListener(
    "visibilitychange",
    () => {
      if (
        document.visibilityState === "hidden"
      ) {
        stopConfigRefresh();
        return;
      }

      void refreshPublicConfig();
      startConfigRefresh();
    },
  );

  window.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape" &&
        panel.classList.contains(
          "is-open",
        )
      ) {
        setOpen(false);
      }
    },
  );

  void initialize().catch((error) => {
    console.error(
      "[Athkachatbots] Widget installation failed.",
      error,
    );
  });
})();
