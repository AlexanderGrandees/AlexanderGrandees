# Vexi FIX9 — speech, public conversation context and name preferences

Checkpoint: 2026-09-15. DEVELOPMENT / PARTIAL INTEGRATION.
Notion checkpoint: https://app.notion.com/p/3dcf50fc3b4d8104bc55f651b82ea01b.
Read this first, then HANDOFF_FIX8.md and HANDOFF_FIX7.md for foundation and installer history.

## User decisions

- Ignore «хмм», «мм», «ии», hesitations and unrelated background speech.
- After addressing Vexi, continue conversation without repeating its name.
- Offer «Обычно» or «Почти никогда» for addressing the user by name; default to «Почти никогда».
- The user tested while music was playing and STALKER was running. Do not claim universal
  background-noise robustness from this one report.

## Implementation

speech_input.py filters pure hesitations and punctuation before activation, canonicalization
and routing. It strips only leading fillers; meaningful short words, numbers and dictated
payload after the first meaningful token are preserved. A wake word plus only fillers is
dropped without creating a task, speaking, or extending the reply window.

PublicDialogue keeps a volatile public reply context for 90 seconds after an answer.
Recognized acknowledgements are silent and can extend this window; noise cannot.
Supported public questions, selected public-video commands, negative execution feedback,
repeat and close controls can continue without another wake word. Private/arbitrary commands
are excluded; media still passes its existing public-target freshness and capability checks.
This is not speaker authentication, verified owner authority or an approval mechanism.
No raw ambient transcripts are saved. Only deterministic public assistant replies are
available for public repeat; private output is not placed in that buffer.

«Стоп» ends speech/listening continuation without completing the unresolved task.
«Всё, спасибо» / «задача завершена» explicitly closes the task. Reply-window expiry does
not delete the task. Mute/recovery clears the volatile public dialogue state.

TTS classifies an apparent interruption locally. Hums, acknowledgement sounds and unaddressed
background utterances resume the remaining spoken output instead of producing a reply.
There may be a short pause while classification runs. Audio stays in RAM; no new raw log
or microphone recording store is introduced.

After the user found «как дела?» unsupported, fixed public small-talk routes were added:
«как дела», «как ты», «как настроение», «что делаешь», «чем занята», «что ты умеешь».
Short wellbeing replies are interpreted only when that response is expected. Their public
answers can be repeated. This does NOT implement arbitrary free-form LLM conversation.

speech_preferences.py reads/writes the existing local config atomically and preserves other
keys. Settings → Ассистент → Разговор exposes the two name-use modes and the public followup
toggle. Changes apply on the next turn. The model system prompt reads the selected name rule;
the current deterministic guest voice facade does not inject owner names. Personal owner
memory is not enabled by the setting. Assistant wake-name remains a separate preference.

## Installed state and rollback

Applied to C:\Vexi with backups in C:\Vexi.hotfix-backup-speech-fix9.
Complete replaced modules and config/manifest were backed up; new speech_input.py,
speech_preferences.py and test_speech_input.py did not exist in the old version.
To roll back, stop the specific Vexi process, restore backed-up files and old manifest,
and remove only these known newly introduced files if returning completely to FIX8.
Do not merge arbitrary old code, erase workspace data or delete C:\Jarvis.

Installed manifest/preflight passed, and the final installed REGRESSION contains 98 tests.
The final runtime reported MICROPHONE_READY with launch_id=fix9-ready-20260914 on 2026-09-14.
On 2026-09-15 no pythonw process was found; that marker is historical, not proof that the
assistant is currently running. Always verify a live matching process/launch before READY.

## Evidence

Final ZIP: Vexi_0.1.5_dev4_FIX9_Installer.zip.
SHA256: 1b70998b9e9628a1ab7855bd606300d420171bf3aca64a2b76c27e19ed0680d1.
63 payload files; 59 Python syntax checks; 122 module tests; 15 installer regressions.
Final extraction/manifest, actual PowerShell 5.1 preflight, all diagnostic modes,
DOCX smoke, failure exit code and runtime preflight passed.
See installer/evidence/fix9-verified and installer/evidence/fix9/installer_tests.log.

The first FIX9 verification failed because the test harness imported the runtime before
strict package verification and thereby created a runtime log inside the extraction.
Verification now checks the pristine extraction first; manifest restrictions were not relaxed.
The original failure remains in installer/evidence/fix9. This is separate from user field evidence.

User explicitly confirmed «Да, всё так» for: wake greeting → hums ignored → unaddressed
version question → repeat. Treat only that sequence as user-confirmed PASS.
They then reported «как дела» received no answer; routes were added and tested automatically.
No user confirmation of the final small-talk/music/game scenario has arrived yet: NOT_RUN.
Settings control presence and default selection were checked using real Tk widgets;
save/readback and normal/rare prompt changes were checked against synthetic config.

## Next work

1. If needed, start the installed Vexi and confirm the new launch marker against its live child PID.
2. Verify «Векси, как дела?» → «нормально» → «повтори» with the real microphone and audible output.
3. Field-check noise/false activation during music and STALKER, plus TTS resume after a hum.
4. Expand real conversation support deliberately: the current whitelist does not fulfil
   arbitrary natural dialogue. Keep model conversation separate from action authorization,
   scoped/private context and owner-only capabilities. Do not solve this with an unrestricted Router bypass.
5. Full UAC installation and installer-console exit after the FIX8 WaitForExit change remain NOT_RUN.

Continue release discipline: backup → coherent replacement → syntax/regression → launch
→ actual field evidence → rollback if needed. Never promote this development branch as stable v0.1.5.
