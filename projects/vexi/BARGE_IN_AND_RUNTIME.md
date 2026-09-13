# Vexi v0.1.2 — Barge-In & Runtime Identity

## Interruptible TTS
During speech, Vexi monitors the microphone concurrently. If independent user speech remains above an adaptive threshold long enough, Vexi stops TTS, preserves the captured utterance and routes it as the next turn.

States:
`SPEAKING -> BARGE_IN_CANDIDATE -> INTERRUPTED_BY_USER -> LISTENING`.

Initial safeguards:
- arm delay before interruption detection;
- adaptive echo baseline learned from early speaker leakage;
- minimum continuous speech duration;
- post-interrupt recording continues until silence;
- if microphone duplex monitoring fails, Vexi falls back to normal playback rather than crashing.

## Addressing policy
`name_address_mode = occasional`.
The stored user name is identity memory, not a prefix. Routine command confirmations should not use the name.

## Runtime identity
Single canonical source: `version.py`.
Every production surface must show the same identity:
- tray tooltip/menu;
- overlay;
- voice command `какая у тебя версия?`;
- startup log with version/channel/build/PID/path;
- installer-created shortcut descriptions;
- `runtime_identity.json`.

## Console policy
Production runtime launches `pythonw.exe` directly. A console exists only for the explicitly named `Vexi v0.1.2 DEBUG` shortcut.
