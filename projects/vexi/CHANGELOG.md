# Vexi changelog

All dates use Europe/Berlin local date unless noted otherwise.

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

### Public clean-install bootstrap r1
- Supports both a clean PC and an existing `C:\Vexi` installation.
- Detects Python 3.11; when missing, can install `Python.Python.3.11` through Windows Package Manager (`winget`).
- Detects Ollama; when missing, can install `Ollama.Ollama` through `winget`.
- Creates/uses `C:\Vexi\.venv` and installs Vexi Python dependencies.
- Pulls the configured local Ollama model when absent.
- Prewarms faster-whisper `small` and Silero `v5_ru` so clean-PC first startup is observable during installation rather than failing a short READY timeout.
- Creates canonical startup, desktop and Settings shortcuts.
- Starts Core hidden and requires `Vexi v0.1.3 ready` before reporting install completion.
- Browser Packs remain separate and are installed only for browsers present on the target PC.
- Installer transcript: `%TEMP%\Vexi_v0.1.3_public_install.log`.

### Validation before public preview packaging
- Core Python compile: PASS.
- `regression_tests_v013.py`: PASS on the build environment used for the v0.1.3 candidate.
- Six Browser Pack Python payloads: compile PASS.
- Browser extension JavaScript syntax: PASS.
- Browser Pack command-queue deterministic regression: PASS on the candidate build.
- Public clean-install bootstrap is **preview/test** until it passes on additional Windows PCs.

### v0.1.3 public preview hashes
- Public Preview all-in-one bundle: `07f03bb5f0dac9916e029fa0a9332ec6701d8eabc3edff919a4e13cecd566dac`
- Vivaldi Pack: `71f6ce3a4e8a24e115c1dfe46a83cc8e501064b2805b48c55110b239caee76a4`
- Chrome Pack: `01cda7f9cc7740348a0f0055ad020b275c4f1aedfa0bff9b493a63109af241c7`
- Edge Pack: `ed68281852ad08387bd0f2fad6fa2632d4589d503c6ad247157943b559f09c85`
- Brave Pack: `135d49012ff024ff76bb1af663542f9599dee69b96a082bcdc83e12787b70624`
- Opera Pack: `216a18d1c40127b5aecd41988703bff9337d3380410c737a5762f2914323eadc`
- Firefox Pack: `efc7483eb8e75569a061c33bc0aa6c6e338421c6d4e58fced05634ecf9cc93f2`
- All Browser Packs bundle: `e5a3f6fafaef4e1e77015a967521f1cd71d4e14742d6557d5c0f3022f0ed06fa`

## 2026-09-13 - v0.1.2 candidate
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

### Installer revision r1 - failed
- Added persistent installer logging and transactional rollback after the first update attempt left v0.1.1 active.
- Added package syntax checks before stopping the working runtime.
- Added explicit `version.py == 0.1.2` validation and `Vexi v0.1.2 ready` promotion evidence.
- **Field result:** Windows PowerShell 5.1 parser failure inside `install_v012.ps1`; runtime was not promoted.

### Installer revision r2 - failed preflight
- Removed the r1 nested inline `python -c` version-detection quoting.
- Added installer syntax preflight before touching the working runtime.
- **Field result:** batch caret escaping (`^|`) reached PowerShell literally; preflight itself failed with `Unexpected token '^'`.
- Safety result: the existing v0.1.1 installation was not modified.

### Installer revision r3 - successful runtime path
- Replaced inline `powershell -Command` syntax parsing with dedicated `preflight_v012.ps1`.
- Preflight reports parser line/column and returns a stable non-zero exit code.
- Hardened UAC re-launch quoting for installer paths.
- Runtime payload remains v0.1.2; r3 changes installer reliability only.
- **Field result:** v0.1.2 subsequently reached runtime on the laptop and logged `BrowserBridge ready` plus canonical `Vexi v0.1.2 ready`; structured page routing still required architectural completion.

### v0.1.2 package hashes
- base candidate: `6ec9c68b0673cc4c99694c6e5d4a782cd967e573635ce3cb928a2e137a3845e7`
- installer r1: `59ea2af4eb81c46c215c2cf410c6422fff5b25321ecbd6a881e3acaa21c39600`
- installer r2: `d6532e0a576a8890db488ba7ecac05f9f869b72fe2549a6839edc53459e1f8fc`
- installer r3: `64fecd8b7d819a1c3f20a3e680036f5f4e8af90aa60166fcf4307bd4fcf188fe`

## 2026-09-13 - v0.1.1
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

## 2026-09-13 - legacy lab lineage
Historical experiment labels only; not public product versions.

- Lab 4.0: local STT + female Silero TTS + application/browser control foundation.
- Lab 4.1: Steam/application safety, microphone recovery, minimize/maximize/focus/close verification work.
- Lab 4.2: routing/filler-word experiments and browser/site parsing.
- Lab 4.3: intent-parser regression testing; exposed `OPEN_STT_ALIASES` and live-patch failures.
- Lab 4.4/4.4.1: architecture work that was later normalized into semantic versions v0.1.1+.

See [INCIDENTS.md](INCIDENTS.md) for dated failure details.