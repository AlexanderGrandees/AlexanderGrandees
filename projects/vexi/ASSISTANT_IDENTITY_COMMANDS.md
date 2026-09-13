# Vexi assistant identity commands

The internal product/component identity remains `vexi`. The user-facing assistant name is a durable, configurable identity and, beginning with v0.1.3, the new name **fully replaces** the previous wake identity.

## Intents

- `GET_ASSISTANT_NAME`
- `SET_ASSISTANT_NAME`
- `RESET_ASSISTANT_NAME`

## Natural command examples

- `Как тебя зовут?`
- `Какое у тебя имя?`
- `Теперь тебя зовут Луна.`
- `Смени имя на Луна.`
- `Поменяй имя на Луна.`
- `Твоё имя теперь Луна.`
- `Зови себя Луна.`
- `Верни имя Векси.`
- `Сбрось имя ассистента.`

## Data model

```text
internal_id = vexi
display_name = "Луна"
wake_names = ["Луна"]
```

## v0.1.3 behavior

- A new name changes both TTS/UI identity and the accepted wake identity immediately.
- The previous wake name is not silently retained as an alias.
- Renaming never changes internal component IDs, install paths, plugin IDs, Browser Protocol IDs, or semantic runtime version.
- Tray, overlay, TTS, activation and STT vocabulary read the durable current identity dynamically.
- `Как тебя зовут?` reads the durable identity state, never a hardcoded string.
- Recovery from a poorly recognized custom wake name is always available through local Settings UI; recovery does not depend on the old wake word.

## Recognition safety

Wake-name fuzziness may generate candidates, but similarity alone must not invoke an unrelated capability. The Speech Canonicalizer uses semantic-family context, confidence thresholds and margin checks before repair. Ambiguous text stays conversational/ambiguous instead of executing a tool.

## Regression requirements

- Rename persists across reboot.
- Tray/overlay/TTS use the configured display name while runtime version remains canonical Vexi semver.
- The new wake name activates the assistant.
- The old wake name no longer activates after rename.
- Settings UI can reset the identity without voice activation.
- Similar-sounding unrelated terms do not trigger tool actions.
