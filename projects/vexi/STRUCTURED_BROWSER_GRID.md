# Vexi Structured Browser Grid — Core v0.1.4 / Browser Protocol v1

Canonical mechanism:

`Browser Session -> Active Page Snapshot -> Semantic Elements -> Site Mapping -> Entity Resolver -> Typed Action -> Post-action Snapshot -> Verification`

## Current component line
- Core: `v0.1.4 Public Preview`
- Browser Protocol: `v1`
- Vivaldi Browser Pack: `v0.1.2`, field-proven on the primary machine
- Chrome Browser Pack: `v0.1.2`, packaged for third-party validation

Core and Browser Packs are independently versioned and installed.

## Horizontal element model

Every supported page may expose:
- `Page / Route`
- `NavigationItem`
- `SearchBox`
- `ResultCard`
- `ContentCard`
- `MediaCard / VideoCard`
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

`OBSERVE_ACTIVE_SURFACE, GET_ACTIVE_TAB, LIST_VISIBLE, READ, FIND, FILTER, SELECT, OPEN, CLICK, FOCUS, SEARCH, PLAY, PAUSE, SEEK, SET_PROPERTY, BACK, FORWARD, REFRESH, CLOSE, CONFIRM`.

## Adapter priority
1. Vexi Browser Pack (local extension + localhost Browser Protocol service)
2. CDP when Vexi owns/debug-controls the browser instance
3. OS accessibility tree / UI Automation
4. visual-agent fallback
5. coordinate-only clicks are non-canonical and should not be the primary route.

## Browser Pack health contract
A Browser Pack is not considered ready merely because files exist.

Promotion/health checks:

```text
plugin manifest readable by Core
-> pack service healthy
-> extension heartbeat connected
-> normal web page active
-> fresh page snapshot
-> semantic element count > 0 where expected
-> site-specific regression passes
```

Diagnostics should expose:
- registry present;
- manifest encoding/BOM state;
- pack/service version + protocol;
- extension connection;
- site/page type/URL/title;
- snapshot age;
- semantic element counts;
- representative structured objects.

## Confirmed field evidence — YouTube / Vivaldi
Browser Pack v0.1.2 produced:

```text
installed: true
extension_connected: true
site: youtube
page_type: HOME
snapshot_age: ~0.65s
snapshot_elements: 4
semantic_types:
  search_box: 1
  video: 3
```

The visible video objects included ordered positions, titles and channels from the active viewport.

Subsequent Core execution confirmed opening the second visible video and player fullscreen ON.

## Current-page-first rule
For supported web actions, prefer the already-open active/known site context:

```text
existing supported tab?
-> observe
-> resolve target object
-> use generic skill
-> act
-> verify
```

Opening a new site/tab is a fallback when no usable existing site context exists.

## Security boundary
Browser Pack MUST NOT collect cookies, passwords, password-field values, auth tokens, recovery codes or payment credentials. It should expose only page structure required for the requested action.

Protected internal browser pages such as `chrome://...` or `vivaldi://...` are not normal content-script targets and may correctly return no semantic snapshot.

## Site support model
Known origins/capability targets include YouTube, Google Search, GitHub, Gmail, Google Calendar, Notion, TradingView, Steam Support/Store, ChatGPT and Binance.

Only YouTube currently has field-proven deep structured interaction. Other origins should not be advertised as equivalent until their own semantic verticals and regression matrices are implemented and validated.
