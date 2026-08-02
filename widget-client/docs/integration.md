# MAAP Widget Client Integration

The Widget Client is a dependency-free, Shadow DOM chat launcher for the
Modern AI Agent Platform. The production bundle uses the existing secure
Widget bootstrap and chat endpoints; it does not expose a tenant API key.

## Production embed

Place the public CDN script before the closing `</body>` tag:

```html
<script
  src="https://cdn.travel-x.online/widget/v1.js"
  data-widget-id="wgt_REPLACE_WITH_ADMIN_GENERATED_ID"
  data-server-url="https://ai.travel-x.online"
  defer
></script>
```

The two embed values are public:

- `data-widget-id` is the opaque identifier generated for one Agent by the
  Admin Widget API.
- `data-server-url` is the API origin. Production requires HTTPS. Local
  development may use `http://localhost` or `http://127.0.0.1`.

Do not put an API key, admin token, tenant ID, internal Agent ID or Widget JWT
in the HTML snippet.

Optional host settings are limited to UI chrome:

```html
<script
  src="https://cdn.travel-x.online/widget/v1.js"
  data-widget-id="wgt_REPLACE_WITH_ADMIN_GENERATED_ID"
  data-server-url="https://ai.travel-x.online"
  data-language="ar"
  data-direction="rtl"
  data-launcher-label="افتح المحادثة"
  defer
></script>
```

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
await window.WidgetAPI.refresh();
window.WidgetAPI.destroy();
```

There is intentionally no public `setConfig()` colour API. Production colours
and Agent identity come from the authenticated Admin configuration and public
bootstrap response.

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
npm run lint
npm run typecheck
npm test
npm run test:coverage
npm run test:visual
npm run build
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
