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
Russian STT aliases became `???????`, while application/site entity resolution still worked.

Deterministic evidence before repair:
```text
открой vivaldi   -> False
открой проводник -> False
открой youtube   -> False
```

### Cause
Encoding corruption during direct PowerShell text manipulation.

### Recovery
A direct block replacement plus Python syntax check restored deterministic routing:
```text
открой vivaldi   -> True
открой проводник -> True
открой youtube   -> True
```

### Policy change
Production Python modules are no longer modified through ad-hoc search/replace PowerShell patches.

---

## 2026-09-13 — Regex Unicode replacement failure
**Symptom**
```text
re.error: bad escape \u
```

### Cause
Unicode escape text was interpreted by the regex replacement engine.

### Lesson
Avoid regex replacement for source-code surgery when replacement content contains escape sequences.

---

## 2026-09-13 — Patch-generated Python syntax failure
### Symptom
A live text replacement inserted invalid literal escape/boundary text and produced a Python `SyntaxError`.

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
### Symptom
"Open/focus Vivaldi" could pull the browser out of fullscreen/maximized mode.

### Cause
`SW_RESTORE` was used as part of generic focus logic even when the window was not minimized.

### New invariant
`FOCUS != RESTORE != MAXIMIZE != BROWSER_FULLSCREEN`.

Only minimized windows should be restored before focus.

---

## 2026-09-13 — Natural-language modal open not recognized
Direct executor diagnostics showed:
- `открой youtube` handled;
- `можешь открыть youtube` not handled by the old parser.

### Lesson
Intent must be normalized semantically, not matched only by narrow verb forms.

---

## 2026-09-13 — Audio backend vs semantic routing split
### Evidence
Direct Windows master-volume test succeeded with read/set/readback/restore (`~60% -> ~70% -> ~60%`).

### Failure domain
Natural phrases such as "громкость на полную" / "на половину" were not consistently routed to the working adapter.

### Architecture response
Introduce a reusable property engine:
`READ -> COMPUTE -> SET -> READBACK -> VERIFY`.

---

## 2026-09-13 — Narrative text executed as commands
Examples observed in field testing:
- reports like "страница не открылась" could trigger action routing;
- descriptions containing "полный экран" could trigger fullscreen behavior;
- statements like "Vivaldi открыт" could be misclassified as status/action intent.

### Fix contract
Classify utterances before execution:
`COMMAND | QUESTION | REPORT | CORRECTION | EXPLANATION | CONVERSATION`.

Only executable command/question intents may reach PC/browser tools.

---

## 2026-09-13 — Duplicate unsupported response
A single unsupported media request produced duplicate `UNSUPPORTED` responses.

### Fix contract
One `intent_id` -> one execution -> one result -> one spoken response.

---

## 2026-09-13 — v0.1.2 installer r1 parser failure
**Status:** failed; previous runtime preserved / rolled back.

### Evidence
- active runtime remained v0.1.1;
- `version.py` remained `0.1.1`;
- Windows PowerShell 5.1 reported parser failures in `install_v012.ps1`.

### Root-cause class
Nested inline `python -c` / quoting in the PowerShell installer was not safe under Windows PowerShell 5.1.

### Response
- persistent installer transcript;
- pre-copy syntax validation;
- explicit installed-version check;
- transactional backup/rollback;
- promotion requires `Vexi v0.1.2 ready` evidence.

---

## 2026-09-13 — v0.1.2 installer r2 preflight failure
**Status:** failed before touching current installation.

### Observed error
```text
Unexpected token '^'
```

### Root cause
CMD caret escape characters were passed literally into the quoted PowerShell preflight command.

### Safety result
The working v0.1.1 installation was not modified.

---

## 2026-09-13 — v0.1.2 installer r3
**Status:** current candidate / awaiting field confirmation.

### Change
- dedicated `preflight_v012.ps1` replaces inline `powershell -Command` parser logic;
- exact parser line/column reporting;
- stable non-zero preflight exit code;
- hardened UAC relaunch quoting.

### Promotion evidence required
- `C:\Vexi\version.py` reports `0.1.2`;
- runtime log contains `Vexi v0.1.2 ready`;
- tray/overlay/voice report the same version;
- normal startup leaves no console window visible.

---

## Incident-management rule
Every confirmed failure becomes:
1. a dated incident entry;
2. a regression test or promotion-gate condition;
3. a documented architecture invariant when the failure reveals a systemic flaw.
