# Vexi

**Vexi** is a local-first Windows voice assistant / desktop agent focused on truthful execution, state-aware automation, reusable browser control, local personal memory, and safe tool routing.

> Status: **v0.1.3 Public Preview / field testing**. Core v0.1.3 has reached `READY` on the primary Windows laptop. Browser Packs v0.1.0 and the new clean-install bootstrap are now being validated on additional PCs. This is not yet a stable release.

## Public Preview

The public preview contains the **Core installer plus independent Browser Packs for Vivaldi, Chrome, Edge, Brave, Opera and Firefox**.

- [Install / field-test instructions](releases/v0.1.3-preview/INSTALL.md)
- [Release notes](releases/v0.1.3-preview/RELEASE_NOTES.md)
- [SHA-256 checksums](releases/v0.1.3-preview/SHA256SUMS.txt)

The release documentation and integrity metadata are public in this repository. The binary bundle is currently distributed as the field-test artifact while the GitHub release-asset publication path is being finalized; do not treat a missing repository ZIP asset as a failed Core build.

For a new PC: extract the Public Preview bundle, open `Core`, run `INSTALL_VEXI.bat`, accept UAC, wait for `INSTALL COMPLETE`, then install only the Browser Pack(s) needed on that PC.

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
- Core and plugins are independently versioned.
- Every observed failure becomes a dated regression case.

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
- Window state: open, focus, minimize, maximize, close, terminate, status.
- System master volume / mute with readback verification.
- Display controls foundation: brightness, HDR workflow, wallpaper.
- Filesystem typed operations foundation.
- Background runtime, tray, overlay, version identity.

### Browser / web
Browser integration is now a separate installable layer rather than an embedded Core component.

- Browser Protocol v1.
- Independent Browser Pack v0.1.0 candidates for Vivaldi, Chrome, Edge, Brave, Opera and Firefox.
- Active-tab observation, semantic snapshots, text input, ordered collections, element selection and media control.
- Reusable `observe -> find -> resolve -> act -> verify` page automation.
- Core upgrades preserve installed browser packs.

### YouTube first full vertical
YouTube is the first structured-site vertical used to prove the reusable browser model.

Canonical interaction chain:

`existing YouTube tab -> SearchBox -> input -> results collection -> ordinal/title/channel selection -> verified video page -> player context`

Player-scoped control is separated from browser/system control: media fullscreen affects the video player, and media volume affects the HTML video element rather than Windows master volume.

### Security / service auth
v0.1.3 adds a local Security UI and a universal service/auth routing contract. Manual API/token values are stored in Windows Credential Manager and are never accepted by voice or normal conversation.

Material communication and financial/legal/security-sensitive side effects are denied in the current Vexi profile. Reversible external account mutation requires a dedicated approval contract.

### Assistant identity
The user can rename the assistant by voice or Settings UI. In v0.1.3 the new name fully replaces both display and wake identity. Internal component IDs and version identity remain `vexi` / semantic versioning.

### Personal memory
Vexi stores local user-confirmed preferences separately from short-lived conversational context. Credentials, passwords, tokens, recovery codes, and other security secrets are not durable Vexi memory.

## Version line

### v0.1.1 - Control Foundation
First real semantic release. Introduced router/control/memory foundation, Windows control adapters, initial YouTube navigation and local personal memory.

### v0.1.2 - Structured Browser Control & Barge-In
Reached laptop runtime and proved Browser Bridge startup, canonical runtime identity, barge-in and several control foundations. Field testing showed that structured current-page YouTube routing still needed completion.

### v0.1.3 - Plugin Kernel, Security UI & YouTube Automation
Current public preview. Core v0.1.3 has a confirmed Windows `READY` field run. The public bootstrap supports both clean install and update, while browser integrations are independently versioned Browser Packs.

Earlier `3.x / 4.x` values are retained only as **legacy lab lineage**, not public product versions.

## Runtime truth states

Every action result is normalized to one of:

`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

The response layer must preserve that truth.

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - semantic release history and installer revisions.
- [INCIDENTS.md](INCIDENTS.md) - dated engineering failures and fixes.
- [FIELD_LOG_2026-09-13.md](FIELD_LOG_2026-09-13.md) - chronological laptop field evidence.
- [ARCHITECTURE.md](ARCHITECTURE.md) - horizontal/vertical architecture.
- [ACCESS_CONTROL.md](ACCESS_CONTROL.md) - system + web permission model.
- [SERVICE_AUTH_ROUTING.md](SERVICE_AUTH_ROUTING.md) - universal service/auth route registry.
- [SECURITY_AUTH_UI.md](SECURITY_AUTH_UI.md) - Credential Manager and strict risk profile.
- [ASSISTANT_IDENTITY_COMMANDS.md](ASSISTANT_IDENTITY_COMMANDS.md) - configurable assistant identity.
- [SPEECH_CANONICALIZER.md](SPEECH_CANONICALIZER.md) - conservative STT correction rules.
- [V013_CORE_AND_BROWSER_PACKS.md](V013_CORE_AND_BROWSER_PACKS.md) - v0.1.3 component split and artifact hashes.
- [CAPABILITY_GRID.md](CAPABILITY_GRID.md) - reusable horizontal capabilities and site tiers.
- [STRUCTURED_BROWSER_GRID.md](STRUCTURED_BROWSER_GRID.md) - generic page snapshot / resolver / verification mechanism.
- [YOUTUBE_CONTROL_GRID.md](YOUTUBE_CONTROL_GRID.md) - first deep structured-site vertical.
- [WINDOWS_CONTROL_GRID.md](WINDOWS_CONTROL_GRID.md) - display, audio, windows, filesystem and future device controls.
- [BARGE_IN_AND_RUNTIME.md](BARGE_IN_AND_RUNTIME.md) - interruptible TTS and runtime policy.
- [ROADMAP.md](ROADMAP.md) - current validation and next-stage work.

## Public repository note

This folder is the sanitized public engineering mirror. Internal operational details remain in the canonical Notion project record. No credentials, private memory data, tokens, or raw local account identifiers are published here.
