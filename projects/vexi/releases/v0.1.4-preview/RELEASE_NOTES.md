# Vexi v0.1.4 Public Preview

Release date: 2026-09-13

## Included public components
- Vexi Core v0.1.4 (`public-preview`, build `media-context-natural-control`).
- Browser Protocol v1.
- Chrome Browser Pack v0.1.2 in the third-party bundle.
- Vivaldi Browser Pack v0.1.2 as the field-proven primary-machine browser pack.

## Field evidence carried into this release
- Core v0.1.3 previously reached READY on Windows.
- Core v0.1.4 is now installed and version-confirmed on the primary Windows machine.
- Browser Pack registry and extension heartbeat work through Browser Protocol v1.
- Vivaldi Browser Pack v0.1.2 returned a fresh YouTube HOME snapshot with one search box and three visible video cards.
- `открой второе видео` returned `CONFIRMED_SUCCESS` and opened the second visible card.
- `весь экран` returned `CONFIRMED_SUCCESS` for the YouTube player.

## v0.1.4 Core changes
- Media target priority over generic window/system control while a player context is active.
- Active browser-surface observation foundation: active page/tab plus visible semantic objects.
- Compound browser command planning for flows such as `открой YouTube и скажи что видишь`.
- Browser selection can fall back to an actually installed browser instead of only hard-defaulting to Vivaldi.
- Plugin manifests accept legacy UTF-8 BOM and manifest parse failures are logged.
- High-risk financial, irreversible and security-sensitive actions remain denied.

## Browser Pack v0.1.2 changes
- UTF-8 BOM registration issue from v0.1.0 is fixed in the v0.1.1+ installer path.
- Local Browser Protocol v1 bridge/service.
- Manifest V3 browser extension.
- Structured active-tab snapshots.
- Resilient YouTube video-card extraction using current `/watch` links and multiple renderer/view-model fallbacks.
- Semantic video-card ordering, deduplication, title/channel extraction and diagnostics.

## Known open issues
- Natural fullscreen-OFF phrases still need broader Core routing coverage. `сверни это видео` was observed to route to generic window minimize instead of player fullscreen OFF.
- Some short audio phrases are still classified as conversation even though the Windows audio backend itself is working.
- Exact v0.1.4 Core + Chrome Browser Pack v0.1.2 combination is not yet promoted to Stable; it still needs a real third-party Windows/Chrome field test.
- macOS support is architecture/planning only and is not part of this release.

## Validation performed before packaging
- Python compile check: PASS.
- Core v0.1.4 regression script: PASS in the build environment.
- Chrome extension JavaScript syntax check: PASS.
- Chrome manifest JSON validation: PASS.

## Release status
**Public Preview**, not Stable.

Promotion requires representative clean-install evidence plus the critical browser/media regression matrix.
