# Vexi engineering incident registry

Public/sanitized record. Local usernames, account identifiers, private memory content, and secrets are intentionally omitted.

## 2026-09-13 — Steam discovery selected maintenance/uninstall path
**Severity:** high safety regression

### Symptom
A generic application discovery route could select Steam uninstall/maintenance entries instead of the trusted launcher.

### Cause
Registry/uninstall metadata and broad discovery were allowed to compete with trusted application paths.

### Fix
- trusted Steam path resolution;
- vendor registry / standard path priority;
- blacklist for `uninstall`, `unins`, `remove`, `setup`, `installer`, repair/maintenance targets;
- trusted paths cannot be overwritten by lower-trust discovery;
- app cache invalidation;
- launch verification.

### Permanent regression rule
Maintenance/uninstall tools are never generic launch targets.

---

## 2026-09-13 — PortAudio stream interruption
**Symptom:** microphone stream interruption (`PortAudio -9983`) during continuous voice runtime.

### Fix direction
Transient audio-device failures are treated as recoverable runtime events: reopen/retry the microphone stream instead of collapsing into a generic loop error.

---

## 2026-09-13 — Silero TTS dependency failure
**Symptom**
```text
ModuleNotFoundError: No module named 'scipy'
```

### Effect
Preferred Silero female voice could not load; fallback TTS was used.

### Fix
`scipy` became a required clean-install dependency for the Silero path.

---

## 2026-09-13 — Router constant missing
**Symptom**
```text
NameError: name 'OPEN_STT_ALIASES' is not defined
```

### Cause
A partial hotfix referenced a constant that had not been safely introduced into the active module.

### Lesson
No live partial production-module patching without whole-module validation.

---

## 2026-09-13 — PowerShell live patch corrupted Russian aliases
### Symptom
Russian STT aliases became `???????`.

### Cause
Encoding corruption during direct PowerShell text manipulation.

### Policy change
Production Python modules are no longer modified through ad-hoc search/replace PowerShell patches.

---

## 2026-09-13 — Regex Unicode replacement failure
**Symptom**
```text
re.error: bad escape \u
```

### Lesson
Avoid regex replacement for source-code surgery when replacement content contains escape sequences.

---

## 2026-09-13 — Patch-generated Python syntax failure
A live text replacement produced invalid Python syntax.

### Lesson
Source updates must be packaged, syntax-checked, regression-tested, and promoted atomically.

---

## 2026-09-13 — Explorer false-positive state
### Symptom
Vexi reported Explorer as open because `explorer.exe` existed, even when no File Explorer window was visible.

### Cause
Windows shell process presence was treated as application-window evidence.

### Fix contract
A real File Explorer window must be detected (`CabinetWClass` / `ExploreWClass`) and verified after open/focus actions.

---

## 2026-09-13 — Browser focus changed fullscreen/maximized state
### Cause
`SW_RESTORE` was used as part of generic focus logic even when the window was not minimized.

### New invariant
`FOCUS != RESTORE != MAXIMIZE != FULLSCREEN`.

Only minimized windows should be restored before focus.

---

## 2026-09-13 — Natural-language modal open not recognized
Direct executor diagnostics showed `открой youtube` handled while `можешь открыть youtube` was not handled by the old parser.

### Lesson
Intent must be normalized semantically, not matched only by narrow verb forms.

---

## 2026-09-13 — Audio backend vs semantic routing split
### Evidence
Direct Windows master-volume test succeeded with read/set/readback/restore (`~60% -> ~70% -> ~60%`).

### Failure domain
Natural phrases such as `громкость на полную`, `выключим звук на ноуте`, and `звук на ноль` were not consistently routed to the working adapter.

### Architecture response
Reusable property workflow: `READ -> COMPUTE -> SET -> READBACK -> VERIFY` plus broader semantic audio routing.

---

## 2026-09-13 — Narrative text executed as commands
Reports/descriptions could be mistaken for actions.

### Fix contract
Classify utterances before execution:
`COMMAND | QUESTION | REPORT | CORRECTION | EXPLANATION | CONVERSATION`.

Only executable intents may reach PC/browser tools.

---

## 2026-09-13 — Duplicate unsupported response
A single unsupported media request produced duplicate `UNSUPPORTED` responses.

### Fix contract
One `intent_id` -> one execution -> one result -> one spoken response.

---

## 2026-09-13 — v0.1.2 installer r1 parser failure
**Status:** failed; previous runtime preserved / rolled back.

### Root-cause class
Nested inline `python -c` / quoting in Windows PowerShell 5.1.

---

## 2026-09-13 — v0.1.2 installer r2 preflight failure
**Status:** failed before touching current installation.

### Observed error
```text
Unexpected token '^'
```

### Root cause
CMD caret escape characters were passed literally into quoted PowerShell.

### Safety result
Working v0.1.1 installation was not modified.

---

## 2026-09-13 — v0.1.2 installer r3
**Status:** runtime path later succeeded.

Dedicated PowerShell preflight replaced the inline parser logic. v0.1.2 subsequently reached `Vexi v0.1.2 ready` and `BrowserBridge ready` on the primary machine.

---

## 2026-09-13 — v0.1.3 installer parent waited indefinitely after successful install
**Severity:** medium installer UX/reliability issue

### Symptom
The initial window remained on:
```text
Vexi Core v0.1.3 - requesting administrator permission...
```
while the elevated install had actually completed and the runtime later logged `Vexi v0.1.3 ready`.

### Root cause
`Start-Process powershell.exe -Verb RunAs -Wait` could continue waiting on the elevated process tree after that installer started the long-lived Vexi `pythonw.exe` runtime.

### Important finding
Two visible `pythonw.exe` entries were a venv launcher plus its base-Python child, not duplicate Vexi instances.

### Fix contract
Do not use an unbounded process-tree wait for installer completion. Use explicit child/result handshake or bounded PID/status verification.

---

## 2026-09-13 — Public Preview package exposed stale installer entry point
**Severity:** medium packaging issue

### Symptom
A field tester could launch an old `INSTALL_UPDATE.bat` path and reproduce the old elevation/wait behavior even though a newer clean installer existed in the same package.

### Cause
Multiple plausible installer entry points were shipped together.

### Fix
- canonical `START_HERE_INSTALL_VEXI.bat`;
- stale updater entry points removed or redirected;
- packaging itself added to release validation.

### Regression rule
One obvious install entry point per public bundle.

---

## 2026-09-13 — Browser Pack v0.1.0 manifest BOM made installed pack invisible to Core
**Severity:** high functional integration regression

### Symptom
Files and extension existed, but Core returned:
```json
{"installed": false, "connected": false, "detail": "browser_pack_not_installed"}
```

### Evidence
Plugin manifest first bytes:
```text
EF BB BF
```

### Root cause
Windows PowerShell 5.1 `Set-Content -Encoding UTF8` wrote a UTF-8 BOM. Core read plugin JSON with plain `utf-8`; JSON parsing failed and the plugin manager silently skipped the file.

### Fix
Browser Pack v0.1.1:
- writes UTF-8 without BOM;
- validates the written manifest;
- checks Core registration;
- exposes service/extension diagnostics.

Core v0.1.4:
- accepts legacy BOM manifests;
- logs manifest parse failures instead of silently continuing.

### Regression rule
Plugin install success requires a Core-readable manifest, not merely copied files.

---

## 2026-09-13 — Browser extension heartbeat worked but YouTube cards were missing
**Severity:** medium structured-browser regression

### Symptom
Browser Pack diagnostics showed a connected extension and fresh YouTube page metadata, but structured snapshot contained only:
```text
search_box: 1
video: 0
```

### Root cause
The YouTube extractor depended on selectors/structures that no longer matched the active YouTube DOM.

### Fix
Browser Pack v0.1.2:
- enumerates actual `/watch` links;
- supports newer renderer/view-model layouts;
- deduplicates by video id;
- orders by viewport position;
- uses multiple title/channel extraction fallbacks;
- diagnostics now expose semantic element counts and visible video samples.

### Field result
Vivaldi v0.1.2 later returned:
```text
search_box: 1
video: 3
```
with real visible titles/channels.

---

## 2026-09-13 — Internal browser pages produced no page snapshot
### Observation
When `vivaldi://extensions` was the active tab, `extension_connected=true` but `site/url/snapshot=null`.

### Classification
Expected browser security behavior, not a Vexi defect. Content scripts cannot operate on protected internal browser pages.

### Diagnostic rule
Always test structured-page snapshots on a normal supported web page, not `chrome://` / `vivaldi://` internal pages.

---

## 2026-09-13 — YouTube media fullscreen OFF misrouted to window minimize
**Severity:** current open Core routing regression

### Evidence
```text
HEARD: сверни это видео.
INTENT action=MINIMIZE entity=None source=window status=AMBIGUOUS
```
And a more explicit phrase was classified as conversation:
```text
HEARD: убери видео с полной экранного режима.
```

### Correct contract
Explicit object scope outranks generic verbs:
`video/player -> MEDIA_FULLSCREEN OFF`, while `browser/window/app -> WINDOW_MINIMIZE`.

### Status
Open in the v0.1.4 Public Preview line; requires additional semantic routing regression coverage.

---

## 2026-09-13 — Windows computer-control behavior differed by elevation level
### Field observation
On the primary machine, `выключи звук на ноуте` returned `CONFIRMED_SUCCESS` after launching Vexi elevated, while some system-control behavior had been unreliable without elevation.

### Classification
Platform permission/integrity behavior requiring explicit capability diagnostics. Do not generalize this as “Vexi always requires administrator rights”.

### Design direction
Run user-mode by default; elevate only narrowly where a specific Windows capability genuinely requires it.

---

## Incident-management rule
Every confirmed failure becomes:
1. a dated incident entry;
2. a regression test or promotion-gate condition;
3. a documented architecture invariant when the failure reveals a systemic flaw.
