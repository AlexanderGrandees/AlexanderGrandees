# Vexi v0.1.3 Core + Browser Packs

Status: **release candidate / Windows field validation required**.

## Component line

- Vexi Core: `v0.1.3 • test`
- Browser Protocol: `v1`
- Browser Packs: `v0.1.0`

Core and browser integrations are independently versioned. Core updates preserve Browser Pack install roots and plugin manifests.

## Install roots

```text
C:\Vexi\                             # Core
%LOCALAPPDATA%\VexiBrowserPacks\    # independent browser packs
%LOCALAPPDATA%\Vexi\plugins\        # plugin manifests
%LOCALAPPDATA%\Vexi\data\           # local durable identity/preferences/corrections
```

## Browser Packs

Each installed browser has a dedicated pack/endpoint so multiple Chromium-family browsers do not compete for one command queue.

| Browser | Plugin ID | Port |
|---|---|---:|
| Vivaldi | `vexi.browser.vivaldi` | 8765 |
| Chrome | `vexi.browser.chrome` | 8766 |
| Edge | `vexi.browser.edge` | 8767 |
| Brave | `vexi.browser.brave` | 8768 |
| Opera | `vexi.browser.opera` | 8769 |
| Firefox | `vexi.browser.firefox` | 8770 |

Pack capabilities:

`active_tab`, `structured_snapshot`, `text_input`, `element_select`, `media_control`.

## Browser Protocol v1

```text
Core
-> plugin manifest
-> localhost pack service
-> extension background process
-> active tab content script
-> semantic page snapshot / typed action
-> result
-> Core verification
```

Browser extension snapshots explicitly exclude password fields. API/OAuth service secrets are not stored in Browser Pack source.

## YouTube first full vertical

```text
ensure existing YouTube tab
-> observe active page
-> find semantic search box
-> input text + submit
-> verify search-results page
-> store ordered visible VideoCard collection
-> resolve ordinal/title/channel/spatial reference
-> open target
-> verify VIDEO page
-> create player context
-> control player itself
```

Player-scoped commands are distinct from browser/system commands:

- `видео на весь экран` -> media/player fullscreen, not browser F11;
- `видео тише` -> HTML media volume, not Windows master volume;
- `пауза`, `продолжи`, seek, rate, mute -> player state.

## Core v0.1.3 modules

New horizontal modules include assistant identity, conservative speech canonicalization, Credential Manager secret storage, service/auth registry, universal service router, policy gate, plugin manager, Browser Pack client, capability registry and Settings UI.

## Validation performed before packaging

- all Core Python files compile;
- deterministic Core regression suite passes;
- all Browser Pack Python files compile;
- all Chromium/Firefox extension JavaScript passes `node --check`;
- Browser Pack command-queue deterministic regression passes.

Windows-specific installer/runtime/extension behavior still requires laptop field evidence before promotion.

## Candidate hashes

- Core v0.1.3: `9eed77be7f6939b35ddab9526ec059c2fb03028cff17bf7bd11e776a31a80b4e`
- Vivaldi Pack: `71f6ce3a4e8a24e115c1dfe46a83cc8e501064b2805b48c55110b239caee76a4`
- Chrome Pack: `01cda7f9cc7740348a0f0055ad020b275c4f1aedfa0bff9b493a63109af241c7`
- Edge Pack: `ed68281852ad08387bd0f2fad6fa2632d4589d503c6ad247157943b559f09c85`
- Brave Pack: `135d49012ff024ff76bb1af663542f9599dee69b96a082bcdc83e12787b70624`
- Opera Pack: `216a18d1c40127b5aecd41988703bff9337d3380410c737a5762f2914323eadc`
- Firefox Pack: `efc7483eb8e75569a061c33bc0aa6c6e338421c6d4e58fced05634ecf9cc93f2`
- All Packs bundle: `e5a3f6fafaef4e1e77015a967521f1cd71d4e14742d6557d5c0f3022f0ed06fa`
