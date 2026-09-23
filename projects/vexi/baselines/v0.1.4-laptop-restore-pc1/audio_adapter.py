import logging


class AudioAdapter:
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
            logging.warning("System audio unavailable: %s", exc)

    def available(self):
        return self._endpoint is not None

    def get_volume(self):
        if not self.available():
            return None
        try:
            return max(0.0, min(1.0, float(self._endpoint.GetMasterVolumeLevelScalar())))
        except Exception:
            return None

    def get_mute(self):
        if not self.available():
            return None
        try:
            return bool(self._endpoint.GetMute())
        except Exception:
            return None

    def set_volume(self, value, remember=True):
        if not self.available():
            return "UNSUPPORTED", None
        value = max(0.0, min(1.0, float(value)))
        current = self.get_volume()
        if remember and current is not None:
            self.previous_volume = current
        try:
            self._endpoint.SetMasterVolumeLevelScalar(value, None)
            actual = self.get_volume()
            ok = actual is not None and abs(actual - value) <= 0.03
            logging.info("ACTION system.volume.set requested=%.3f actual=%s verified=%s", value, actual, ok)
            return ("CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED"), actual
        except Exception as exc:
            logging.exception("set_volume failed: %s", exc)
            return "FAILED", self.get_volume()

    def set_mute(self, muted):
        if not self.available():
            return "UNSUPPORTED", None
        current = self.get_mute()
        if current is not None:
            self.previous_mute = current
        try:
            self._endpoint.SetMute(bool(muted), None)
            actual = self.get_mute()
            ok = actual == bool(muted)
            return ("CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED"), actual
        except Exception as exc:
            logging.exception("set_mute failed: %s", exc)
            return "FAILED", self.get_mute()

    def restore_volume(self):
        if self.previous_volume is None:
            return "NOT_FOUND", self.get_volume()
        target = self.previous_volume
        # avoid toggling previous_volume back to current when restoring
        return self.set_volume(target, remember=False)
