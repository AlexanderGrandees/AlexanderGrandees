# Vexi

**Vexi** is a local-first desktop voice assistant / agent focused on truthful execution, state-aware automation, reusable browser control, local personal memory, and safe tool routing.

> Status: **v0.1.4 Public Preview / field testing**. Core v0.1.4 is installed and running on the primary Windows laptop. Vivaldi Browser Pack v0.1.2 has confirmed structured YouTube DOM extraction, ordinal video selection, and player fullscreen ON. The Chrome v0.1.2 bundle is packaged for third-party field testing. This is not yet a stable release.

## Current public preview

The current Windows preview is split into independently versioned components:

- **Vexi Core v0.1.4**
- **Browser Protocol v1**
- **Vivaldi Browser Pack v0.1.2** - field-tested on the primary machine
- **Chrome Browser Pack v0.1.2** - packaged for third-party clean-install testing

Release documentation:

- [v0.1.4 install / field-test instructions](releases/v0.1.4-preview/INSTALL.md)
- [v0.1.4 release notes](releases/v0.1.4-preview/RELEASE_NOTES.md)
- [v0.1.4 SHA-256 checksums](releases/v0.1.4-preview/SHA256SUMS.txt)
- [macOS port plan](MACOS_PORT_PLAN.md)

The repository currently publishes sanitized engineering documentation and integrity metadata. Binary ZIP artifacts are distributed separately until a GitHub release-asset publication path is finalized.

## Why this project exists

The goal is not to build a voice chatbot that only narrates actions. Vexi follows a stricter execution contract:

`Natural language -> intent -> typed entities -> context -> plan -> permission gate -> tool execution -> state verification -> truthful response`

If an action cannot be verified, Vexi must not claim that it succeeded.

## Core principles

- Local-first where practical.
- Typed tools instead of unrestricted shell access.
- Deterministic PC/browser routing before free-form LLM fallback.
- Execution before narration.
- State verification before success claims.
- Trusted application discovery hierarchy.
- Explicit risk tiers for local/system and web/account actions.
- Short-lived action context + durable local personal preferences.
- Whole-module releases instead of live regex/PowerShell patching of production files.
- Core and plugins are independently versioned.
- Every observed failure becomes a dated regression case.
- Financial, irreversible, security-sensitive, and elevated-responsibility actions remain deny-by-default in the current profile.

## Current architecture

```text
Microphone / Text
-> Activation & session state
-> STT
-> conservative Speech Canonicalizer
-> Narrative-vs-command gate
-> Intent router
-> Entity + role resolver
-> Context resolver
-> Capability + Auth Registry
-> Permission / risk gate
-> Core adapter or independent plugin
-> Execution
-> State verification
-> Event + audit log
-> Response composer
-> TTS / tray / overlay
```

## Current capability areas

### Windows / desktop
- Application discovery and trusted launch paths.
- Window state foundation: open, focus, minimize, maximize, close, terminate, status.
- System master volume / mute with readback verification.
- Display controls foundation: brightness, HDR workflow, wallpaper.
- Filesystem typed operations foundation.
- Background runtime, tray, overlay, version identity.
- Field note: on the primary Windows setup, some computer-control paths worked reliably only when the runtime was elevated. This is tracked as a platform/permission issue, not a universal requirement.

### Browser / web
Browser integration is an independent installable layer rather than an embedded Core component.

- Browser Protocol v1.
- Per-browser packs survive Core upgrades.
- Active-tab observation and semantic page snapshots.
- Text input, ordered collections, element selection and media control.
- Reusable `observe -> find -> resolve -> act -> verify` automation.
- Browser-pack diagnostics expose registry, bridge service, extension heartbeat, page type, URL, snapshot age and semantic element counts.

### YouTube first full vertical
The YouTube vertical now has confirmed field evidence for the structured path.

Observed on 2026-09-13 with Vivaldi Browser Pack v0.1.2:

- active YouTube page detected as `site=youtube`, `page_type=HOME`;
- structured snapshot returned `search_box` plus visible `video` objects;
- titles/channels were extracted from the active viewport;
- `открой второе видео` selected the second visible card and returned `CONFIRMED_SUCCESS`;
- `весь экран` applied player fullscreen and returned `CONFIRMED_SUCCESS`.

Current interaction chain:

`existing YouTube tab -> fresh snapshot -> SearchBox / VideoCard[] -> ordinal/title/channel resolution -> verified video page -> player context`

Known remaining Core-side gap: natural fullscreen-OFF phrases such as `сверни это видео` / `убери видео из полноэкранного режима` still need consistent media-target routing instead of generic window routing.

### Security / service auth
Manual API/token values are UI-only and stored in the OS credential store. They are never accepted by voice as normal conversation input and must not appear in generic memory or public logs.

Material communication and financial/legal/security-sensitive side effects are denied in the current Vexi profile unless a dedicated future policy explicitly allows them.

### Assistant identity
The user can rename the assistant. The new name replaces display and wake identity while internal component IDs and semantic version identity remain `vexi`.

### Personal memory
Vexi stores local user-confirmed preferences separately from short-lived conversational context. Credentials, passwords, tokens, recovery codes, and other security secrets are excluded from durable Vexi memory.

## Version line

### v0.1.1 - Control Foundation
First real semantic release: router/control/memory foundation, Windows control adapters, initial YouTube navigation and local personal memory.

### v0.1.2 - Structured Browser Control & Barge-In
Proved Browser Bridge startup and barge-in foundations, but field testing showed current-page structured routing was still incomplete.

### v0.1.3 - Plugin Kernel, Security UI & YouTube Automation
Separated Browser Packs from Core, introduced service/auth routing, Security UI, assistant identity, Speech Canonicalizer and Browser Protocol v1. Field testing exposed installer and plugin-manifest issues that became regression cases.

### v0.1.4 - Media Context & Natural Control
Current public preview. Adds media-target priority, active-surface observation, compound browser commands, BOM-tolerant plugin loading, safer browser selection and packaged Chrome v0.1.2 support. Primary Windows runtime identity has been confirmed as `v0.1.4`.

Earlier `3.x / 4.x` values are retained only as **legacy lab lineage**, not public product versions.

## Runtime truth states

Every action result is normalized to one of:

`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

The response layer must preserve that truth.

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - semantic release history and installer/browser-pack revisions.
- [INCIDENTS.md](INCIDENTS.md) - dated engineering failures and fixes.
- [FIELD_LOG_2026-09-13.md](FIELD_LOG_2026-09-13.md) - chronological field evidence.
- [ARCHITECTURE.md](ARCHITECTURE.md) - horizontal/vertical architecture.
- [ACCESS_CONTROL.md](ACCESS_CONTROL.md) - system + web permission model.
- [SERVICE_AUTH_ROUTING.md](SERVICE_AUTH_ROUTING.md) - universal service/auth route registry.
- [SECURITY_AUTH_UI.md](SECURITY_AUTH_UI.md) - credential storage and strict risk profile.
- [ASSISTANT_IDENTITY_COMMANDS.md](ASSISTANT_IDENTITY_COMMANDS.md) - configurable assistant identity.
- [SPEECH_CANONICALIZER.md](SPEECH_CANONICALIZER.md) - conservative STT correction rules.
- [CAPABILITY_GRID.md](CAPABILITY_GRID.md) - reusable horizontal capabilities and site tiers.
- [STRUCTURED_BROWSER_GRID.md](STRUCTURED_BROWSER_GRID.md) - generic page snapshot / resolver / verification mechanism.
- [YOUTUBE_CONTROL_GRID.md](YOUTUBE_CONTROL_GRID.md) - YouTube structured vertical and current field status.
- [WINDOWS_CONTROL_GRID.md](WINDOWS_CONTROL_GRID.md) - display, audio, windows, filesystem and future device controls.
- [BARGE_IN_AND_RUNTIME.md](BARGE_IN_AND_RUNTIME.md) - interruptible TTS and runtime policy.
- [MACOS_PORT_PLAN.md](MACOS_PORT_PLAN.md) - planned platform split for macOS.
- [ROADMAP.md](ROADMAP.md) - current validation and next-stage work.

## Public repository note

This folder is a sanitized public engineering mirror. Internal operational details remain in the canonical project record. No credentials, private memory data, tokens, or raw local account identifiers are published here.
