import json
import sqlite3
import time
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                key TEXT NOT NULL,
                value_json TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                sensitivity TEXT DEFAULT 'normal',
                user_confirmed INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                last_used_at REAL,
                expires_at REAL,
                active INTEGER DEFAULT 1,
                provenance TEXT,
                UNIQUE(kind, key)
            )
        """)
        self.db.commit()

    def set(self, kind, key, value, source="user_explicit", confidence=1.0, sensitivity="normal", user_confirmed=True, provenance=""):
        now = time.time()
        payload = json.dumps(value, ensure_ascii=False)
        self.db.execute("""
            INSERT INTO memory(kind,key,value_json,source,confidence,sensitivity,user_confirmed,created_at,updated_at,last_used_at,active,provenance)
            VALUES(?,?,?,?,?,?,?,?,?,?,1,?)
            ON CONFLICT(kind,key) DO UPDATE SET
              value_json=excluded.value_json,
              source=excluded.source,
              confidence=excluded.confidence,
              sensitivity=excluded.sensitivity,
              user_confirmed=excluded.user_confirmed,
              updated_at=excluded.updated_at,
              active=1,
              provenance=excluded.provenance
        """, (kind, key, payload, source, confidence, sensitivity, int(user_confirmed), now, now, now, provenance))
        self.db.commit()

    def get(self, kind, key, default=None):
        row = self.db.execute("SELECT value_json FROM memory WHERE kind=? AND key=? AND active=1", (kind, key)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row[0])
        except Exception:
            return default

    def delete(self, kind, key):
        self.db.execute("UPDATE memory SET active=0, updated_at=? WHERE kind=? AND key=?", (time.time(), kind, key))
        self.db.commit()

    def all_active(self, limit=100):
        rows = self.db.execute("SELECT kind,key,value_json,source,user_confirmed,updated_at FROM memory WHERE active=1 ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for kind, key, payload, source, confirmed, updated in rows:
            try:
                value = json.loads(payload)
            except Exception:
                value = payload
            out.append({"kind": kind, "key": key, "value": value, "source": source, "user_confirmed": bool(confirmed), "updated_at": updated})
        return out
