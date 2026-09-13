# Vexi v0.1.3 Public Preview

## Status

Public Preview / test build. Core v0.1.3 has a confirmed `READY` field run on the primary Windows laptop. The clean-install bootstrap and Browser Packs v0.1.0 are being validated on additional PCs.

## Core

- Plugin Kernel / Browser Protocol v1.
- Independent per-browser packs rather than browser extensions embedded in Core.
- Universal Service Router and Auth/Capability Registry.
- Settings UI with Assistant / Plugins / Security sections.
- Windows Credential Manager secret storage.
- Full user-defined assistant rename: display identity and wake identity change together.
- Conservative STT canonicalization and explicit correction memory.
- Strict high-responsibility policy gate.
- YouTube current-page-first automation and player-scoped media controls.

## Browser Packs v0.1.0

Separate packs are included for:

- Vivaldi
- Chrome
- Edge
- Brave
- Opera
- Firefox

Core upgrades do not overwrite Browser Pack installations.

## Public bootstrap r1

The original v0.1.3 update package successfully installed Core and reached `Vexi v0.1.3 ready`, but the non-elevated launcher could remain waiting after the long-lived runtime started. The Public Preview bootstrap removes that blocking `RunAs -Wait` pattern.

The new bootstrap also supports clean PCs by detecting/installing Python 3.11 and Ollama through `winget`, creating the Vexi virtual environment, installing dependencies, prewarming speech/TTS models and verifying runtime READY before declaring success.

## Known preview constraints

- Browser Pack installation still requires browser-specific extension activation. Chromium-family builds currently use `Load unpacked` during field testing.
- Browser Pack end-to-end YouTube behavior is still being validated on additional hardware/browser profiles.
- This is not a signed Windows installer/MSI yet.
- First clean install downloads dependencies and local AI models, so it is substantially heavier than an update.

## Integrity

See `SHA256SUMS.txt` in this folder.
