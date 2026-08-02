# Widget Client Integration Guide

The `@maap/widget-client` package provides an isolated, zero-dependency, Shadow DOM embeddable chat widget for the Modern AI Agent Platform.

---

## 🚀 Quick Start (Script Embed)

Add the IIFE bundle to any HTML page before the closing `</body>` tag:

```html
<script>
  window.WidgetConfig = {
    agentId: "agent-sales-01",
    launcherLabel: "Chat with Sales Support",
    welcomeMessage: "Hello! How can we assist your business today?",
    theme: {
      primary: "#4f46e5",
      headerBg: "#3730a3"
    }
  };
</script>
<script src="https://cdn.example.com/widget.iife.js" defer></script>
```

Alternatively, pass JSON configuration via `data-widget-config`:

```html
<script
  src="https://cdn.example.com/widget.iife.js"
  data-widget-config='{"agentId":"agent-sales-01","position":"right"}'
  defer
></script>
```

---

## ⚙️ Configuration Parameters (`WidgetConfig`)

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `agentId` | `string` | `""` | **Recommended**. Identifier of the agent to connect to. |
| `theme` | `Partial<ThemeTokens>` | `{}` | Theme colour token overrides (hex, rgb, hsl). |
| `position` | `"left"` \| `"right"` | `"right"` | Corner placement on screen. |
| `language` | `string` | `"en"` | BCP-47 language code. |
| `direction` | `"ltr"` \| `"rtl"` \| `"auto"` | `"auto"` | Text direction mode (auto-detects page dir). |
| `transport` | `"mock"` \| `"websocket"` \| `"sse"` | `"mock"` | Transport strategy. Wave 1 supports `"mock"`. |
| `transportUrl` | `string` | `""` | Target backend URL for real transports. |
| `mockScenario` | `"happy-path"` \| `"slow-response"` \| `"error-response"` \| `"stream-error-midway"` | `"happy-path"` | Active mock scenario. |
| `launcherLabel` | `string` | `"Open chat"` | Accessible ARIA label for floating launcher button. |
| `welcomeMessage` | `string` | `"Hello! How can I help you today?"` | Message displayed on greeting screen. |
| `shadowMode` | `"open"` \| `"closed"` | `"open"` | Shadow DOM encapsulation mode. |

---

## 🎨 Theme Tokens

The widget uses scoped CSS Custom Properties (`--wc-*`):

```typescript
interface ThemeTokens {
  primary: string;        // Primary brand colour (--wc-primary)
  text: string;           // Base text colour (--wc-text)
  launcherBg: string;     // Launcher button background (--wc-launcher-bg)
  headerBg: string;       // Chat panel header background (--wc-header-bg)
  userBubbleBg: string;   // User message bubble background (--wc-user-bubble-bg)
}
```

---

## 💻 Public JavaScript API (`window.WidgetAPI`)

Once mounted, `window.WidgetAPI` exposes 4 control methods:

```typescript
// Open the chat panel
window.WidgetAPI.open();

// Close the chat panel
window.WidgetAPI.close();

// Update configuration at runtime
window.WidgetAPI.setConfig({
  launcherLabel: "Help Center",
  theme: { primary: "#059669" }
});

// Tear down widget and remove element from DOM
window.WidgetAPI.destroy();
```

---

## 🛠️ Production Build Command

To compile the production IIFE and ESM bundles with sourcemaps:

```bash
npm run build
```

Outputs created in `dist/`:
- `dist/widget.iife.js`
- `dist/widget.esm.js`
- `dist/index.d.ts`

---

## ♿ Manual WCAG Testing Note

The widget complies with **WCAG 2.1 Level AA**:
- Keyboard navigation (Tab/Shift+Tab focus wrapping in modal, Escape key close).
- All interactive elements have minimum **44px × 44px** touch target bounds.
- Accessible ARIA live regions for assistant streaming text updates.
