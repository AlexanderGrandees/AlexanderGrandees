# Vexi service auth & command routing registry

This document records how Vexi should choose between local UI control, Browser Pack, native Windows APIs, and official service APIs.

## Core routing rule

For each command:

1. Use the current local context first when the user is manipulating what is already visible.
2. Use the structured Browser Pack for active-page observation, text input, element selection, tab state, and media control.
3. Use an official service API when it provides a better structured route for background data, account data, or remote actions.
4. Use native OS APIs for Windows capabilities.
5. Use accessibility/UI Automation only as a fallback when no stable structured route exists.
6. Verify state before reporting success.

## Auth classes

- `NONE_LOCAL` — no cloud credential; local/native capability.
- `EXTENSION_PERMISSION` — browser extension permissions only.
- `API_KEY` — application/project key for public API requests.
- `OAUTH_USER` — user-authorized OAuth token.
- `BOT_TOKEN` — bot identity token.
- `APP_TOKEN` — app/integration token with declared scopes.
- `PARTNER_KEY` — protected publisher/backend key; never ship to desktop clients.

## Service matrix

### YouTube

- Current-page inspection, search-field input, visible video-card selection, and control of the native `youtube.com` player belong to Browser Pack / DOM automation.
- These local browser actions do **not** require a YouTube Data API key.
- The YouTube Data API can be used for structured public metadata/search and requires Google API credentials; private/user-account actions use OAuth 2.0.
- The YouTube IFrame Player API is designed for embedded players controlled by the integrating page and is not the canonical route for controlling YouTube's own website player.
- Default route for commands such as `найди ...`, `открой второе`, `что здесь есть`, `видео тише`, and `видео на весь экран`: Browser Pack first.

### Chromium family / Vivaldi

- `chrome.tabs` is used for tab discovery/manipulation.
- Script injection uses the `scripting` permission plus host permissions or temporary `activeTab` access.
- Vivaldi is Chromium-based and supports Chrome extensions.
- No external API key is required for local browser-extension control.

### Windows

- System master volume: Windows Core Audio / EndpointVolume.
- Display/HDR/window state: native Windows APIs.
- No cloud API key.

### Steam

- Local Steam client/window/account-picker automation: local adapter/UIA; no Steam Web API key required.
- Steam Web API includes public and protected methods; protected methods may require Web API keys.
- Publisher/partner keys belong only on trusted backend infrastructure and must never be included in desktop/plugin packages.

### Discord

- Bot operations: bot token + granted server/channel permissions.
- Acting on behalf of a user: OAuth2 user token with explicit scopes.
- Vexi must never request or use raw personal-account/self-bot tokens.

### Telegram

- Telegram Bot API uses a bot token.
- Bot API controls the bot identity, not the user's personal Telegram desktop session.
- Personal local-client commands remain a UI Automation/local-app capability.

### GitHub

- Some public read endpoints work without auth.
- Authenticated operations use a token, GitHub App token, OAuth app flow, or GitHub CLI auth.
- Prefer GitHub App/OAuth/fine-grained credentials for distributable integrations.

### Notion

- Internal connection: static integration token.
- Public connection: OAuth 2.0; each user authorizes access to their own workspace.
- Public Vexi builds should prefer OAuth and must never ask users to paste secrets into normal chat prompts.

### Gmail / Google Workspace

- Gmail API account access requires OAuth 2.0 authorization.
- API key alone is not the canonical account-access mechanism.
- Request minimum required scopes.

## Secret storage policy

- Vexi may detect whether a credential exists and whether auth works, but never print the secret value.
- Secrets belong in an OS credential store / encrypted plugin credential store.
- Public GitHub contains only auth requirements and scope descriptions, never actual values.
- Runtime status should expose only `NOT_CONFIGURED | AUTH_REQUIRED | CONNECTED | EXPIRED | PERMISSION_DENIED`.

## Command execution protocol

```text
USER COMMAND
-> resolve current context
-> resolve target service + capability
-> choose local / browser / native / official API route
-> check capability permission
-> check auth class + credential status
-> execute
-> read response/state
-> verify expected state
-> speak truthful result
```

## Public-doc references

- YouTube Data API / OAuth: Google Developers.
- YouTube IFrame Player API: Google Developers.
- Chrome Extensions `tabs` / `scripting`: Chrome for Developers.
- Vivaldi extension compatibility: Vivaldi Help.
- Windows Core Audio: Microsoft Learn.
- Steam Web API: Steamworks Documentation.
- Discord OAuth2 and permissions: Discord Developer Docs.
- Telegram Bot API: Telegram Core Docs.
- GitHub REST authentication: GitHub Docs.
- Notion authentication/authorization: Notion Developer Docs.
- Gmail OAuth: Google Developers.
