# Vexi architecture

## Design objective
Vexi is built as a reusable local agent runtime rather than a collection of phrase-specific automation scripts.

Canonical flow:

```text
Natural language
-> normalization
-> narrative/command classification
-> intent(s)
-> entities + semantic roles
-> context
-> capability / permission checks
-> plan
-> typed adapter execution
-> state verification
-> truthful response
```

## Horizontal vs vertical architecture

### Horizontals
Implemented once and reused across domains:
- activation/session state;
- STT/input normalization;
- intent routing;
- entity resolution;
- app discovery/trust tiers;
- window state/control;
- browser session/page snapshot;
- permission/risk gate;
- numeric property engine;
- filesystem mechanics;
- memory/context;
- verification;
- logging/telemetry;
- TTS/UI/runtime lifecycle.

### Verticals
Define domain semantics only:
- YouTube;
- Steam / Steam Support;
- Google Search;
- GitHub;
- Gmail / Calendar;
- Notion;
- TradingView;
- Binance;
- platform display/audio/filesystem/devices.

A vertical must not reimplement generic window, permission, memory, property, or verification logic.

## Runtime modules
Representative modular layout:

```text
vexi.py
router.py
memory.py
memory_store.py
capability_registry.py
service_registry.py
service_router.py
policy_gate.py
plugin_manager.py
browser_pack_client.py
app_registry.py
window_manager.py
browser_adapter.py
youtube_adapter.py
audio_adapter.py
display_adapter.py
filesystem_adapter.py
steam_adapter.py
ui.py
version.py
```

## Platform abstraction
The semantic Core should remain shared while OS-specific mechanics live behind typed adapters.

```text
Shared Core
├─ intent / context / memory
├─ capability + auth registry
├─ policy / verification
├─ Browser Protocol v1
├─ site verticals
└─ platform adapters
   ├─ Windows
   │  ├─ Core Audio / Win32 / UI Automation
   │  ├─ Credential Manager
   │  └─ Windows startup/runtime
   └─ macOS (planned)
      ├─ CoreAudio
      ├─ Accessibility APIs
      ├─ Keychain
      └─ LaunchAgent / Service Management
```

macOS support is currently a port plan, not a released runtime. See [MACOS_PORT_PLAN.md](MACOS_PORT_PLAN.md).

## Application discovery trust hierarchy

1. explicit trusted config/path;
2. vendor-authoritative registry/API;
3. known standard install path;
4. exact safe Start Menu/Desktop shortcut;
5. safe metadata discovery;
6. fuzzy candidate only as a low-risk fallback.

Lower-trust discovery must never overwrite a trusted T0-T2 mapping without revalidation.

Blocked generic launch candidates include uninstallers, installers, repair/maintenance tools, and ambiguous setup binaries.

## Window state contract
Application/process state and visible-window state are separate.

Generic operations:
- `is_running`;
- `has_visible_window`;
- `open`;
- `focus`;
- `minimize`;
- `maximize`;
- `close_window`;
- `terminate_process`;
- `active_window`.

Important invariant:
`FOCUS != RESTORE != MAXIMIZE != BROWSER_FULLSCREEN != MEDIA_FULLSCREEN`.

Restore is valid only when the target is minimized.

## Browser architecture
Browser integration is independently versioned from Core.

Current proven component line:
- Core v0.1.4 Public Preview;
- Browser Protocol v1;
- Vivaldi Browser Pack v0.1.2 field-tested;
- Chrome Browser Pack v0.1.2 packaged for third-party validation.

Preferred structured execution priority:

1. local browser extension / structured DOM bridge using the user's existing browser profile;
2. CDP when the browser is Vexi-managed;
3. accessibility tree / OS accessibility APIs;
4. deterministic keyboard shortcuts after context verification;
5. visual-agent fallback.

Coordinate-only clicking is not the canonical route.

Generic page execution:

```text
Browser Session
-> Page Snapshot
-> Semantic Elements
-> Entity Resolver
-> Site Vertical Mapping
-> Action Planner
-> DOM / Accessibility Action
-> Post-action Snapshot
-> Verification
```

Semantic elements expose fields such as:
`element_id`, `role`, `text`, `accessible_name`, `href`, `value`, `selected`, `checked`, `disabled`, `visible`, `rect`, `container`, `semantic_type`.

## YouTube reference vertical
Page types:
`HOME | SEARCH_RESULTS | VIDEO | CHANNEL | PLAYLIST | SHORTS | HISTORY | SUBSCRIPTIONS`.

Visible video cards capture:
`title`, `channel`, `duration`, `metadata_text`, `href`, `position`, `visible`.

Current field evidence proves that Browser Pack v0.1.2 can expose visible YouTube `video` semantic objects and that Core can open the second visible card and enter player fullscreen.

Resolver behavior:
- combine title/channel/context/spatial signals;
- auto-select only at high confidence;
- ask a short clarification when top matches are too close;
- verify the resulting page/URL after activation.

## Media target contract
Media controls must be scoped separately from window/system controls.

```text
explicit object target
> current active media/player
> last controlled target
> browser/window/system default
```

Examples:
- `сверни браузер` -> window minimize;
- `сверни это видео` while player is fullscreen -> media fullscreen OFF;
- `выключи звук видео` -> media audio;
- `выключи звук на ноуте` -> system audio.

This target-priority rule is currently being hardened in Core v0.1.4.

## Property engine
Reusable numeric-property workflow:

```text
READ CURRENT
-> PARSE USER VALUE / DELTA
-> COMPUTE TARGET
-> SET
-> READ BACK
-> VERIFY
-> RESPOND
```

Used for master volume, brightness, browser zoom, media volume, playback speed, and future device properties.

## Context
Short-lived action context is separate from LLM conversation history.

Representative fields:
- `last_app`;
- `last_window`;
- `last_site`;
- `last_browser`;
- `last_tab`;
- `current_collection`;
- `current_media`;
- `current_player`;
- `last_media`;
- `last_action`;
- `last_target`;
- `last_created_object`;
- `last_destination`.

Context must only commit unverified target state when the execution contract explicitly allows an intermediate state. A failed or merely sent action must not silently become the canonical current object.

## Personal memory
Durable memory is local and explicit.

Examples:
- preferred name;
- language;
- preferred browser;
- app/device aliases;
- response preferences;
- user-confirmed defaults.

Secrets are excluded: passwords, tokens, Steam Guard codes, recovery codes, API secrets, and credentials are not durable memory.

## Truthful execution states
Every action returns exactly one of:

`CONFIRMED_SUCCESS`, `SENT_NOT_CONFIRMED`, `ALREADY_SATISFIED`, `NOT_FOUND`, `BLOCKED`, `UNSUPPORTED`, `FAILED`, `AMBIGUOUS`.

Response text must preserve the state semantics.

## Barge-in
Target speech architecture:

```text
TTS synthesis
-> chunked OutputStream
+ concurrent microphone monitor
-> VAD + echo guard
-> human speech detected
-> cancel TTS
-> preserve user utterance buffer
-> route as next turn
```

The assistant's own speaker output must not repeatedly self-trigger interruption.

## Release mechanics
Production update policy:

```text
package
-> preflight syntax/tests
-> backup
-> stop active runtime
-> whole-module replacement
-> config migration
-> installed syntax/regression checks
-> start hidden production runtime
-> verify canonical version/log identity
-> promote OR rollback
```

Browser Packs follow the same principle independently: package -> install -> registry validation -> service health -> extension heartbeat -> page snapshot -> semantic regression.

No ad-hoc regex/source surgery is part of the supported production update path.
