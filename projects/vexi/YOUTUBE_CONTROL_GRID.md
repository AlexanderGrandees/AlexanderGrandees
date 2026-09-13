# YouTube Vertical — v0.1.2

## Structure model
`YouTube → Home / Search / SearchResults / Video / Channel / Playlist / Player / Shorts / History / Subscriptions / Comments / Account`.

## Current v0.1.2 execution grid
| Concept | Example voice command | Tier | v0.1.2 |
|---|---|---:|---|
| Open home | «Открой YouTube» | W0 | implemented |
| Search | «Найди на YouTube Marmok CS2» | W0 | implemented |
| Search channel/video | «Найди канал Marmok» | W0 | implemented as search results |
| Open exact visible card by title | «Открой видео Скользкий пол» | W0 | structured DOM required; search fallback only |
| Continue-watching card | «Продолжи просмотр» | W0/W1 | structured DOM required |
| Play/Pause | «Пауза», «Продолжи видео» | W1 | best-effort official shortcut |
| Seek ±10 sec | «На 20 секунд вперёд» | W1 | best-effort official shortcut |
| Fullscreen player | «Видео на полный экран» | W1 | best-effort official shortcut |
| Captions | «Включи субтитры» | W1 | best-effort official shortcut |
| Video mute | «Выключи звук видео» | W1 | best-effort official shortcut |
| Player volume ±5% | «Видео громче/тише» | W1 | best-effort official shortcut |
| Next/previous | «Следующее видео» | W1 | best-effort official shortcut |
| Miniplayer | «Миниплеер» | W1 | best-effort official shortcut |
| Speed one step | «Ускорь видео» | W1 | best-effort official shortcut |
| Exact speed | «Скорость 1.5» | W1 | deferred until structured player state |
| Read video title/channel/time | «Что играет?» | W0 | deferred until structured player state |
| Like / Subscribe / Save | explicit command | W2 | deferred structured DOM |
| Comment | explicit text + confirmation policy | W3 | deferred |
| Purchases / memberships / account security | — | W4 | blocked default |

## Official desktop keyboard layer used for best-effort control
YouTube documents desktop shortcuts including `K` play/pause, `M` mute, `J/L` ±10 seconds, `F` fullscreen, `C` captions, `Shift+N/P` next/previous, `I` miniplayer, Up/Down volume ±5%, and speed controls with `>` / `<`. The player may need focus, so v0.1.2 reports these as `SENT_NOT_CONFIRMED` until CDP/accessibility can verify focus and player state.

## Structured adapter target
Future `YouTubeStructuredAdapter` should expose:
- active page type;
- visible result cards (`title`, `channel`, `href`, `position`);
- active video (`id`, `title`, `channel`, `duration`, `currentTime`);
- player state (`playing/paused/buffering`, volume, mute, rate, captions, fullscreen);
- authenticated action targets (like/subscribe/save/comment) under W2/W3 policies.

Preferred implementation order: CDP/DOM → accessibility tree fallback → visual agent fallback. Coordinate clicking is not a canonical route.

## Safety / truth rules
- Search results are not the same as opening a requested video.
- Sending a shortcut is not verified player success.
- Account mutation requires explicit user intent.
- Purchase/security workflows are not inherited from ordinary UI control.

## v0.1.2 structured page controls
- Enumerate visible video cards on HOME and SEARCH_RESULTS through Browser Bridge.
- Resolve by ordinal (`первое/второе/...`), title, channel and spatial references (`слева/справа/по центру/снизу`).
- Open resolved card and verify transition to a YouTube VIDEO route.
- If two candidates score too closely, return AMBIGUOUS and ask instead of guessing.
- Structured HTML5 media readback/control: play, pause, seek, mute/unmute, volume, playback rate; YouTube controls for fullscreen/captions/next/miniplayer when available.
- Keyboard shortcuts remain fallback and must report SENT_NOT_CONFIRMED when exact state is not observable.
