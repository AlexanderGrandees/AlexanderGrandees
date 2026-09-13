# Vexi changelog

All dates use Europe/Berlin local date unless noted otherwise.

## 2026-09-13 - v0.1.4 Public Preview
### Media Context & Natural Control
- Promoted Core semantic version to `0.1.4`, channel `public-preview`, build `media-context-natural-control`.
- Added media-target priority so explicit/current YouTube player context outranks generic window/system routing.
- Added active-surface observation foundations for active tab/page and visible YouTube video lists.
- Added compound browser-command planning for flows such as `открой YouTube и скажи что видишь`.
- Added browser selection fallback to an actually installed browser instead of hard-defaulting only to Vivaldi.
- Added BOM-tolerant plugin-manifest loading plus parse-error logging.
- Kept high-risk financial, irreversible and security-sensitive actions denied by policy.
- Packaged a third-party Windows + Chrome bundle containing Core v0.1.4 and Chrome Browser Pack v0.1.2.

### Primary-machine field evidence
- `C:\Vexi\version.py` confirmed `__version__ = "0.1.4"`.
- Vivaldi Browser Pack v0.1.2 reported `installed=true`, `extension_connected=true`, `site=youtube`, `page_type=HOME` and a sub-second snapshot age.
- Structured snapshot returned one `search_box` plus three visible `video` objects with titles/channels from the active YouTube viewport.
- Voice command `открой второе видео` returned `CONFIRMED_SUCCESS` and selected `Autumn Rain | 8 Hours of soft rain for Relaxation & Meditation 8 часов`.
- Voice command `весь экран` returned `CONFIRMED_SUCCESS` for the YouTube player.
- Remaining routing defect: `сверни это видео` was incorrectly routed to generic window `MINIMIZE`, and `убери видео с полноэкранного режима` was not consistently recognized. This remains open for fullscreen-OFF/media-scope hardening.

### Browser Pack v0.1.1 - registry repair
- Fixed plugin manifests written by Windows PowerShell 5.1 with UTF-8 BOM (`EF BB BF`).
- v0.1.0 could physically install the pack/extension while Core reported `browser_pack_not_installed` because the manifest JSON parse error was silently skipped.
- v0.1.1 writes UTF-8 without BOM, validates Core registration and exposes bridge/extension diagnostics.

### Browser Pack v0.1.2 - YouTube extractor repair
- Confirmed bridge service and extension heartbeat through Browser Protocol v1.
- Reworked YouTube card extraction to discover current `/watch` links and newer renderer/view-model structures instead of depending only on legacy `#video-title` selectors.
- Added deduplication by YouTube video id, viewport ordering, title/channel extraction fallbacks and richer diagnostics.
- Field result on Vivaldi: `search_box: 1`, `video: 3` with real visible titles/channels.
- Chrome v0.1.2 uses the same structured YouTube extraction logic and is packaged for third-party field testing.

### Windows control field note
- Natural command `выключи звук на ноуте` returned `CONFIRMED_SUCCESS` when the runtime was launched elevated on the primary machine.
- Earlier variants such as `выключим звук на ноуте` / `звук на ноль` were classified as conversation, confirming that semantic phrase normalization still needs expansion independent of the working audio backend.
- Elevation helping on this setup is treated as a permission/integrity observation, not a universal runtime requirement.

### v0.1.4 / Browser Pack artifact hashes
- Public Preview Chrome bundle: `0b86e358bc9779abc51f8d5d5066809c733a8b46648a315dde677d5e916fe96b`
- Core v0.1.4 Public Preview: `ae098a7218c3dd4b43ad36c8eb6a8e5d933bdf72e06da0e7ab8f9aa8cb99978c`
- Chrome Browser Pack v0.1.2: `0dacf43ec7fee5a11cbb5d40d6adf0b4650aa0424e2b329de3d04015da7667b3`
- Vivaldi Browser Pack v0.1.2: `f40a84127b119652d6369c88c0f00c9eeb7be08005d626faaf659c5c772fab0c`

### Validation before packaging
- Python compile: PASS.
- Core v0.1.4 regression script: PASS in the build environment.
- Chrome extension JavaScript syntax: PASS.
- Chrome manifest JSON validation: PASS.
- Exact Core v0.1.4 + Chrome Pack v0.1.2 combination remains **Public Preview** until a real third-party Windows/Chrome field test completes.

## 2026-09-13 - v0.1.3 Public Preview
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

### Core field result
- Core v0.1.3 installed on the primary Windows laptop and logged canonical `Vexi v0.1.3 ready` evidence.
- STT `small / cpu / int8` reached ready state.
- Silero TTS `xenia` reached ready state.
- The observed two `pythonw.exe` entries were one virtual-environment launcher process plus its base Python child, not two independent Vexi runtimes.

### Installer completion incident
- The original v0.1.3 updater reached runtime `READY` but its non-elevated launcher window remained on `requesting administrator permission...`.
- Root cause: `Start-Process ... -Verb RunAs -Wait` can continue waiting on the elevated process tree after the installer starts the long-lived Vexi `pythonw.exe` runtime.
- Runtime installation itself was successful; the defect was installer completion UX.
- Public Preview bootstrap no longer uses that blocking wait pattern. It launches a separate elevated installer window and lets the initial launcher exit.

### Public clean-install bootstrap
- Supports both a clean PC and an existing `C:\Vexi` installation.
- Detects Python 3.11 and Ollama and can install them through `winget` when absent.
- Creates/uses `C:\Vexi\.venv`, installs dependencies, pulls the configured local Ollama model and prewarms STT/TTS dependencies.
- Creates canonical startup, desktop and Settings shortcuts.
- Browser Packs remain separate and are installed only for browsers present on the target PC.

## 2026-09-13 - v0.1.2 candidate
### Structured Browser Control & Barge-In
- Added local Browser Bridge runtime + Manifest V3 extension foundation for Chromium-family browsers.
- Added semantic active-page snapshots and generic `find -> resolve -> select -> verify` automation.
- Added YouTube visible-card enumeration and selection by ordinal/title/channel/spatial reference when Browser Bridge is connected.
- Added structured HTML5 media control foundation: play/pause/seek/volume/rate/mute and YouTube-specific fullscreen/captions/next/miniplayer actions where available.
- Added interruptible TTS / barge-in test implementation with adaptive echo guard.
- Production startup target changed to hidden `pythonw.exe`; debug console remains explicit.

### Installer revision r1 - failed
- Added persistent installer logging and transactional rollback.
- **Field result:** Windows PowerShell 5.1 parser failure inside `install_v012.ps1`; runtime was not promoted.

### Installer revision r2 - failed preflight
- **Field result:** batch caret escaping (`^|`) reached PowerShell literally; preflight failed with `Unexpected token '^'`.
- Safety result: existing installation was not modified.

### Installer revision r3 - successful runtime path
- Dedicated `preflight_v012.ps1` replaced inline syntax parsing.
- v0.1.2 subsequently reached runtime and logged `BrowserBridge ready` plus canonical `Vexi v0.1.2 ready`; structured page routing still required completion.

## 2026-09-13 - v0.1.1
### Control Foundation
First real semantic release.

- Introduced router/control/memory foundation.
- Added Windows audio/display/filesystem adapters.
- Added application/window state operations.
- Added initial deterministic YouTube navigation.
- Added local personal memory/onboarding.
- Added truth-preserving execution states.

## 2026-09-13 - legacy lab lineage
Historical experiment labels only; not public product versions.

- Lab 4.0: local STT + female Silero TTS + application/browser control foundation.
- Lab 4.1: Steam/application safety, microphone recovery, minimize/maximize/focus/close verification work.
- Lab 4.2: routing/filler-word experiments and browser/site parsing.
- Lab 4.3: intent-parser regression testing; exposed `OPEN_STT_ALIASES` and live-patch failures.
- Lab 4.4/4.4.1: architecture work later normalized into semantic versions v0.1.1+.

See [INCIDENTS.md](INCIDENTS.md) for dated failure details.
