# Vexi

**Vexi** is a local-first Windows voice assistant / desktop agent focused on truthful execution, state-aware automation, reusable browser control, local personal memory, and safe tool routing.

> Status: active development / field testing. The proven installed runtime is currently **v0.1.1**. **v0.1.2** is the current structured-browser + barge-in candidate and is not considered promoted until laptop field validation passes.

## Why this project exists

The goal is not to build a voice chatbot that only narrates actions. Vexi is designed around a stricter execution contract:

`Natural language -> intent -> typed entities -> plan -> permission gate -> tool execution -> state verification -> truthful response`

If an action cannot be verified, Vexi must not claim that it succeeded.

## Core principles

- Local-first where practical.
- Typed tools instead of unrestricted shell access.
- Deterministic PC/browser routing before free-form LLM fallback.
- Execution before narration.
- State verification before success claims.
- Trusted application discovery hierarchy.
- Explicit risk tiers for local/system and web/account actions.
- Short-lived context + durable local personal preferences.
- Whole-module releases instead of live regex/PowerShell patching of production files.
- Every observed failure becomes a dated regression case.

## Current architecture

```text
Microphone / Text
-> Activation & session state
-> STT / normalization
-> Narrative-vs-command gate
-> Intent router
-> Entity + role resolver
-> Context resolver
-> Capability / permission gate
-> App / Browser / System / Filesystem adapter
-> Execution
-> State verification
-> Event + audit log
-> Response composer
-> TTS / tray / overlay
```

## Current capability areas

### Windows / desktop
- Application discovery and trusted launch paths.
- Window state: open, focus, minimize, maximize, close, terminate, status.
- System master volume / mute with readback verification.
- Display controls foundation: brightness, HDR workflow, wallpaper.
- Filesystem typed operations foundation.
- Background runtime, tray, overlay, version identity.

### Browser / web
- Preferred browser: Vivaldi in the current test environment.
- Generic browser navigation and state model.
- `StructuredPageAdapter` foundation.
- Local Browser Bridge + Manifest V3 extension design for Chromium-family browsers.
- Reusable `find -> resolve -> select -> verify` page automation.

### YouTube first vertical
YouTube is the first full structured-site vertical used to prove the reusable browser model.

Objects:
`Home, SearchResults, ResultCard, Video, Channel, Playlist, Player, Shorts, History, Subscriptions, Comment, Account`.

Target commands include:
- open/search YouTube;
- enumerate visible video cards;
- open by ordinal, title, channel, or spatial reference;
- ask for clarification when multiple cards are close matches;
- verified player play/pause/seek/volume/rate/fullscreen when structured player state is available.

### Personal memory
Vexi stores local user-confirmed preferences separately from short-lived conversational context.

Examples:
- preferred name;
- preferred browser;
- app aliases;
- preferred Steam profile alias;
- response/name-addressing preferences;
- other explicit, non-secret settings.

Credentials, passwords, tokens, recovery codes, and security secrets are not durable Vexi memory.

## Version line

### v0.1.1 — Control Foundation
First real semantic release. Introduced the router/control/memory foundation, Windows control adapters, initial YouTube navigation, application/window state work, and local personal memory.

### v0.1.2 — Structured Browser Control & Barge-In
Current candidate. Adds the generic structured browser layer, YouTube visible-card selection, browser bridge, interruptible TTS / barge-in, occasional-name policy, hidden production runtime, and canonical version identity.

Earlier `3.x / 4.x` values are retained only as **legacy lab lineage**, not public product versions.

## Runtime truth states

Every action result is normalized to one of:

`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

The response layer must preserve that truth. For example, `SENT_NOT_CONFIRMED` must never be spoken as "done".

## Safety model

Vexi uses two independent permission dimensions:

- `A0-A4` for local/system impact.
- `W0-W4` for web/account impact.

The stricter boundary wins. Public/read-only actions are low risk; account mutation, communication, financial, security, or destructive actions require stronger controls or are blocked by default.

See [ACCESS_CONTROL.md](ACCESS_CONTROL.md).

## Engineering history

A public, sanitized incident registry is maintained in [INCIDENTS.md](INCIDENTS.md). It includes the Steam uninstaller discovery failure, microphone interruption recovery, intent-router failures, live-patch regressions, Explorer/browser state bugs, audio routing findings, and the v0.1.2 installer `r1 -> r2 -> r3` chain.

A chronological reconstruction of the shared laptop logs is available in [FIELD_LOG_2026-09-13.md](FIELD_LOG_2026-09-13.md).

## Current promotion gate for v0.1.2

v0.1.2 is not promoted until:
- structured YouTube cards can be enumerated and selected on the laptop;
- browser transitions are verified;
- barge-in interrupts TTS without persistent self-echo false positives;
- normal runtime starts without a console;
- tray/overlay/log/voice all report the same canonical version;
- stale production launchers do not create duplicate runtimes;
- installer field test proves the runtime is actually `v0.1.2`.

## Documentation

- [CHANGELOG.md](CHANGELOG.md) — semantic release history and installer revisions.
- [INCIDENTS.md](INCIDENTS.md) — dated engineering failures and fixes.
- [FIELD_LOG_2026-09-13.md](FIELD_LOG_2026-09-13.md) — chronological field evidence from the shared laptop logs.
- [ARCHITECTURE.md](ARCHITECTURE.md) — horizontal/vertical architecture.
- [ACCESS_CONTROL.md](ACCESS_CONTROL.md) — system + web permission model.
- [CAPABILITY_GRID.md](CAPABILITY_GRID.md) — reusable horizontal capabilities and site tiers.
- [STRUCTURED_BROWSER_GRID.md](STRUCTURED_BROWSER_GRID.md) — generic page snapshot / resolver / verification mechanism.
- [YOUTUBE_CONTROL_GRID.md](YOUTUBE_CONTROL_GRID.md) — first deep structured-site vertical.
- [WINDOWS_CONTROL_GRID.md](WINDOWS_CONTROL_GRID.md) — display, audio, windows, filesystem and future device controls.
- [BARGE_IN_AND_RUNTIME.md](BARGE_IN_AND_RUNTIME.md) — interruptible TTS, runtime identity and console policy.
- [ROADMAP.md](ROADMAP.md) — current validation and next-stage work.

## Public repository note

This folder is the sanitized public engineering mirror. Internal operational details remain in the canonical Notion project record. No credentials, private memory data, tokens, or raw local account identifiers are published here.
