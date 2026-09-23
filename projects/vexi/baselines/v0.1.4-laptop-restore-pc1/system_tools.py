import ctypes
import logging
import re


def norm(value):
    value = (value or '').lower().replace('ё', 'е').strip()
    return re.sub(r'\s+', ' ', value)


class SystemTools:
    def __init__(self):
        self.previous_volume = None
        self.previous_mute = None
        self._endpoint = None
        self._init_error = None
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER

            device = AudioUtilities.GetSpeakers()
            try:
                endpoint = device.EndpointVolume
            except Exception:
                interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                endpoint = cast(interface, POINTER(IAudioEndpointVolume))
            self._endpoint = endpoint
        except Exception as exc:
            self._init_error = str(exc)
            logging.warning('System audio unavailable: %s', exc)

    def available(self):
        return self._endpoint is not None

    def get_volume(self):
        if not self.available():
            return None
        try:
            return max(0.0, min(1.0, float(self._endpoint.GetMasterVolumeLevelScalar())))
        except Exception:
            return None

    def set_volume(self, value):
        if not self.available():
            return False, None
        value = max(0.0, min(1.0, float(value)))
        current = self.get_volume()
        if current is not None:
            self.previous_volume = current
        try:
            self._endpoint.SetMasterVolumeLevelScalar(value, None)
            actual = self.get_volume()
            ok = actual is not None and abs(actual - value) <= 0.03
            logging.info('ACTION system.volume.set requested=%.3f actual=%s verified=%s', value, actual, ok)
            return ok, actual
        except Exception as exc:
            logging.exception('Volume set failed: %s', exc)
            return False, None

    def get_mute(self):
        if not self.available():
            return None
        try:
            return bool(self._endpoint.GetMute())
        except Exception:
            return None

    def set_mute(self, muted):
        if not self.available():
            return False
        try:
            self.previous_mute = self.get_mute()
            self._endpoint.SetMute(1 if muted else 0, None)
            actual = self.get_mute()
            ok = actual is not None and actual == bool(muted)
            logging.info('ACTION system.volume.mute requested=%s actual=%s verified=%s', muted, actual, ok)
            return ok
        except Exception as exc:
            logging.exception('Mute failed: %s', exc)
            return False

    def _percent_from_text(self, t):
        m = re.search(r'(?:на|до)\s*(\d{1,3})\s*%?', t)
        if m:
            return max(0, min(100, int(m.group(1))))
        m = re.search(r'громк(?:ость|ости)?\s*(\d{1,3})\s*%?', t)
        if m:
            return max(0, min(100, int(m.group(1))))
        if 'наполовину' in t or 'на половину' in t or 'половина' in t:
            return 50
        if 'на максимум' in t or 'максимум' in t or 'на всю' in t:
            return 100
        return None

    def execute(self, text):
        t = norm(text)
        mentions_audio = any(x in t for x in ('громк', 'звук', 'тише', 'громче', 'mute', 'мут'))
        if not mentions_audio:
            return False, None

        if not self.available():
            return True, 'Системное управление звуком пока недоступно: модуль Windows Audio не загрузился.'

        current = self.get_volume()
        if current is None:
            return True, 'Не смогла прочитать текущую громкость Windows.'

        if any(x in t for x in ('выключи звук', 'без звука', 'замуть', 'mute')):
            ok = self.set_mute(True)
            return True, 'Звук выключен.' if ok else 'Команду mute отправила, но состояние подтвердить не смогла.'

        if any(x in t for x in ('включи звук', 'размуть', 'unmute')):
            ok = self.set_mute(False)
            return True, 'Звук включен.' if ok else 'Команду unmute отправила, но состояние подтвердить не смогла.'

        if ('верни' in t or 'как было' in t) and self.previous_volume is not None:
            target = self.previous_volume
            ok, actual = self.set_volume(target)
            pct = round((actual if actual is not None else target) * 100)
            return True, f'Вернула громкость примерно на {pct}%.' if ok else 'Попыталась вернуть громкость, но проверка не прошла.'

        relative_phrase = ('тише' in t or 'громче' in t)
        pct = None if relative_phrase else self._percent_from_text(t)
        if pct is not None:
            ok, actual = self.set_volume(pct / 100.0)
            actual_pct = round((actual if actual is not None else pct / 100.0) * 100)
            return True, f'Громкость {actual_pct}%.' if ok else f'Поставила команду на {pct}%, но точное состояние подтвердить не смогла.'

        target = current
        if 'в два раза тише' in t or 'вдвое тише' in t or 'убавь вдвое' in t:
            target = current / 2.0
        elif re.search(r'на\s*(\d{1,2})\s*%?\s*тише', t):
            points = int(re.search(r'на\s*(\d{1,2})\s*%?\s*тише', t).group(1))
            target = current - points / 100.0
        elif re.search(r'на\s*(\d{1,2})\s*%?\s*громче', t):
            points = int(re.search(r'на\s*(\d{1,2})\s*%?\s*громче', t).group(1))
            target = current + points / 100.0
        elif 'чуть чуть тише' in t or 'чуть-чуть тише' in t:
            target = current - 0.05
        elif 'чуть чуть громче' in t or 'чуть-чуть громче' in t:
            target = current + 0.05
        elif 'тише' in t:
            target = current - 0.10
        elif 'громче' in t:
            target = current + 0.10
        elif 'сколько громкость' in t or 'какая громкость' in t:
            return True, f'Системная громкость примерно {round(current * 100)}%.'
        else:
            return False, None

        ok, actual = self.set_volume(target)
        pct = round((actual if actual is not None else target) * 100)
        return True, f'Громкость {pct}%.' if ok else 'Изменила громкость, но состояние подтвердить не смогла.'
