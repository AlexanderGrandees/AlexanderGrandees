# Vexi v0.1.2 — Capability / Access Grid

## Versioning
`v0.1.2` is the current semantic release candidate. Earlier `3.x / 4.x` names remain historical lab-build labels only.

## Horizontal capability primitives
These primitives are reusable across every vertical and should be implemented once rather than as site-specific phrase patches.

| Horizontal | Meaning | Default risk | Verification requirement |
|---|---|---:|---|
| ACTIVATE | wake/session/text activation | A0 | activation state |
| RESOLVE_ENTITY | app/site/file/device/resource resolution | A0 | deterministic target + trust tier |
| READ_STATE | read process/window/tab/property/device state | A0 | direct readback |
| OPEN | open app/site/file/folder/resource | A1/A2 | resulting window/resource when possible |
| FOCUS | foreground existing object | A1 | foreground HWND/object |
| NAVIGATE | back/forward/tab/page/service route | A1 | structured state when available |
| SEARCH | web/site/local search | A0/A1 | query sent + destination |
| MEDIA | play/pause/seek/fullscreen/captions/speed | A1 | player state when structured adapter exists |
| PROPERTY | get/set/increase/decrease/restore numeric state | A1/A2 | read → set → readback |
| FILE_MUTATION | create/copy/move/rename/trash | A2/A3 | source/destination verification |
| ACCOUNT_MUTATION | subscribe/like/save/edit account data | A2/A3 | explicit user intent + resulting state |
| COMMUNICATE | send/comment/publish/submit | A3 | explicit user intent + preview/receipt |
| FINANCIAL | order/purchase/withdraw/trade | A4 | blocked or mandatory confirmation + dedicated adapter |
| SECURITY | credentials/recovery/security state | A4 | blocked by default; secrets never stored |

## Web access tiers
- **W0** — public/read-only navigation and search.
- **W1** — reversible session/UI state.
- **W2** — account-scoped reversible mutation; explicit command required.
- **W3** — external communication/publication or meaningful account mutation; explicit intent + verification.
- **W4** — financial/security/destructive/purchase/identity-sensitive; confirmation or blocked by default.

## Vertical map
| Vertical | W0 | W1 | W2 | W3 | W4 |
|---|---|---|---|---|---|
| YouTube | open/search/read | player/nav | like/save/subscribe | comment/delete comment | purchases/account security |
| Google Search | open/search | result navigation | — | — | — |
| Gmail | open/read/search | navigation | draft/archive/labels | send/trash | account/security |
| Calendar | open/read | navigation | create/update | delete/respond invite | account/security |
| GitHub | read/search | navigation | create issue | comment/PR | merge/delete repo/secrets |
| Notion | read/search | navigation | create/update page | delete content | schema/destructive ops |
| TradingView | public chart/read | symbol/timeframe/layout | watchlist local mutation | alert creation | broker orders |
| Binance | public market data | UI navigation | account read via dedicated adapter | — | orders/withdraw/security |
| Steam Support | browse/read | navigation | — | support ticket | recovery/security |

## Runtime execution states
`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

A planned capability in a registry is **not executable** until an adapter exposes it. The LLM cannot narrate planned capabilities as completed actions.

## Horizontal vs vertical rule
A vertical may define domain semantics, objects and allowed workflows. It must not reimplement generic window, browser, permission, memory, property, file or verification logic.

Example: YouTube defines `Video / Channel / Player`; it reuses generic `OPEN / SEARCH / MEDIA / PROPERTY / VERIFY` primitives.

## v0.1.2 additions
- StructuredPageAdapter / Browser Bridge foundation.
- YouTube visible-card selection when extension is connected.
- Structured media state where an HTML5 video element is accessible.
- Barge-in / interruptible TTS test mode with adaptive echo guard.
- Runtime identity/version menu/voice query contract.
- Production no-console startup through direct `pythonw.exe` path.
