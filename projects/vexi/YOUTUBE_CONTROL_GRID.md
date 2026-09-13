# YouTube Vertical — Core v0.1.4 / Browser Pack v0.1.2

## Structure model
`YouTube -> Home / Search / SearchResults / Video / Channel / Playlist / Player / Shorts / History / Subscriptions / Comments / Account`.

## Current field status
Confirmed on the primary Windows + Vivaldi setup on 2026-09-13:

```text
Browser Pack installed: true
extension_connected: true
site: youtube
page_type: HOME
snapshot_age: < 1s
semantic objects:
  search_box: 1
  video: 3
```

Visible video cards included real `position`, `title` and `channel` values from the current viewport.

Confirmed voice actions:

```text
"открой второе видео"
-> structured ordinal selection
-> CONFIRMED_SUCCESS

"весь экран"
-> active YouTube player fullscreen ON
-> CONFIRMED_SUCCESS
```

Current open regression:

```text
"сверни это видео"
-> incorrectly routed to generic window MINIMIZE / AMBIGUOUS

"убери видео с полноэкранного режима"
-> not consistently classified as a media command
```

The required invariant is:
`explicit/current video target > generic window verb`.

## Execution grid
| Concept | Example voice command | Tier | Current state |
|---|---|---:|---|
| Open home | `Открой YouTube` | W0 | implemented; can reach CONFIRMED_SUCCESS when Browser Pack confirms active page |
| Observe page | `Что видишь на YouTube?` | W0 | Browser Pack snapshot works; Core natural routing still being hardened |
| List visible videos | `Какие видео здесь?` | W0 | semantic `VideoCard[]` extraction proven |
| Search | `Найди на YouTube Marmok CS2` | W0 | SearchBox exists in snapshot; full natural flow still under field validation |
| Open visible card by ordinal | `Открой второе видео` | W0 | **field-proven CONFIRMED_SUCCESS** |
| Open exact visible card by title | `Открой видео Autumn Rain` | W0 | structured resolver available; needs broader field matrix |
| Open by channel | `Открой видео от <channel>` | W0 | resolver contract defined; needs field matrix |
| Play/Pause | `Пауза`, `Продолжи видео` | W1 | structured media control foundation; field validation pending |
| Seek | `На 20 секунд вперёд` | W1 | structured media control foundation; field validation pending |
| Fullscreen player ON | `Весь экран` / `Видео на полный экран` | W1 | **field-proven CONFIRMED_SUCCESS** |
| Fullscreen player OFF | `Убери видео с полного экрана` | W1 | **open Core routing regression** |
| Captions | `Включи субтитры` | W1 | available at adapter level; field validation pending |
| Video mute | `Выключи звук видео` | W1 | media-target path exists; field validation pending |
| Player volume | `Видео тише` / `Сделай видео на 40%` | W1 | media-target path exists; readback validation pending |
| Next/previous | `Следующее видео` | W1 | available at adapter level; field validation pending |
| Speed | `Скорость 1.5` | W1 | structured player-state path planned/partial |
| Read current video | `Что играет?` | W0 | needs player-state field validation |
| Like / Subscribe / Save | explicit command | W2 | disabled/deferred under current strict policy |
| Comment / publish | explicit text + confirmation | W3 | disabled/deferred under current strict policy |
| Purchases / memberships / account security | — | W4 | blocked default |

## Browser Pack extraction contract
Browser Pack v0.1.2 no longer relies only on legacy YouTube selectors. The extractor:

- discovers current `/watch` links;
- supports newer renderer/view-model structures;
- deduplicates by YouTube video id;
- sorts visible cards by viewport position;
- extracts title/channel through multiple fallbacks;
- emits a fresh structured snapshot through Browser Protocol v1.

Representative semantic card:

```json
{
  "semantic_type": "video",
  "position": 2,
  "title": "Autumn Rain | 8 Hours of soft rain for Relaxation & Meditation 8 часов",
  "channel": "The Flower of Life",
  "href": "https://www.youtube.com/watch?v=...",
  "visible": true
}
```

## Current-page-first behavior
The canonical path is:

```text
active browser/tab
-> existing YouTube page?
-> fresh snapshot
-> SearchBox / VideoCard[] / Player
-> resolve requested object
-> execute
-> post-action snapshot
-> verify
-> respond truthfully
```

Creating a new YouTube tab is a fallback only when no usable existing YouTube context exists.

## Media scope rules
Three scopes are distinct:

```text
WINDOW_MAXIMIZE / WINDOW_MINIMIZE
BROWSER_FULLSCREEN
MEDIA_FULLSCREEN
```

And audio is also separated:

```text
SYSTEM_AUDIO
MEDIA_AUDIO
```

Examples:
- `сверни браузер` -> window minimize;
- `сверни это видео` while player is fullscreen -> media fullscreen OFF;
- `выключи звук на ноуте` -> system audio;
- `выключи звук видео` -> media audio.

## Safety / truth rules
- Search results are not the same as opening the requested video.
- A sent browser/keyboard action is not a verified player success.
- Account mutation requires explicit policy approval and post-action verification.
- Financial/security/purchase workflows are not inherited from ordinary UI control and remain denied in the current profile.

## Next regression matrix
1. `что видишь на YouTube?`
2. `найди X` using the active SearchBox rather than URL-only fallback.
3. `что нашла?`
4. `открой первое/второе`.
5. `весь экран`.
6. `убери с полного экрана`.
7. `видео тише` / `звук видео на 40%`.
8. `выключи звук на ноуте` to verify system/media separation.
9. Repeat the same structured path in Chrome Browser Pack v0.1.2 on a third-party PC.
