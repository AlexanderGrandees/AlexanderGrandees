# Vexi access & control model

Vexi evaluates actions on two independent axes. The stricter boundary wins.

## A0-A4 — local/system impact
- **A0** — read/status only.
- **A1** — reversible local UI/session state.
- **A2** — launch/close or bounded local mutation.
- **A3** — meaningful local workflow mutation.
- **A4** — destructive/security/financial/high-impact system action.

Default policy:
- A0/A1: automatic when the target is resolved and verified.
- A2: automatic only for allowlisted personal apps/workflows.
- A3: explicit workflow contract + audit + optional confirmation.
- A4: deny-by-default or mandatory confirmation with preview/rollback where possible.

## W0-W4 — web/account impact
- **W0** — public/read-only navigation and search.
- **W1** — reversible browser/session/player state.
- **W2** — account-scoped reversible mutation.
- **W3** — external communication/publication or meaningful cloud mutation.
- **W4** — financial/security/destructive/purchase/identity-sensitive action.

## Generic objects
The router resolves typed objects rather than raw strings:

`Device, Computer, Monitor, AudioEndpoint, Microphone, Application, Process, Window, Dialog, Browser, Tab, Page, Route, Site, Service, Account, Profile, SearchBox, Query, ResultList, ResultCard, ContentItem, Video, Channel, Playlist, Player, File, Folder, Drive, Archive, Download, Form, Field, Button, Menu, Toggle, Message, Thread, Draft, Comment, Repository, Issue, PullRequest, Commit, Branch, Chart, Symbol, Watchlist, Alert, Order, Transaction, Purchase, SecuritySetting`.

## Generic action vocabulary
`READ, STATUS, LIST, OPEN, CLOSE, FOCUS, MINIMIZE, MAXIMIZE, SELECT, SEARCH, FILTER, SORT, BACK, FORWARD, REFRESH, NEW, NEXT, PREVIOUS, PLAY, PAUSE, RESUME, SEEK, MUTE, UNMUTE, FULLSCREEN, EXIT_FULLSCREEN, GET_PROPERTY, SET_PROPERTY, INCREASE, DECREASE, MULTIPLY, RESTORE, CREATE, EDIT, SAVE, COPY, MOVE, RENAME, TRASH, DELETE, UPLOAD, DOWNLOAD, SEND, PUBLISH, SUBMIT, CONFIRM, CANCEL, LOGIN_FLOW, ACCOUNT_SWITCH, FINANCIAL_ACTION, SECURITY_ACTION`.

Narrative language must be classified before any action verb is allowed to execute.

## Entity roles
A command may contain multiple entities with different semantic roles:
- target;
- source;
- destination;
- container;
- browser;
- site/service;
- query;
- item/card;
- property;
- value/delta;
- account/profile;
- confirmation object.

Example:
`Open Steam Support in Vivaldi` => `resource=steam_support`, `destination_browser=vivaldi`, not two independent app-open actions.

## Adapter priority
Prefer the highest-structure and highest-trust route available:

1. connected service / documented API or connector;
2. service-specific structured browser adapter (DOM/CDP);
3. accessibility / Windows UI Automation;
4. documented deterministic keyboard shortcut after context verification;
5. visual agent fallback.

Coordinate-based clicking is never the generic canonical route.

## Site capability examples

| Vertical | W0 | W1 | W2 | W3 | W4 |
|---|---|---|---|---|---|
| YouTube | open/search/read | player/nav | like/save/subscribe | comment/delete comment | purchases/account security |
| Google Search | open/search | result navigation | — | — | — |
| Gmail | open/read/search | navigation | draft/archive/labels | send/trash | account/security |
| Calendar | open/read | navigation | create/update | delete/respond invite | account/security |
| GitHub | read/search | navigation | create issue | comment/PR | merge/delete repo/secrets |
| Notion | read/search | navigation | create/update page | delete content | schema/destructive ops |
| TradingView | public chart/read | symbol/timeframe/layout | watchlist mutation | alert creation | broker orders |
| Binance | public market data | UI navigation | account read via dedicated adapter | — | orders/withdraw/security |
| Steam Support | browse/read | navigation | — | support ticket | recovery/security |

## PC control verticals

### Window / application
Separate operations:
`OPEN`, `FOCUS`, `MINIMIZE`, `MAXIMIZE`, `CLOSE_WINDOW`, `TERMINATE_PROCESS`, `STATUS`, `PATH`.

### Display
Objects:
`Monitor`, `Brightness`, `HDR`, `Resolution`, `RefreshRate`, `Orientation`, `Topology`, `Wallpaper`.

Brightness should use verified readback where supported. HDR toggle must not be narrated as a verified on/off transition until a reliable state reader is available.

### Audio
Objects:
`MasterVolume`, `Mute`, `AudioEndpoint`, `AppSessionVolume`, `Microphone`.

Master volume/mute can use verified read/set/readback. Endpoint, per-app session, and microphone controls remain separate capabilities.

### Filesystem
Objects:
`File`, `Folder`, `Drive`, `Archive`, `Download`.

Generic file-open permission does not automatically authorize executable/script launch. `.exe`, `.msi`, `.bat`, `.cmd`, `.ps1`, and similar execution surfaces require a dedicated execution route.

### Power / connectivity / devices
`Lock`, `Sleep`, `Shutdown`, `Restart`, `Wi-Fi`, `Bluetooth`, battery/power mode, Quest/XR, and external devices are separate adapters with independent confirmation and state requirements.

## Truth states
Every execution returns exactly one of:

`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

The response layer may never convert `SENT_NOT_CONFIRMED` into a definite success statement.

## Secret-handling boundary
Vexi does not persist or expose passwords, recovery codes, auth tokens, Steam Guard codes, API secrets, or browser credential fields as ordinary memory or model context.
