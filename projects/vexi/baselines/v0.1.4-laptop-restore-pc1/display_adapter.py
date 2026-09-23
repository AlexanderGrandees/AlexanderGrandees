import ctypes
import logging
import os
import re
import subprocess
from pathlib import Path


SPI_SETDESKWALLPAPER = 0x0014
SPI_GETDESKWALLPAPER = 0x0073
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02


class DisplayAdapter:
    """Windows display/personalization controls with explicit verification where practical."""

    def __init__(self):
        self.previous_brightness = None
        self.previous_wallpaper = None

    @staticmethod
    def _powershell(command, timeout=8):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=creationflags,
                encoding="utf-8",
                errors="replace",
            )
            return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()
        except Exception as exc:
            logging.debug("PowerShell display command failed: %s", exc)
            return 1, "", str(exc)

    def get_brightness(self):
        code, out, _ = self._powershell(
            "Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue | "
            "Where-Object {$_.Active -eq $true} | Select-Object -First 1 -ExpandProperty CurrentBrightness"
        )
        if code != 0 or not out:
            return None
        m = re.search(r"\d{1,3}", out)
        if not m:
            return None
        return max(0, min(100, int(m.group(0))))

    def set_brightness(self, percent, remember=True):
        percent = max(0, min(100, int(round(float(percent)))))
        current = self.get_brightness()
        if remember and current is not None:
            self.previous_brightness = current
        cmd = (
            "$m=Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue | "
            "Where-Object {$_.Active -eq $true} | Select-Object -First 1; "
            f"if($null -eq $m){{exit 3}}; Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness "
            f"-Arguments @{{Timeout=1;Brightness=[byte]{percent}}} | Out-Null"
        )
        code, _, err = self._powershell(cmd)
        if code != 0:
            logging.warning("Brightness set unavailable: %s", err)
            return "UNSUPPORTED", self.get_brightness()
        actual = self.get_brightness()
        ok = actual is not None and abs(actual - percent) <= 3
        logging.info("ACTION display.brightness.set requested=%s actual=%s verified=%s", percent, actual, ok)
        return ("CONFIRMED_SUCCESS" if ok else "SENT_NOT_CONFIRMED"), actual

    def restore_brightness(self):
        if self.previous_brightness is None:
            return "NOT_FOUND", self.get_brightness()
        return self.set_brightness(self.previous_brightness, remember=False)

    def get_wallpaper(self):
        try:
            buf = ctypes.create_unicode_buffer(32768)
            ok = ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, len(buf), buf, 0)
            if ok:
                return buf.value or None
        except Exception:
            pass
        return None

    def set_wallpaper(self, path):
        p = Path(path).expanduser()
        if not p.exists() or not p.is_file():
            return "NOT_FOUND", None
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            return "BLOCKED", None
        before = self.get_wallpaper()
        if before:
            self.previous_wallpaper = before
        try:
            ok = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, str(p.resolve()), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            after = self.get_wallpaper()
            verified = bool(ok and after and Path(after).resolve() == p.resolve())
            logging.info("ACTION display.wallpaper.set path=%s actual=%s verified=%s", p, after, verified)
            return ("CONFIRMED_SUCCESS" if verified else "SENT_NOT_CONFIRMED"), after
        except Exception as exc:
            logging.exception("set_wallpaper failed: %s", exc)
            return "FAILED", self.get_wallpaper()

    def restore_wallpaper(self):
        if not self.previous_wallpaper:
            return "NOT_FOUND", self.get_wallpaper()
        return self.set_wallpaper(self.previous_wallpaper)

    def toggle_hdr(self):
        """Use Microsoft's documented Win+Alt+B HDR toggle.

        Generic v0.1.1 does not yet have a verified HDR state reader, therefore
        this returns SENT_NOT_CONFIRMED and is intentionally exposed only as a
        toggle operation.  Explicit ON/OFF requests should not guess current state.
        """
        try:
            user32 = ctypes.windll.user32
            KEYUP = 0x0002
            keys = [0x5B, 0x12, 0x42]  # WIN, ALT, B
            for code in keys:
                user32.keybd_event(code, 0, 0, 0)
            for code in reversed(keys):
                user32.keybd_event(code, 0, KEYUP, 0)
            logging.info("ACTION display.hdr.toggle status=SENT_NOT_CONFIRMED")
            return "SENT_NOT_CONFIRMED"
        except Exception as exc:
            logging.exception("HDR toggle failed: %s", exc)
            return "FAILED"

    def open_display_settings(self):
        try:
            os.startfile("ms-settings:display")
            return "SENT_NOT_CONFIRMED"
        except Exception:
            return "FAILED"
