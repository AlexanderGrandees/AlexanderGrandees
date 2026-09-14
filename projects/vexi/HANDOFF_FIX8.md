# FIX8 — windowless voice startup, 2026-09-14

Supersedes the FIX7 installer. Scope and architecture remain in HANDOFF_FIX7.md.
User reported console stuck at PAYLOAD_VERIFIED and voice/microphone startup failure.

## Root cause and evidence

The installed runtime recorded STARTUP_FAILED. Direct input validation at 16 kHz mono
int16 and opening the HyperX QuadCast S succeeded. STT small loaded successfully.
Torch's model downloader uses tqdm, which calls sys.stderr.write. Actual pythonw has
sys.stderr=None. A local synthetic file download reproduced AttributeError without any
network dependence. Two real pythonw regression cases prove failure before bootstrap
and byte-exact successful download after bootstrap.

runtime_bootstrap.py supplies missing stdin/stdout/stderr using the Windows null device.
No library output, transcripts or audio are persisted by this bootstrap. The executable
entrypoint initializes it before loading dependencies. Startup markers now include STT/TTS
loading stages and exception class only, without raw exception messages.

Two related installer defects were corrected: Windows venv pythonw redirects to a child
PID, so readiness now uses a unique launch ID rather than equality with wrapper PID.
PowerShell Start-Process -Wait waits for descendants, including the assistant; elevation
now waits for the installer process itself through Process.WaitForExit(). The UAC flow
has not been field-tested after this change; AST parsing alone is not a full UAC PASS.

## Installed repair

Original vexi.py and payload-manifest.json were saved in C:\Vexi.hotfix-backup-20260914-fix8.
The complete vexi.py module and new runtime_bootstrap.py were installed; hashes were
updated. Installed runtime preflight and 83 REGRESSION tests passed. The assistant was
restarted through actual pythonw. Wrapper PID 12680, child PID 9068; marker reports
MICROPHONE_READY with launch_id=fix8-live-check-20260914, matching that child process.
This proves model initialization and input stream opening, not an audible conversation.
The user then confirmed: «Есть ответ и голос» after being asked to say «Векси, привет».
This is a PASS for the greeting field scenario only; other conversational scenarios remain untested.

## Package

Vexi_0.1.5_dev4_FIX8_Installer.zip
SHA256: 9d6a25041f153ce1178501c1ef94d740eb9e7b59f2e11c4ec0b98c9b0253e6d1.
60 payload files. Evidence: installer/evidence/fix8-final and fix8_installer_tests.log.
The initial package regression found a flaky DOCX fixture: rebuilding identical documents
can change ZIP timestamps. The no-op test now reuses the exact original bytes; lifecycle
production code is unchanged. Initial failure is retained in installer/evidence/fix8.
15 installer regressions include actual windowless Torch downloads and launch correlation.
Do not reuse FIX7 for a fresh installation. Full legacy Router integration remains incomplete;
guest-safe restrictions, ambient DROP and persistent task context remain unchanged.
