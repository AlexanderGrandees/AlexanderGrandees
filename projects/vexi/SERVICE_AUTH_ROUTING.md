# Vexi service auth & command routing registry

This document records the universal algorithm Vexi uses to choose between local UI control, independent Browser Packs, native Windows APIs, and official service APIs.

## Universal routing contract

```text
USER COMMAND
-> conservative speech canonicalization
-> current context
-> target service + capability
-> risk / permission gate
-> local / Browser Pack / native provider available?
-> official API route enabled?
-> auth state + required scopes
-> typed execution
-> readback / state verification
-> truthful response
```

Local deterministic routes are preferred for actions on already-visible state. Official APIs are registered separately and are selected only when the route is enabled and its authentication/permission contract is satisfied.

## Auth classes

- `NONE_LOCAL` — no cloud credential; local/native capability.
- `EXTENSION_PERMISSION` — browser-extension permissions only.
- `API_KEY` — application/project key for public API requests.
- `OAUTH_USER` — user-authorized OAuth credential.
- `BOT_TOKEN` — bot identity token.
- `APP_TOKEN` — app/integration token with declared scopes.
- `PARTNER_KEY` — protected publisher/backend key; never ship to desktop clients.

Runtime auth state is metadata only:

`NOT_CONFIGURED | AUTH_REQUIRED | CONNECTED | EXPIRED | PERMISSION_DENIED`

## Secret storage

Beginning with v0.1.3, manual API/token values are entered only through **Settings -> Security** and stored in Windows Credential Manager. Secrets are never accepted by voice, personal memory, LLM prompts, public GitHub, or normal logs. OAuth routes are registered separately; raw OAuth-token paste is not the normal user flow.

## Browser Packs

Browser integration is no longer owned by the Core installer. Each browser uses an independently versioned pack implementing Browser Protocol v1 and living outside `C:\Vexi`.

Current pack IDs / localhost endpoints:

- `vexi.browser.vivaldi` -> 8765
- `vexi.browser.chrome` -> 8766
- `vexi.browser.edge` -> 8767
- `vexi.browser.brave` -> 8768
- `vexi.browser.opera` -> 8769
- `vexi.browser.firefox` -> 8770

All packs expose the same capability contract: active tab, structured page snapshot, text input, element selection, ordered collections and media control. Core updates must not overwrite installed packs.

## Service matrix

### YouTube
- Current-page inspection, search-field typing, visible card selection and native `youtube.com` player control use Browser Pack / DOM automation and require no YouTube Data API key.
- Public YouTube Data API metadata/search can use Google API credentials; private user/account data requires OAuth 2.0.
- The Data API is not a replacement for manipulating the user's already-open YouTube page.
- Canonical UI chain: existing YouTube tab -> snapshot -> SearchBox -> input -> results collection -> select/open -> verify `/watch` -> player context.

### Chromium family / Vivaldi
- Local extension control uses browser permissions, not a cloud API key.
- Tab discovery/manipulation and page content-script access are implemented inside the Browser Pack.

### Windows
- System master volume uses Windows Core Audio.
- Display/HDR/window state use native Windows APIs.
- No cloud API key.

### Steam
- Local client/account-picker/window automation uses a local adapter/UIA; no Web API key is required for that path.
- Optional Web API routes are separately registered. Publisher/partner secrets must never ship in desktop/plugin packages.

### Discord
- Bot operations use a bot token with granted permissions.
- Delegated user authorization uses OAuth2.
- Raw personal-account/self-bot tokens are forbidden.

### Telegram
- Bot API uses a dedicated bot token and controls the bot identity, not the user's personal Telegram Desktop session.
- Personal-client control stays in the local UI/application route.

### GitHub
- Public reads may not require authentication.
- Authenticated API work uses fine-grained PAT, GitHub App or OAuth as appropriate.
- Credentials are treated as secrets and never committed to the repository.

### Notion
- Internal integrations use an integration token.
- Public user-facing integration should use OAuth 2.0.
- Tokens are not accepted in normal chat/voice input.

### Gmail / Google Workspace
- User mailbox access uses OAuth 2.0 with minimum required scopes.
- An API key alone is not the canonical Gmail account-access route.

## Strict v0.1.3 risk profile

Vexi inherits the Intelligence governance and privacy contracts. Capability never implies authorization.

- `A0/W0` and resolved reversible UI/read actions: allowed automatically.
- `A1/W1`: allowed when deterministic and verified.
- `A2/W2`: require a dedicated approval contract; no silent account mutation.
- `A3/W3`: denied in this release.
- `A4/W4`: denied.
- Financial, legal-external, medical, identity/security-sensitive actions: denied.

This intentionally blocks payments, trades/orders, withdrawals, legal filings/submissions, password/2FA/security/permission changes and similar high-responsibility side effects until a separately validated Intelligence/Legal execution policy exists.

## Public documentation references

The architecture follows the service vendors' public documentation: Google/YouTube OAuth and Data API documentation, Chrome Extensions permissions/tabs/scripting documentation, Microsoft Windows Credential Manager/Core Audio documentation, GitHub REST authentication guidance, Notion authorization documentation, Discord OAuth2/bot documentation, Telegram Bot API documentation, and Gmail OAuth documentation.
