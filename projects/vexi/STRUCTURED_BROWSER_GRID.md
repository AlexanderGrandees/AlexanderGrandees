# Vexi v0.1.2 — Structured Browser Grid

Canonical mechanism:

`Browser Session -> Active Page Snapshot -> Semantic Elements -> Site Mapping -> Entity Resolver -> Typed Action -> Post-action Snapshot -> Verification`

## Horizontal element model

Every supported page may expose:
- `Page / Route`
- `NavigationItem`
- `SearchBox`
- `ResultCard`
- `ContentCard`
- `MediaCard`
- `Channel/ProfileCard`
- `Playlist/CollectionCard`
- `Button / Link / Tab`
- `Dialog / Modal / Menu / MenuItem`
- `Player`
- `Form / Field`
- `Comment / Message / Draft`

Each snapshot element should provide where available:
`element_id, semantic_type, role, text, accessible_name, href, value, visible, rect, position, selected, checked, disabled, container`.

## Action primitives

`LIST_VISIBLE, READ, FIND, FILTER, SELECT, OPEN, CLICK, FOCUS, SEARCH, PLAY, PAUSE, SEEK, SET_PROPERTY, BACK, FORWARD, REFRESH, CLOSE, CONFIRM`.

## Adapter priority
1. Vexi Browser Bridge (local extension + localhost token)
2. CDP when Vexi owns/debug-controls the browser instance
3. Accessibility/UI Automation
4. Visual agent fallback
5. Coordinate-only clicks are non-canonical and should not be used as the primary route.

## Security boundary
Browser Bridge MUST NOT collect cookies, passwords, password-field values, auth tokens, recovery codes or payment credentials. It should expose only visible/semantic page structure required for the requested action.

## Current supported origins in v0.1.2
YouTube, Google Search, GitHub, Gmail, Google Calendar, Notion, TradingView, Steam Support/Store, ChatGPT, Binance. Only YouTube has a deep structured vertical in v0.1.2; the rest use the same bridge foundation for future domain mappings.
