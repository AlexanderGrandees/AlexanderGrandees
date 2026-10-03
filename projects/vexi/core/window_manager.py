import ctypes
import logging
import time

import psutil

user32 = ctypes.windll.user32

SW_RESTORE = 9
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
WM_CLOSE = 0x0010


def matching_processes(names):
    wanted = {str(x).lower() for x in names if x}
    out = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if (proc.info.get("name") or "").lower() in wanted:
                out.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return out


def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    try:
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


def window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def enum_windows(pids=None):
    wanted = None if pids is None else {int(x) for x in pids}
    results = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if wanted is not None and pid.value not in wanted:
            return True
        title = window_title(hwnd)
        if not title:
            return True
        results.append({
            "hwnd": int(hwnd),
            "pid": int(pid.value),
            "title": title,
            "class_name": window_class(hwnd),
            "minimized": bool(user32.IsIconic(hwnd)),
            "maximized": bool(user32.IsZoomed(hwnd)),
        })
        return True

    user32.EnumWindows(callback, 0)
    return results


def active_window():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    proc_name = ""
    try:
        proc_name = psutil.Process(pid.value).name()
    except Exception:
        pass
    return {
        "hwnd": int(hwnd),
        "pid": int(pid.value),
        "process": proc_name,
        "title": window_title(hwnd),
        "class_name": window_class(hwnd),
        "minimized": bool(user32.IsIconic(hwnd)),
        "maximized": bool(user32.IsZoomed(hwnd)),
    }


def focus_hwnd(hwnd, restore_if_minimized=True, retries=6):
    try:
        if restore_if_minimized and user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.12)
        # IMPORTANT: no SW_RESTORE for normal/maximized/fullscreen windows.
        user32.BringWindowToTop(hwnd)
        for _ in range(retries):
            user32.SetForegroundWindow(hwnd)
            if user32.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.10)
        return user32.GetForegroundWindow() == hwnd
    except Exception as exc:
        logging.debug("focus_hwnd failed: %s", exc)
        return False


def focus_processes(processes):
    if not processes:
        return False
    windows = enum_windows([p.pid for p in processes])
    if not windows:
        return False
    # Prefer the last/foreground-looking window; EnumWindows is z-order based.
    for w in windows:
        if focus_hwnd(w["hwnd"], restore_if_minimized=True):
            return True
    return False



def explorer_windows():
    """Return real File Explorer windows, excluding the desktop shell."""
    return [w for w in enum_windows(None) if w.get("class_name") in {"CabinetWClass", "ExploreWClass"}]


def focus_explorer_window():
    wins = explorer_windows()
    for w in wins:
        if focus_hwnd(w["hwnd"], restore_if_minimized=True):
            return True
    return False

def minimize_processes(processes):
    windows = enum_windows([p.pid for p in processes])
    if not windows:
        return False
    for w in windows:
        user32.ShowWindow(w["hwnd"], SW_MINIMIZE)
    time.sleep(0.15)
    return all(bool(user32.IsIconic(w["hwnd"])) for w in windows)


def maximize_processes(processes):
    windows = enum_windows([p.pid for p in processes])
    if not windows:
        return False
    for w in windows:
        user32.ShowWindow(w["hwnd"], SW_MAXIMIZE)
    time.sleep(0.12)
    return all(bool(user32.IsZoomed(w["hwnd"])) for w in windows)


def close_process_windows(processes):
    windows = enum_windows([p.pid for p in processes])
    if not windows:
        return False
    for w in windows:
        user32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
    return True


def send_hotkey(*keys):
    KEYEVENTF_KEYUP = 0x0002
    vk = {
        "CTRL": 0x11, "ALT": 0x12, "SHIFT": 0x10,
        "T": 0x54, "W": 0x57, "R": 0x52, "L": 0x4C, "J": 0x4A, "H": 0x48, "TAB": 0x09,
        "LEFT": 0x25, "RIGHT": 0x27, "UP": 0x26, "DOWN": 0x28, "F11": 0x7A,
        "PLUS": 0xBB, "MINUS": 0xBD, "0": 0x30,
        "F": 0x46, "K": 0x4B, "M": 0x4D, "C": 0x43, "N": 0x4E, "P": 0x50, "I": 0x49,
        "PERIOD": 0xBE, "COMMA": 0xBC, "SPACE": 0x20,
        "MEDIA_PLAY_PAUSE": 0xB3, "MEDIA_NEXT": 0xB0, "MEDIA_PREV": 0xB1,
    }
    codes = [vk[k] for k in keys]
    for code in codes:
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)
    return True


def list_visible_windows(limit=20):
    result = []
    for w in enum_windows(None)[:limit]:
        try:
            proc = psutil.Process(w["pid"]).name()
        except Exception:
            proc = ""
        result.append({**w, "process": proc})
    return result
