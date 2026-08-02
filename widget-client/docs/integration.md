# MAAP Widget Client Integration

The Widget Client is a dependency-free, Shadow DOM chat launcher for the
Modern AI Agent Platform. The production bundle uses the existing secure
Widget bootstrap and chat endpoints; it does not expose a tenant API key.

## Production embed

Set the public configuration before loading the IIFE bundle:

```html
<script>
  window.WidgetConfig = {
    widgetId: "wgt_REPLACE_WITH_ADMIN_GENERATED_ID",
    apiBaseUrl: "https://ai.travel-x.online",
    language: "ar",
    direction: "rtl"
  };
</script>
<script src="https://cdn.travel-x.online/widget/widget.iife.js" defer></script>
```

The two embed values are public:

- `widgetId` is the opaque identifier generated for one Agent by the
  Admin Widget API.
- `apiBaseUrl` is the API origin. Production requires HTTPS. Local
  development may use `http://localhost` or `http://127.0.0.1`.

Do not put an API key, admin token, tenant ID, internal Agent ID or Widget JWT
in the HTML snippet.

Data attributes are also supported when an embed system cannot emit a config
object:

```html
<script
  src="https://cdn.travel-x.online/widget/widget.iife.js"
  data-widget-id="wgt_REPLACE_WITH_ADMIN_GENERATED_ID"
  data-api-base-url="https://ai.travel-x.online"
  data-language="ar"
  data-direction="rtl"
  data-position="right"
  data-launcher-label="افتح المحادثة"
  defer
></script>
```

`serverUrl` and `data-server-url` are deprecated compatibility aliases. New
embeds must use `apiBaseUrl` or `data-api-base-url`.

## Runtime flow

1. The Widget sends `{ "widget_id": "wgt_..." }` to
   `POST /api/widget/bootstrap`.
2. The Backend verifies the exact browser `Origin`, Widget status, Agent,
   tenant and rate limits.
3. Bootstrap returns a short-lived, origin-bound bearer token and safe public
   presentation data.
4. The Widget applies the trusted Agent name, greeting, colours, position and
   light/dark appearance.
5. Messages are sent to `POST /api/chat` with the in-memory bearer token.
   Agent and tenant IDs are derived from that token, not from browser input.

The token and conversation ID are kept in memory only. The Widget does not
write them to cookies, `localStorage` or `sessionStorage`.

## Per-Agent settings from the Admin UI

The Admin dashboard must load and save settings through the RBAC-protected
endpoint:

```http
GET /api/admin/tenants/{tenant_id}/agents/{agent_id}/widget
PUT /api/admin/tenants/{tenant_id}/agents/{agent_id}/widget
Authorization: Bearer <admin-access-token>
```

Example update body:

```json
{
  "is_enabled": true,
  "display_name": "Customer Support",
  "greeting": "How can we help?",
  "theme": {
    "primaryColor": "#123456",
    "textColor": "#FFFFFF",
    "launcherColor": "#234567",
    "headerColor": "#345678",
    "userMessageColor": "#456789",
    "position": "right",
    "appearance": "light"
  },
  "allowed_origins": ["https://customer.example"]
}
```

`textColor` is applied to text and icons on branded backgrounds. The Backend
rejects invalid colours and combinations that do not meet its WCAG contrast
rule. Customer websites cannot override these trusted per-Agent values through
the production embed.

After an Admin save, a dashboard preview already mounted on an allowed origin
can request the latest configuration with:

```js
await window.WidgetAPI.refresh();
```

## Public JavaScript API

```js
window.WidgetAPI.open();
window.WidgetAPI.close();
await window.WidgetAPI.setConfig({ language: "ar", direction: "rtl" });
await window.WidgetAPI.refresh();
window.WidgetAPI.destroy();
```

`setConfig()` can update safe embed settings such as language, direction,
position, Widget ID and API origin. In production, values inside `mock` are
ignored: colours and Agent identity always come from the trusted bootstrap
response. Changing Widget identity starts a new in-memory session.

## Local UI preview

Mock mode must be selected explicitly and must never be used in a production
embed:

```html
<script>
  window.WidgetConfig = {
    transport: "mock",
    mockScenario: "happy-path",
    mock: {
      displayName: "Preview Assistant",
      welcomeMessage: "This is a local preview.",
      position: "right",
      appearance: "light"
    }
  };
</script>
<script type="module" src="/src/index.ts"></script>
```

## Build and verification

```bash
npm ci
npm run typecheck
npm run lint
npm run lint:css
npm test -- --pool=threads --maxWorkers=1 --minWorkers=1
npm run test:coverage -- --pool=threads --maxWorkers=1 --minWorkers=1
npm run build
npx playwright test
npm audit --audit-level=high
```

Production output:

- `dist/widget.iife.js` for the CDN script.
- `dist/widget.esm.js` for module consumers.
- `dist/index.d.ts` and declarations for TypeScript consumers.

The static Widget bundle should be served from
`https://cdn.travel-x.online/widget/v1.js`; API traffic remains on
`https://ai.travel-x.online`. Cloudflare must not serve an interactive
challenge on the Widget bootstrap or chat browser endpoints.
