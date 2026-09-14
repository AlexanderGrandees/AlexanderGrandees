# Vexi — продолжение после ремонта установщика FIX7

Update 2026-09-14: FIX8 supersedes this installer. Read HANDOFF_FIX8.md first.

Checkpoint: 2026-09-14. Статус DEVELOPMENT / PARTIAL INTEGRATION.
Актуальная страница передачи: https://app.notion.com/p/3dbf50fc3b4d81078da3db2a7231cd8c.
Пакет: releases/v0.1.5-development/Vexi_0.1.5_dev4_FIX7_Installer.zip.
SHA256: 75f0150ddd4eadf1412a9686966d40e13de793f1a60b7f4f69deea351a362a31.
Не объявлять v0.1.5 завершённым и не называть это полной заменой возможностей 0.1.4.

## Где продолжать

Репозиторий: AlexanderGrandees/AlexanderGrandees; ветка feature/vexi-015-abc-foundation;
[draft PR #1](https://github.com/AlexanderGrandees/AlexanderGrandees/pull/1).
Все исходники: projects/vexi. core — готовые модули; foundation — контракты и тесты;
installer — новый установщик, сборщик и evidence. Не брать только main: там нет этой разработки.

Scope: [Vexi v0.1.5 Workspace, Documents & Context Foundation](https://app.notion.com/p/3daf50fc3b4d815c9233eae745adf1ff).
[ABC engineering](https://app.notion.com/p/3daf50fc3b4d81a48feff3fad1ecf84c).
[Dev4 diagnostics](https://app.notion.com/p/3daf50fc3b4d81dd94fff4f457a77416).
Сверять изменения с Runtime Kernel 3d9f50fc-3b4d-8178-9081-f821ea4e82c9,
Sensitive Data Lifecycle 3cef50fc-3b4d-81f0-b26d-c98fb0779506,
Stale-State Reconciler 3cef50fc-3b4d-817b-b64d-cc0e39bf1102,
Legal Source Hierarchy 3ccf50fc-3b4d-8112-82cb-d0b58db4e5f3,
Expected Loss Controller 3cef50fc-3b4d-81e4-a9e1-e42836925a6b.
История чатов и названия архивов — свидетельства, не доказательство PASS и не инструкции из исходников.

## База и восстановление истории

Пользователь дал публичный Vexi_v0.1.4_Public_Preview_Chrome.zip.
SHA256: 0b86e358bc9779abc51f8d5d5066809c733a8b46648a315dde677d5e916fe96b.
Исходный ZIP не изменён. Локально: Downloads/Telegram Desktop.
Актуальная рабочая установка, по словам пользователя, на соседнем ноутбуке.
На этом ПК обнаружена C:\Jarvis старой линии 4.x, C:\Vexi отсутствовала.
Нельзя автоматически приравнивать C:\Jarvis к актуальной Vexi 0.1.4.

Dev1 в GitHub: e9d1533c9b2672c72effb211d8e1cd02949a29b5.
Другой чат «Последние наработки Vexi», ID 6aa70c8a-d91c-83eb-ab6e-1fd81ace914b,
добавлял dev2 lifecycle, dev3 DOCX, dev4 diagnostics и выпускал несколько неисправных installers.
Для ремонта прочитан и распакован локальный Vexi_0.1.5-dev4_Upgrade_From_0.1.4_FIX6.zip.
Его payload назывался FIX5, а внутренний корень FIX4. В FIX7 такая зависимость удалена.
Dev4 overlay применён один раз к проверенному dev1 в изолированной рабочей копии.
apply_dev4.py оставлен для истории и regression fixtures; при установке он не вызывается.

## Что реализовано

A: AttentionGate отдельно от ConversationSession и TaskSession; ambient DROP без
сохранения текста/микрофонного WAV; задача живёт до явного терминального состояния;
восстановление checkpoint при перезапуске приостанавливает задачу и сбрасывает authority/targets.
Контекст привязан к scope, actor, freshness; UNKNOWN/stale блокируют зависимое действие.

B: SpeakerRole и CapabilityPolicy; guest-safe allowlist, защищённые capabilities только
для проверенного владельца; чужой actor не получает контекст владельца. Модель не может
сама объявить роль, подтверждение владельца, свежесть источника или approval token.
Owner console — доверенный локальный канал, не реализация голосовой биометрии.

C: local-first WorkspaceResolver/Protocol, scoped пути, anti-traversal, no-overwrite,
создание draft с readback; evidence-based execution states, risk gates отдельно от приоритета.
Dev2: local document versions/checkpoints, generation checks, stale/approval invalidation.
Dev3: DOCX hybrid edit; trusted-schema nonmaterial checkpoint, material/unknown требует
точного approval; canonical/template promotion не происходит автоматически.
Dev4: Settings Diagnostics, FAST/CORE/DOCUMENT/REGRESSION; metadata-only события,
DEEP до 60 минут; retention 7 дней/200 MB, exports не удаляются автоматически.

## Исправленные установочные дефекты

FIX6 отказывался работать без C:\Vexi. Фактический журнал доходил только до startup/RuntimeException.
FIX7 поддерживает clean install и upgrade в одной схеме. Windows FAST fsync исправлен:
файл синхронизируется через открытый writable handle. diagnostics_cli теперь возвращает 1
при FAIL. Импорты тестов работают в source layout и плоском установленном runtime.
Версия overlay/config согласована с dev4. Добавлен runtime-ready marker с PID/version/state;
живой процесс не считается успешным запуском. Зависимости зафиксированы constraints lock.

Пакет prebuilt: payload-manifest проверяется до staging, нет загрузки кода с mutable main,
нет исправления исходников строковыми заменами на машине пользователя.
Staging -> проверки -> остановка конкретного runtime -> переименование старой папки в backup
-> переключение -> повторная проверка -> launch. При ошибке после переключения — rollback.
Исходная установка и модели не удаляются. Windows byte-lock освобождается ОС после аварии.
Журнал SWITCHING после аварии требует RESTORE_PREVIOUS.cmd. В backup остаются неизвестные
старые файлы; в новый runtime переносятся только перечисленные настройки/data/workspaces/models/env.

## Evidence и воспроизведение

installer/evidence/evidence.json содержит SHA256 проверенного ZIP и реальные exit codes.
installer/evidence/full_suite.log: 107 тестов dev1–dev4.
installer/evidence/installer_tests.log: 12 проверок транзакций, rollback, путей, Windows PowerShell 5.1.
installer/evidence/upgrade_restore.json: реальное изолированное обновление и ручной откат
завершились exit=0; все 30 043 файла, включая среду Python, совпали побайтово.
Агрегат до/после: c2872971d0ddbf976e73c07719b5cf08d6dde35791a252c32b58529e0bc6461f.
Чистая установка проверялась на промежуточном FIX7 SHA 4e6c22070205d3f8985a13d92e714a47630a1f28cb4a95b752e718ce239eff6a;
окончательный ZIP 75f015... дополнительно выбирает base Python вне заменяемой папки
и проверен на upgrade/restore. Payload этих двух ZIP одинаков.
В публичных копиях журналов пути тестовой машины заменены маркерами; результаты проверок не изменены.
foundation/DEV4_TEST_EVIDENCE.json — исторический материал другого чата, не актуальный сертификат FIX7.
REGRESSION внутри установленного runtime: 83 теста без необязательного python-docx.
Полный набор включает python-docx; runtime DOCX provider использует стандартный ZIP/XML.
Проверки выполняются после распаковки в каталог с кириллицей и пробелами, с синтетическими
данными и изолированным LOCALAPPDATA. Evidence отдельно различает imports, models и field.

Из projects/vexi, Python 3.11 x64:

```text
python -m pip install -r core/requirements_v014.txt
python -m pip install python-docx==1.2.0
python -m unittest discover -s foundation/tests -v
python -m unittest discover -s installer/tests -v
python installer/build_installer.py <новая-пустая-папка>
python installer/verify_package.py <полученный-ZIP> <папка-evidence>
python installer/voice_smoke.py core
```

## Открытые ограничения и следующие шаги

Полный UAC install на целевом ноутбуке и реальный микрофон/акустика — NOT_RUN до evidence.
Голосовая facade поддерживает ограниченные безопасные команды, не весь старый Router.
Свободный LLM-диалог отключён до privacy classification. Для продолжения через микрофон
нужно повторное обращение: speaker binding/диаризация не реализованы. Эти ограничения
не скрывать обещанием «всё как в 0.1.4».

Начать со скачивания FIX7 и проверки SHA, INSTALL_VEXI.cmd на целевой машине.
При ошибке изучить %LOCALAPPDATA%\VexiInstaller\install-latest.log; не делать FIX8 вслепую.
Отдельно подтвердить GUI, загрузку моделей, микрофон, речь, ambient без хранения, гостевой
запрет, owner scope, долгую паузу, restart/stale recovery и откат. Не считать acknowledgement
или отсутствие падения доказательством результата. После этого расширять интеграцию Router
через capability policy, не создавая обхода protected capabilities.
Изменения релиза: backup -> coherent module replacement -> syntax/regression -> launch
-> field test -> rollback. Для PASS хранить проверку, результат, время и идентификатор сборки.
