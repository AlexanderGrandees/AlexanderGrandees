# FIX10 prerelease checkpoint — 2026-09-17

Status: EXPERIMENTAL, NOT PROMOTED. ZIP prepared and extracted-package checks pass. Default local_dialogue_enabled=false because real Qwen semantic quality failed review.
Package SHA256: 1e3ba43fe8f637b510a3393650954edb1db926a3cf0a174f293ace2c7e0b6b40.
Package: releases/v0.1.5-development/Vexi_0.1.5_dev4_FIX10_Installer.zip.
Test order: installer/README_RU.md.

## Implemented
local_dialogue.py: bounded public-topic grammar, local-only Ollama HTTP adapter, no proxies/redirects/tools, input/output bounds, deadline/cancellation, one in-flight request, revision-safe context, explicit option binding, existing public capability policy.
attention_loop integrates as an opt-in route; retains deterministic FIX9 replies and all protected-action routes. No non-public LOCAL_MODEL permission expansion.
Settings checkbox controls experimental mode. Diagnostics CORE and REGRESSION include dialogue tests.
Context lives in RAM, goal survives pause, explicit forget clears application references. Pausing/forgetting cannot certify wiping model-server memory/OS swap.
The model's replies are never dispatched as actions. Action-claim regex is a supplemental heuristic, not a complete factual verifier.
Generation timeout returns within 60s; a stalled daemon request may retain its bounded payload until its socket timeout finishes. Only one request per client; no invisible retry or remote fallback.
Voice stop during THINKING is not implemented because the existing capture loop is serial. UI mute/exit cancels; TTS barge-in still follows FIX9.

## Evidence
148 foundation tests: installer/evidence/fix10/foundation-tests.log.
15 installer tests: installer/evidence/fix10/installer-tests.log.
63 Python files syntax parsed; 67 payload files; extracted package manifests, Windows PowerShell 5.1, FAST/CORE/DOCUMENT/REGRESSION, DOCX smoke, failure exit, imports/preflight pass: installer/evidence/fix10-package/evidence.json.
Local model synthetic multi-turn requests succeeded at transport level. Semantic quality FAIL: awkward phrasing, repetition, weak fact precision. See installer/evidence/fix10/review.json and model-eval*.json; do not relabel PASS.
Field microphone/game/music tests NOT_RUN. User has not tested FIX10.
First unelevated install attempt stopped before staging due to ACL on C:\Vexi.install.lock. OS RunAs installer started; final install/launch result is recorded separately in install-observation.json after verification.

## Explicit scope gaps
This is not unrestricted natural conversation. First-turn public grammar and continuation grammar are intentionally bounded. Generic private/personal speech is not sent to the model.
No speaker verification or reliable music/game source separation. Matching background phrases can trigger allowed continuations. Disable followups for strict wake-only mode.
Task facts/ExpectedResponse framework and general conversational privacy route remain future work from ENGINEERING_LOCAL_DIALOGUE.md.
No stable release until quality and field evidence pass. Follow backup → coherent replacement → regression → launch → field → rollback.

## Roborock follow-up
User owns Q7 L5+, Roborock app. Network: shared Wi-Fi → laptop → laptop hotspot → vacuum. App shows connected.
App connectivity is not proof of local control. Candidate route Vexi → Home Assistant → Roborock; current HA documentation says Q-series compatibility varies and maps/routines use cloud.
Source: https://www.home-assistant.io/integrations/roborock/
Do not claim Q7 L5+ supported before discovery/read-only state test. No device commands, scans, credential access or pairing were performed. No robot adapter in FIX10.
User may open same conversation on laptop; re-check execution host before touching laptop resources. Opening a synced chat does not establish tool access to that laptop.

