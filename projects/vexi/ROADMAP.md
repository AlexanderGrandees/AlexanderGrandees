# Vexi roadmap

## Current state
- Proven active semantic release: **v0.1.1**.
- Current candidate: **v0.1.2 r3**.
- v0.1.2 is not promoted until field evidence confirms the installed runtime identity and critical browser/TTS regression matrix.

## Immediate validation — v0.1.2
1. Installer r3 preflight passes on Windows PowerShell 5.1.
2. Update transaction preserves rollback and promotes only after runtime-ready evidence.
3. `version.py`, tray, overlay, startup log, diagnostics, and voice version query all agree on `v0.1.2`.
4. Normal startup/autostart leaves no console window visible.
5. Debug launch intentionally exposes a console.
6. Structured Browser Bridge connects to the user's existing Vivaldi profile.
7. YouTube Home and Search Results expose visible semantic cards.
8. Exact/high-confidence card selection opens the intended video and verifies the resulting route/page.
9. Ambiguous card matches ask a short clarification instead of guessing.
10. Barge-in interrupts Vexi speech quickly while avoiding persistent self-echo interruption.
11. Routine confirmations do not repeatedly address the user by name.

## Reliability hardening after v0.1.2
- Explorer real-window verification.
- Browser fullscreen/maximized preservation during focus.
- Typed context commit only after confirmed or explicitly intermediate action states.
- One intent -> one execution -> one result -> one spoken response.
- Natural numeric property language across volume/brightness/zoom/media.
- Better STT correction constrained by known entities and command context.
- Microphone recovery with bounded retry/backoff/device re-selection.

## Browser platform roadmap
### Generic structured page layer
Prove the same `snapshot -> resolve -> select -> verify` interface on at least one second site beyond YouTube.

Candidate verticals:
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
- structured dialogs/modals/menus/forms.

## YouTube roadmap
- Home/Search visible-card enumeration.
- Open by title/channel/ordinal/spatial reference.
- Channel/profile resolution.
- Playlist/Shorts support.
- `Continue watching` section semantics when structurally visible.
- Verified player state.
- Play/pause/seek/fullscreen/captions/speed/volume/rate.
- Current video title/channel/status queries.
- Account mutations (like/save/subscribe) only after explicit W2 policy + post-action verification.
- Comments/publishing remain W3 and require explicit intent.

## Windows control roadmap
### Audio
- master volume/mute verified baseline;
- output device selection;
- per-application session volume;
- microphone level/mute;
- restore previous value/state.

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