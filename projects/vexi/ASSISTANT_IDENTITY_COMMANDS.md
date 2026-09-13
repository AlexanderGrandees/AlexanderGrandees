# Vexi assistant identity commands

The internal product/component identity remains `vexi`. User-facing assistant name and wake aliases are configurable and stored separately from version/build identity.

## Intents

- `GET_ASSISTANT_NAME`
- `SET_ASSISTANT_NAME`
- `SET_PRIMARY_WAKE_NAME`
- `ADD_WAKE_ALIAS`
- `REMOVE_WAKE_ALIAS`
- `LIST_WAKE_ALIASES`
- `RESET_ASSISTANT_NAME`

## Natural command examples

- `Как тебя зовут?`
- `Какое у тебя имя?`
- `Теперь тебя зовут Луна.`
- `Смени имя на Луна.`
- `Запомни, твоё имя теперь Луна.`
- `Зови себя Луна.`
- `Поставь основное имя Луна.`
- `Добавь обращение Нова.`
- `Реагируй ещё на Нова.`
- `Какие имена ты слушаешь?`
- `Убери обращение Нова.`
- `Не реагируй больше на Нова.`
- `Верни имя Векси.`
- `Сбрось имя ассистента.`

## Data model

```text
assistant_display_name = "Vexi"
primary_wake_name = "Векси"
wake_aliases = ["Векси", "Vexi", "Veksi"]
```

## Behavior

- `assistant_display_name` controls the name used in TTS/UI.
- `primary_wake_name` is the preferred spoken wake name.
- `wake_aliases[]` contains alternate accepted wake forms.
- Renaming never changes internal component IDs, install paths, plugin IDs, protocol names, or semantic runtime version identity.
- When the display name changes, the new name is automatically added as a wake alias.
- The previous wake name remains temporarily as a fallback until the new name passes a microphone recognition test or the user explicitly removes it.
- `Как тебя зовут?` must read from durable identity memory, never from a hardcoded string.

## Safety / recovery

A wake-name change must never lock the user out of voice activation. At least one recovery path must remain available through the tray/settings UI. Vexi may retain the prior wake name during a validation window, then allow the user to remove it explicitly.

## Regression requirements

- Rename persists across reboot.
- Tray/overlay/TTS use the configured display name while the runtime version remains canonical Vexi semver.
- New wake name activates the assistant.
- Old alias behavior matches user configuration.
- Failed wake-name recognition test does not remove the last working wake alias.
