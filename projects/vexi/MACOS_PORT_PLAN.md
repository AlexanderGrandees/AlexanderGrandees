# Vexi macOS port plan

Status: architecture/planning only. No macOS runtime release exists yet.

## Objective
Keep one shared semantic Core while replacing Windows-only execution adapters with a platform abstraction layer.

Target model:

```text
Shared Vexi Core
├─ Router / intent / context
├─ memory
├─ service + capability registry
├─ Browser Protocol v1
├─ site verticals (YouTube first)
├─ policy / verification / logging
└─ platform adapters
   ├─ Windows
   └─ macOS
```

## Shared components to preserve
The following should remain platform-neutral where possible:
- wake/session logic;
- STT/TTS orchestration;
- LLM/Ollama routing;
- Speech Canonicalizer;
- assistant identity;
- personal memory schema;
- service/auth registry;
- Browser Protocol v1;
- structured page snapshot model;
- YouTube vertical;
- media context and target resolution;
- execution truth states;
- permission/risk policy.

## macOS platform adapters
### Audio
Replace Windows Core Audio integration with a macOS CoreAudio-backed adapter.

Required first controls:
- read/set system output volume;
- mute/unmute;
- restore previous state;
- later: selected output device / per-app audio where supported.

### Window / application control
Replace Win32/UI Automation assumptions with macOS Accessibility APIs.

Initial operations:
- application running/visible state;
- focus/activate app;
- minimize/restore window;
- close normal window;
- active app/window observation.

The user must grant Accessibility permission explicitly. Vexi should not request broader privileges than needed.

### Secrets
Replace Windows Credential Manager with macOS Keychain while keeping the same logical secret-store interface.

Secrets remain excluded from:
- generic memory;
- normal voice input;
- LLM prompts where not required;
- public logs;
- GitHub/Notion documentation.

### Startup/runtime
Replace Windows Startup shortcuts with a macOS LaunchAgent / Service Management compatible user-mode startup path.

Normal runtime should remain user-mode. Do not model macOS deployment around running the entire assistant as root/admin.

### Permissions onboarding
Explicitly handle:
- Microphone;
- Accessibility;
- Automation only when a workflow truly requires it;
- Screen Recording only if a future visual/screen-reading layer actually needs pixels rather than DOM/accessibility state.

## Browser Packs on macOS
Chrome is the first target because the existing Manifest V3 Browser Pack architecture is portable in principle.

Target flow:

```text
Chrome
-> Vexi Browser Pack extension
-> localhost Browser Protocol v1 bridge
-> structured DOM snapshot
-> YouTube vertical
```

The YouTube semantic model should not be rewritten for macOS. Only browser-pack installation/runtime paths and platform integration should differ.

## First macOS MVP scope
Include:
- Core runtime;
- STT/TTS;
- Ollama/local LLM path;
- memory;
- Chrome Browser Pack;
- YouTube snapshot/search/ordinal selection/player controls;
- system volume/mute;
- basic app/window focus/minimize;
- Keychain secret storage;
- LaunchAgent/startup;
- settings/security UI adapted for macOS permissions.

Defer initially:
- HDR/display parity with Windows;
- deep display topology controls;
- Windows-specific registry/application discovery;
- Steam Windows-specific automation;
- low-level features that would require unnecessary root privileges.

## Distribution target
Public macOS distribution should use a proper application bundle:

```text
Vexi.app
-> Developer ID signing
-> Hardened Runtime
-> notarization
-> stapled notarization ticket
-> DMG (or equivalent signed distribution artifact)
```

Do not label the macOS build public-ready until codesigning/notarization and clean-machine permission onboarding are validated.

## Hardware target priority
1. Apple Silicon (M-series) first.
2. Intel Mac only after the shared Core and browser path are stable, because local-model performance characteristics differ substantially.

## Promotion matrix
A macOS preview is not promoted until it proves:
1. clean install;
2. microphone permission flow;
3. Accessibility permission flow;
4. local model startup;
5. Chrome Browser Pack connection;
6. active YouTube snapshot;
7. visible video extraction;
8. ordinal video open;
9. player fullscreen/media volume control;
10. system audio control;
11. user-mode autostart;
12. signed/notarized package on a second Mac.
