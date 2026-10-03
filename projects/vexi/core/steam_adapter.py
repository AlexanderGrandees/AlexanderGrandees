import logging
import time

from window_manager import enum_windows, matching_processes


class SteamAdapter:
    def __init__(self, registry, memory=None):
        self.registry = registry
        self.memory = memory

    def processes(self):
        return matching_processes(self.registry.process_names('steam'))

    def windows(self):
        procs = self.processes()
        return enum_windows([p.pid for p in procs]) if procs else []

    def inspect(self):
        wins = self.windows()
        picker = False
        profiles = []
        # Best-effort UIA. Steam may expose profile cards differently by version.
        try:
            from pywinauto import Desktop
            for p in self.processes():
                for w in Desktop(backend='uia').windows(process=p.pid):
                    texts = []
                    try:
                        for c in w.descendants():
                            txt = (c.window_text() or '').strip()
                            if txt:
                                texts.append(txt)
                    except Exception:
                        pass
                    blob = ' | '.join(texts).lower()
                    if any(x in blob for x in ('кто играет', 'who is playing', "who's playing")):
                        picker = True
                        # Candidate profile texts: short unique strings not UI labels.
                        ignore = {'steam', 'кто играет?', 'кто играет', 'who is playing?', 'who is playing', '+',
                                  'при каждом запуске steam спрашивать, какой аккаунт использовать'}
                        for txt in texts:
                            if txt.lower() not in ignore and 1 < len(txt) < 60 and txt not in profiles:
                                profiles.append(txt)
        except Exception as exc:
            logging.debug('Steam UIA inspect unavailable: %s', exc)
        return {
            'process_running': bool(self.processes()),
            'visible_windows': wins,
            'account_picker_detected': picker,
            'available_saved_profiles': profiles[:10],
        }

    def choose_profile(self, requested):
        requested = (requested or '').strip().lower()
        if requested in {'основной', 'мой основной', 'default'} and self.memory:
            requested = str(self.memory.store.get('device', 'steam_default_profile', '') or '').lower()
        if not requested:
            return 'AMBIGUOUS', 'Не знаю, какой Steam-аккаунт выбрать.'
        try:
            from pywinauto import Desktop
            for p in self.processes():
                for w in Desktop(backend='uia').windows(process=p.pid):
                    for c in w.descendants():
                        txt = (c.window_text() or '').strip()
                        if txt and requested in txt.lower():
                            try:
                                c.click_input()
                            except Exception:
                                c.invoke()
                            time.sleep(1.0)
                            state = self.inspect()
                            if not state['account_picker_detected']:
                                if self.memory and self.memory.consent():
                                    self.memory.store.set('device', 'steam_last_profile', txt, source='runtime', user_confirmed=False)
                                return 'CONFIRMED_SUCCESS', f'Выбрала Steam-профиль {txt}.'
                            return 'SENT_NOT_CONFIRMED', f'Выбор профиля {txt} отправила, но Steam ещё не подтвердил вход.'
        except Exception as exc:
            logging.exception('Steam profile selection failed: %s', exc)
            return 'FAILED', 'Не смогла выбрать Steam-профиль через интерфейс.'
        return 'NOT_FOUND', f'Не нашла сохранённый Steam-профиль «{requested}».'
