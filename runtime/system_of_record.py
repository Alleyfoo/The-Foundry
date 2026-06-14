"""
The system of record — a local SQLite stand-in for SAP.

Holds the current, mutable state of every object plus an append-only event log of
every transition. Seeded from data/objects.json on first use; state then persists
between runs (so an approval or a commit sticks).

Local-first, standard library only. The DB lives under artifacts/ (gitignored).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class SystemOfRecord:
    """SQLite-backed store: the current truth of the object set + its history."""

    def __init__(self, db_path: str = "artifacts/foundry.db"):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False so a single connection can be reused across
        # Streamlit reruns (access is serialised; fine for this demo).
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS objects (
                object_id TEXT PRIMARY KEY,
                data      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         TEXT NOT NULL,
                object_id  TEXT NOT NULL,
                action     TEXT NOT NULL,
                from_state TEXT,
                to_state   TEXT,
                actor_role TEXT,
                note       TEXT
            );
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    def is_empty(self) -> bool:
        cur = self._conn.execute("SELECT COUNT(*) AS n FROM objects")
        return cur.fetchone()["n"] == 0

    def seed_if_empty(self, objects: list[dict[str, Any]]) -> bool:
        """Load the seed objects the first time only. Returns True if it seeded."""
        if not self.is_empty():
            return False
        self.reset(objects)
        return True

    def reset(self, objects: list[dict[str, Any]]) -> None:
        """Wipe and reseed from the given objects. Clears history too."""
        self._conn.execute("DELETE FROM objects")
        self._conn.execute("DELETE FROM events")
        for obj in objects:
            self.upsert(obj, commit=False)
        self._conn.commit()
        self.add_event("__seed__", "seed", None, None, "system", f"seeded {len(objects)} objects")

    # ------------------------------------------------------------------
    def all_objects(self) -> list[dict[str, Any]]:
        cur = self._conn.execute("SELECT data FROM objects ORDER BY object_id")
        return [json.loads(r["data"]) for r in cur.fetchall()]

    def get(self, object_id: str) -> dict[str, Any] | None:
        cur = self._conn.execute("SELECT data FROM objects WHERE object_id = ?", (object_id,))
        row = cur.fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, obj: dict[str, Any], commit: bool = True) -> None:
        self._conn.execute(
            "INSERT INTO objects (object_id, data) VALUES (?, ?) "
            "ON CONFLICT(object_id) DO UPDATE SET data = excluded.data",
            (obj["object_id"], json.dumps(obj)),
        )
        if commit:
            self._conn.commit()

    # ------------------------------------------------------------------
    def add_event(self, object_id: str, action: str, from_state: str | None,
                  to_state: str | None, actor_role: str | None, note: str = "") -> None:
        self._conn.execute(
            "INSERT INTO events (ts, object_id, action, from_state, to_state, actor_role, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), object_id, action, from_state, to_state, actor_role, note),
        )
        self._conn.commit()

    def events(self, limit: int = 200) -> list[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in cur.fetchall()]

    def next_object_id(self, prefix: str = "OBJ-IN") -> str:
        """Generate the next intake object id, e.g. OBJ-IN1, OBJ-IN2 ..."""
        cur = self._conn.execute(
            "SELECT object_id FROM objects WHERE object_id LIKE ?", (prefix + "%",)
        )
        nums = []
        for r in cur.fetchall():
            tail = r["object_id"][len(prefix):]
            if tail.isdigit():
                nums.append(int(tail))
        return f"{prefix}{(max(nums) + 1) if nums else 1}"

    def close(self) -> None:
        self._conn.close()
