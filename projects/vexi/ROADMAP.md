# Vexi roadmap

## Current state
- Proven active primary Windows Core: **v0.1.4 Public Preview**.
- Proven primary browser pack: **Vivaldi Browser Pack v0.1.2**, Browser Protocol v1.
- Proven structured YouTube snapshot: active page metadata + visible `VideoCard[]` extraction.
- Proven ordinal card selection: `открой второе видео` -> `CONFIRMED_SUCCESS`.
- Proven player fullscreen ON: `весь экран` -> `CONFIRMED_SUCCESS`.
- Open regression: natural player fullscreen OFF / media-vs-window target resolution.
- Chrome Browser Pack v0.1.2 + Core v0.1.4 bundle: packaged, awaiting third-party Windows/Chrome field validation.
- macOS: architecture planned; no macOS runtime release yet.

## Immediate validation — v0.1.4
1. Complete a clean third-party Windows install of Core v0.1.4.
2. Complete Chrome Browser Pack v0.1.2 install and extension activation on that PC.
3. Confirm Browser Pack registry, bridge service, extension heartbeat and active-page snapshot.
4. Confirm YouTube `search_box` plus visible `video` semantic objects in Chrome.
5. Confirm `открой первое/второе видео` against the active collection.
6. Confirm player fullscreen ON and OFF with natural phrases.
7. Confirm player volume/mute and system volume/mute are separated by target scope.
8. Confirm active-surface questions such as `что видишь?` / `какая вкладка активна?` are routed consistently.
9. Confirm compound flow `открой YouTube и скажи что видишь` executes as a plan rather than stopping after the first action.
10. Confirm normal user-mode runtime versus elevated Windows-control capability behavior and document exactly which operations require elevation, if any.

## Core routing hardening
- Explicit semantic object scope must outrank generic verbs: `video` -> player, `browser/window` -> window, `system/laptop` -> OS control.
- Add robust `OBSERVE_ACTIVE_SURFACE`, `GET_ACTIVE_TAB`, `LIST_VISIBLE_OBJECTS` routing.
- Persist short-lived media state: current player, current collection, selected media, fullscreen, volume/mute, last target.
- Expand natural audio phrases without turning approximate terms into unsafe fuzzy matches.
- Preserve `REPORT` / `CONVERSATION` as non-executable unless a command intent is explicitly present.
- One intent -> one execution -> one result -> one spoken response.

## Browser platform roadmap
### Generic structured page layer
Use one protocol/skill surface across browser families:

`snapshot -> semantic objects -> resolve -> act -> verify`

Current proven vertical: YouTube on Vivaldi.

Next validation target: same YouTube flow on Chrome, then a second site vertical.

Candidate second verticals:
- Google Search result cards;
- GitHub repositories/issues/PRs;
- Gmail threads/messages;
- Notion pages/databases/views;
- TradingView controls;
- Steam Support product/ticket cards.

### Browser state
- active tab title + URL;
- list tabs;
- switch tab by semantic target;
- close target tab;
- tab/page verification;
- structured dialogs/modals/menus/forms;
- re-inject/reload content script safely after Browser Pack upgrades without requiring manual page refresh where browser policy permits.

## YouTube roadmap
### Proven
- Home visible-card enumeration.
- Open by ordinal from the active visible collection.
- Visible title/channel extraction.
- Player fullscreen ON.

### Next
- Full SearchBox input flow through the active existing YouTube tab.
- Search-results collection refresh and verification.
- Open by title/channel with confidence scoring.
- Player fullscreen OFF natural-language coverage.
- Player volume/mute with readback.
- Play/pause/seek/speed/captions/current-time queries.
- Channel/profile resolution.
- Playlist/Shorts/history/subscriptions support.
- Current video title/channel/status queries.

### Account mutation
- Like/save/subscribe require explicit W2 policy + post-action verification if enabled in a future profile.
- Comments/publishing remain W3 and require explicit intent + confirmation.
- Purchases, memberships, financial operations, account security and other high-responsibility actions remain denied in the current profile.

## Windows control roadmap
### Audio
- master volume/mute verified baseline;
- output device selection;
- per-application session volume;
- microphone level/mute;
- restore previous value/state;
- diagnose user-mode vs elevated behavior per capability.

### Display
- brightness read/set/readback;
- verified HDR state reader + on/off control;
- wallpaper set/read/restore;
- monitor topology;
- resolution / refresh rate / orientation with stronger confirmation.

### Windows and application control
- stable window inventory;
- move/snap/resize windows;
- multi-monitor placement;
- intermediate-dialog resolver;
- Steam account picker based on UI Automation / structured UI state.

### Filesystem
- typed search/open/create/copy/move/rename/trash/archive;
- recent downloads/documents;
- safe preview + verification for mutations;
- executable/script launch remains a separate permission surface.

## Platform roadmap — macOS
Goal: keep one shared semantic Core while replacing Windows-only adapters with a platform layer.

Planned split:
- shared Router / memory / browser protocol / site verticals;
- macOS audio adapter (CoreAudio);
- macOS accessibility/window adapter;
- macOS Keychain secret store;
- LaunchAgent / Service Management runtime startup;
- microphone + Accessibility permissions as explicit onboarding;
- Chrome Browser Pack reuse where possible;
- signed/notarized `Vexi.app` + DMG for public distribution.

Initial macOS target should prioritize Apple Silicon and avoid claiming Windows-only HDR/display behavior until native adapters exist.

## Device fabric
Future adapters:
- Bluetooth / Wi-Fi status and bounded controls;
- battery / power mode;
- phone/tablet integration;
- Meta Quest / Oculus device state and supported workflows;
- audio endpoints/displays.

## Memory roadmap
- durable confirmed preferences;
- candidate-preference inference with confidence thresholds;
- user review/correction/forget controls;
- explicit no-store zones;
- encrypted-at-rest option for local durable memory;
- never store credentials/tokens/recovery secrets as generic memory.

## Release discipline
- PATCH: bug/path/recovery changes without contract changes.
- MINOR: new tool/app/site class or backward-compatible routing behavior.
- MAJOR: permission semantics, memory/privacy schema, action meaning, or new execution surface requiring migration.

No release is considered promoted only because the package built successfully. Promotion requires representative field evidence and regression results.
