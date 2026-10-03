# FIX10a continuation checkpoint — 2026-09-20
Installed C:\Vexi build fix10a-conversation-routing; local_dialogue_enabled=true, public_followups_enabled=true, name_address_mode=rare.
Backup: C:\Vexi.backup-20260917_145159_640e2ce7.
151 foundation tests pass; extracted package checks pass; actual post-install regression 127 tests, zero failures/errors.
Synthetic actual Silero/Whisper/wake/canonicalizer/bridge checks now answer all four public test phrases.
Reproduced genuine failure: "что ты делаешь" was missing from smalltalk routing. Added full-utterance normalization and bounded spoken variants, retaining compound-command rejection. Unknown routes now say unsupported/unrecognized rather than falsely requiring owner approval.
Before-synthetic harness omitted command-leading filler cleanup; its "ну..." failure must not be treated as proof of that failure in the complete old voice loop. The "что ты делаешь" regression is independently confirmed.
No actual human microphone field confirmation yet. Exact "как дела" and "что делаешь" already worked in synthetic baseline; user's report of universal failures still needs field verification.
FIX10 local model semantic quality remains FAIL/experimental; this patch does not solve model repetition or unrestricted conversation. No security permission expansion. Ambient text remains absent from application logs.
Package SHA256: 44c7005622d4a418b208688188879fdda4cf0fea2ff83bfdd0c58f03e1644203.
ZIP: releases/v0.1.5-development/Vexi_0.1.5_dev4_FIX10a_Installer.zip.
Test now: wake + "как дела", unaddressed "что ты делаешь", "хмм", wake + "расскажи о космосе", "объясни проще". Record actual responses; no field PASS before user evidence.
Desktop "Vexi — Администратор.lnk" points to C:\Vexi\.venv\Scripts\pythonw.exe with C:\Vexi\vexi.py and RunAs flag.
Roborock Q7 L5+ discussion remains separate: Roborock app; shared Wi-Fi → laptop hotspot → vacuum. No robot implementation/pairing/device command has been performed.

