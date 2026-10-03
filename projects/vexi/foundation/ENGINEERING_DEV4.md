# Vexi 0.1.5.dev4 - Diagnostics, Self-Test and Export

Status: DEVELOPMENT MODULE / NOT A LIVE UPDATE.

## Purpose
Give pre-release Vexi a local black-box recorder that is useful for debugging without recording private content. The owner can open one UI tab, run tests, open the log folder, build a sanitized ZIP, and send that ZIP for analysis.

## Diagnostic root
Windows default: `%LOCALAPPDATA%\\Vexi\\Diagnostics`.

Folders:
- `runtime/` safe structured runtime events
- `incidents/` recovery/crash/self-test incidents
- `selftests/` immutable self-test summaries
- `state/` environment + latest self-test + temporary deep-mode state
- `exports/` user-created diagnostic ZIP bundles; never auto-deleted by log retention

## UI
New Settings tab: `Диагностика`.

Actions:
- FAST / CORE / DOCUMENT / REGRESSION self-test
- open diagnostics folder
- open exports folder
- build `ZIP for ChatGPT`
- temporary DEEP diagnostics for 60 minutes
- recent file list and last test status

## Privacy contract
Diagnostics rejects and never persists metadata fields representing transcript, text, content, prompt, response, secret, token, password, email/message, path/filename, payload, document body, traceback/stack, raw query or utterance.

Arbitrary Python logging is ignored. The handler accepts only explicitly structured diagnostics and the three pre-existing metadata-only `vexi.foundation` templates. Exception messages and tracebacks are not persisted. Crash markers record exception type only.

DEEP mode does not relax these rules. It is a time-limited request for denser safe metadata only.

## Retention
- runtime/incidents: 7 days by default
- combined runtime/incident cap: 200 MB
- log segment target: 5 MB
- exports: manual lifecycle, never removed by automatic retention

## Self-test modes
- FAST: diagnostics root, redaction gate, metadata roundtrip, deep-mode state
- CORE: foundation + recovery tests when sources are installed
- DOCUMENT: lifecycle + DOCX + diagnostics tests
- REGRESSION: all `foundation/tests/test*.py`

Self-test files contain test IDs and exception type only. No exception message/traceback is exported.

## Export contract
The export ZIP includes only managed runtime/incident/self-test/state files, `bundle_summary.json`, and `manifest.json`. Every included file gets SHA-256 + size in the manifest. Existing exports are never recursively included.

## Runtime wiring
`vexi.py` installs the diagnostics manager after existing metadata-only logging setup. The diagnostics handler is independent of the legacy `vexi.log` handler. Failure to initialize diagnostics must not block assistant startup.

Document lifecycle and headless DOCX controller emit safe events for register/autosave/checkpoint/canonical/stale/lifecycle, edit plan, approval wait, verified edit, and automatic recovery.

## Installation boundary
`apply_dev4.py` is for an isolated exact dev1 source tree only. It validates Git blob identities for `vexi.py`, `settings_ui.py`, and `version.py`, backs them up, then applies the dev4 bootstrap/UI/version patch. It refuses unknown baselines.


## Installer FIX3 baseline validation
- The full pinned dev1 source ZIP SHA-256 is the authority for source identity.
- Installer writes `.dev1-source.sha256` into staging only after the archive hash matches.
- `apply_dev4.py` requires that marker and then validates semantic anchors before mutation.
- Raw Git-blob hashes are no longer used as the mutation gate because CRLF/LF packaging differences can produce false mismatches for the same verified source archive.
- Bootstrap failures emit a short machine-readable `DEV4_BOOTSTRAP_ERROR <code>` without raw payloads.


## FIX4 installer compatibility notes
- Runtime installer preserves the proven v0.1.4 installed layout (`C:\Vexi\vexi.py`, not `C:\Vexi\core\vexi.py`).
- Source-stage tests run before runtime flattening.
- In-app DOCUMENT/REGRESSION self-tests use the stdlib-only synthetic DOCX test and do not require the test-only `python-docx` package.
- Exhaustive `test_docx_provider.py` remains available as optional engineering evidence when `python-docx` is installed.
