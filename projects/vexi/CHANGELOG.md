# Vexi changelog

All dates use Europe/Berlin local date unless noted otherwise.

## 2026-09-13 — v0.1.3 release candidate
### Plugin Kernel, Security UI & YouTube Automation
- Split browser integration out of Core into independent per-browser packs using Browser Protocol v1.
- Added Browser Pack v0.1.0 candidates for Vivaldi, Chrome, Edge, Brave, Opera and Firefox.
- Added universal service/auth route selection: context -> capability -> policy -> provider -> auth -> execution -> verification.
- Added Windows Credential Manager secret storage and local Settings tabs for Assistant / Plugins / Security.
- Secret values are UI-only; voice/prompt/memory/log/public-doc secret ingestion is blocked.
- Added strict high-risk policy profile: material communication plus financial/legal/security-sensitive side effects are denied; reversible account mutation requires a dedicated approval contract.
- Added full assistant rename: the new user-defined name replaces both display and wake identity. Recovery remains available through Settings UI.
- Added conservative Speech Canonicalizer with capability-family/context gating and local explicit-correction memory.
- Added YouTube current-page-first chain: reuse existing tab, structured SearchBox input, result collection, ordinal/title/channel/spatial selection, verified video transition and player-scoped control.
- Separated media/player fullscreen and volume from browser fullscreen and Windows master volume.
- Core updates preserve installed Browser Pack directories/plugin manifests.

### Pre-package validation
- Core Python compile: PASS.
- `regression_tests_v013.py`: PASS.
- Six Browser Pack Python payloads: compile PASS.
- Chromium/Firefox extension JavaScript: `node --check` PASS.
- Browser Pack command-queue deterministic regression: PASS.
- Windows laptop field validation is still required before promotion.

### v0.1.3 candidate hashes
- Core: `9eed77be7f6939b35ddab9526ec059c2fb03028cff17bf7bd11e776a31a80b4e`
- Vivaldi Pack: `71f6ce3a4e8a24e115c1dfe46a83cc8e501064b2805b48c55110b239caee76a4`
- Chrome Pack: `01cda7f9cc7740348a0f0055ad020b275c4f1aedfa0bff9b493a63109af241c7`
- Edge Pack: `ed68281852ad08387bd0f2fad6fa2632d4589d503c6ad247157943b559f09c85`
- Brave Pack: `135d49012ff024ff76bb1af663542f9599dee69b96a082bcdc83e12787b70624`
- Opera Pack: `216a18d1c40127b5aecd41988703bff9337d3380410c737a5762f2914323eadc`
- Firefox Pack: `efc7483eb8e75569a061c33bc0aa6c6e338421c6d4e58fced05634ecf9cc93f2`
- All Packs bundle: `e5a3f6fafaef4e1e77015a967521f1cd71d4e14742d6557d5c0f3022f0ed06fa`

## 2026-09-13 — v0.1.2 candidate
### Structured Browser Control & Barge-In
- Added local Browser Bridge runtime + Manifest V3 extension foundation for Chromium-family browsers.
- Added semantic active-page snapshots and generic `find -> resolve -> select -> verify` automation.
- Added YouTube visible-card enumeration and selection by ordinal/title/channel/spatial reference when Browser Bridge is connected.
- Added structured HTML5 media control foundation: play/pause/seek/volume/rate/mute and YouTube-specific fullscreen/captions/next/miniplayer actions where available.
- Added interruptible TTS / barge-in test implementation with adaptive echo guard.
- Added occasional-name policy; routine confirmations should not prepend the owner name.
- Production startup target changed to hidden `pythonw.exe`; debug console remains explicit.
- Tray/overlay/log/voice are designed to expose the canonical `v0.1.2 • test` identity.
- Installer removes stale Vexi/Jarvis launchers, preserves rollback, and requires runtime identity evidence before promotion.

### Installer revision r1 — failed
- Added persistent installer logging and transactional rollback after the first update attempt left v0.1.1 active.
- Added package syntax checks before stopping the working runtime.
- Added explicit `version.py == 0.1.2` validation and `Vexi v0.1.2 ready` promotion evidence.
- **Field result:** Windows PowerShell 5.1 parser failure inside `install_v012.ps1`; runtime was not promoted.

### Installer revision r2 — failed preflight
- Removed the r1 nested inline `python -c` version-detection quoting.
- Added installer syntax preflight before touching the working runtime.
- **Field result:** batch caret escaping (`^|`) reached PowerShell literally; preflight itself failed with `Unexpected token '^'`.
- Safety result: the existing v0.1.1 installation was not modified.

### Installer revision r3 — current candidate
- Replaced inline `powershell -Command` syntax parsing with dedicated `preflight_v012.ps1`.
- Preflight reports parser line/column and returns a stable non-zero exit code.
- Hardened UAC relaunch quoting for installer paths.
- Runtime payload remains v0.1.2; r3 changes installer reliability only.
- **Field result:** v0.1.2 subsequently reached runtime on the laptop and logged `BrowserBridge ready` plus canonical `Vexi v0.1.2 ready`; structured page routing still required architectural completion.

### v0.1.2 package hashes
- base candidate: `6ec9c68b0673cc4c99694c6e5d4a782cd967e573635ce3cb928a2e137a3845e7`
- installer r1: `59ea2af4eb81c46c215c2cf410c6422fff5b25321ecbd6a881e3acaa21c39600`
- installer r2: `d6532e0a576a8890db488ba7ecac05f9f869b72fe2549a6839edc53459e1f8fc`
- installer r3: `64fecd8b7d819a1c3f20a3e680036f5f4e8af90aa60166fcf4307bd4fcf188fe`

## 2026-09-13 — v0.1.1
### Control Foundation
First real semantic release.

- Introduced router/control/memory foundation.
- Added Windows audio/display/filesystem adapters.
- Added application/window state operations.
- Added initial deterministic YouTube navigation.
- Added local personal memory/onboarding.
- Added truth-preserving execution states.

Field evidence:
- YouTube direct open worked when routing reached `OPEN_SITE`.
- System master-volume backend passed direct read/set/readback/restore testing.
- Natural audio-language routing remained incomplete.
- Explorer process-vs-window state remained unreliable.
- Vivaldi launch/focus worked but fullscreen-preserving focus and active-tab truth required hardening.

## 2026-09-13 — legacy lab lineage
Historical experiment labels only; not public product versions.

- Lab 4.0: local STT + female Silero TTS + application/browser control foundation.
- Lab 4.1: Steam/application safety, microphone recovery, minimize/maximize/focus/close verification work.
- Lab 4.2: routing/filler-word experiments and browser/site parsing.
- Lab 4.3: intent-parser regression testing; exposed `OPEN_STT_ALIASES` and live-patch failures.
- Lab 4.4/4.4.1: architecture work that was later normalized into semantic versions v0.1.1+.

See [INCIDENTS.md](INCIDENTS.md) for dated failure details.