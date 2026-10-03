import ctypes
import os
from ctypes import wintypes

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR), ("LastWritten", FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)), ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


class CredentialStore:
    """Windows Credential Manager wrapper. Secrets are never logged or put in config."""
    def __init__(self, prefix="Vexi"):
        self.prefix = prefix
        self.available = os.name == "nt"
        if self.available:
            self.advapi = ctypes.WinDLL("Advapi32.dll")
            self.advapi.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
            self.advapi.CredWriteW.restype = wintypes.BOOL
            self.advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
            self.advapi.CredReadW.restype = wintypes.BOOL
            self.advapi.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
            self.advapi.CredDeleteW.restype = wintypes.BOOL
            self.advapi.CredFree.argtypes = [ctypes.c_void_p]

    def target(self, name):
        return f"{self.prefix}/{name}" if not str(name).startswith(self.prefix + "/") else str(name)

    def write(self, name, secret, username="Vexi"):
        if not self.available:
            raise RuntimeError("Windows Credential Manager is unavailable")
        target = self.target(name)
        raw = str(secret).encode("utf-16-le")
        blob = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        cred = CREDENTIALW()
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.CredentialBlobSize = len(raw)
        cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = username
        if not self.advapi.CredWriteW(ctypes.byref(cred), 0):
            raise ctypes.WinError()
        return True

    def read(self, name):
        if not self.available:
            return None
        target = self.target(name)
        pcred = ctypes.POINTER(CREDENTIALW)()
        if not self.advapi.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
            return None
        try:
            c = pcred.contents
            if not c.CredentialBlob or not c.CredentialBlobSize:
                return ""
            raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
            return raw.decode("utf-16-le")
        finally:
            self.advapi.CredFree(pcred)

    def has(self, name):
        return self.read(name) is not None

    def delete(self, name):
        if not self.available:
            return False
        target = self.target(name)
        ok = self.advapi.CredDeleteW(target, CRED_TYPE_GENERIC, 0)
        return bool(ok)
