# Vexi changelog

All dates use Europe/Berlin local date unless noted otherwise.

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
- **Status:** built; laptop field confirmation still required.

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