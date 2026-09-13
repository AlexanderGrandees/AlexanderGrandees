# Windows / PC Control Grid — Vexi v0.1.2

## Display
| Capability | Voice examples | v0.1.2 | Verification |
|---|---|---|---|
| Brightness read | «Какая яркость?» | implemented for WMI-capable displays | WMI read |
| Brightness set | «Яркость 50%», «Сделай яркость на треть» | implemented | set + readback |
| Brightness delta | «Чуть ярче», «Темнее» | implemented | set + readback |
| Restore brightness | «Верни яркость как было» | implemented session restore | readback |
| HDR toggle | «Переключи HDR» | implemented via Windows Win+Alt+B | not yet state-verified |
| HDR explicit ON/OFF | «Включи HDR» / «Выключи HDR» | blocked until current state reader exists | prevents wrong inverse toggle |
| Display settings | «Открой настройки экрана» | implemented | command sent |
| Resolution / refresh / orientation | — | designed, deferred | DisplayConfig adapter |
| Multi-monitor topology | — | designed, deferred | Query/SetDisplayConfig |

Brightness uses Windows `WmiMonitorBrightnessMethods.WmiSetBrightness` where the panel exposes it. External monitors may require a future DDC/CI adapter.

## Personalization
| Capability | Voice examples | v0.1.2 |
|---|---|---|
| Read wallpaper path | «Какие сейчас обои?» | implemented |
| Set wallpaper by image path | «Поставь обои C:\...\wall.jpg» | implemented |
| Set last-found image | «Найди файл wall.jpg» → «Поставь его на обои» | implemented |
| Restore prior wallpaper | «Верни обои» | implemented for current session |
| Theme / accent / lock-screen wallpaper | — | deferred |

Wallpaper uses the Windows `SystemParametersInfo(SPI_SETDESKWALLPAPER)` path with readback.

## System audio
| Capability | Examples | v0.1.2 |
|---|---|---|
| Read | «Какая громкость?» | implemented |
| Absolute | «50%», «на половину», «на треть», «минимум», «максимум» | implemented |
| Relative | «громче», «тише», «чуть громче», «вдвое тише», «на 20% тише» | implemented |
| Mute | «Выключи звук», «Включи звук» | implemented |
| Restore | «Верни громкость как было» | implemented |

System volume is separate from YouTube/player volume.

## Apps / windows
- open/focus/minimize/maximize/close/terminate/status/path;
- `FOCUS` must preserve normal/maximized/fullscreen state and only restore when minimized;
- File Explorer is verified through real `CabinetWClass/ExploreWClass` windows, never merely by `explorer.exe` existence;
- browser background processes are not equal to a visible browser window;
- context commits only after verified/accepted execution states.

## Filesystem
Read/search/open safe files and known folders; create/copy/move/rename/trash are typed operations. Generic file open blocks executable/script extensions. Permanent deletion remains outside low-risk defaults.

## Planned PC-control horizontals
Power/session (lock/sleep/shutdown/restart), Bluetooth, Wi‑Fi, audio-device switching, microphone/device state, display topology, refresh rate, theme/accent, clipboard, screenshots, notifications, battery/power profile, and Quest device fabric each require dedicated adapters and risk rules; they must not be implemented by arbitrary shell from the LLM.
