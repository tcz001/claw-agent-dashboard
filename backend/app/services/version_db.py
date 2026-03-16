"""Version database — SQLite connection management and CRUD operations."""
import asyncio
import hashlib
from pathlib import Path

import aiosqlite

from ..config import DATA_DIR

DB_PATH = Path(DATA_DIR) / "versions.db"

_db: aiosqlite.Connection | None = None
_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        async with _lock:
            if _db is None:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                _db = await aiosqlite.connect(str(DB_PATH))
                _db.row_factory = aiosqlite.Row
                await _db.execute("PRAGMA journal_mode=WAL")
                await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS agents (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_name  TEXT NOT NULL UNIQUE,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS file_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id        INTEGER NOT NULL REFERENCES agents(id),
            file_path       TEXT NOT NULL,
            version_num     INTEGER NOT NULL,
            content         TEXT NOT NULL,
            content_hash    TEXT NOT NULL,
            source          TEXT NOT NULL,
            likely_openclaw BOOLEAN DEFAULT FALSE,
            commit_msg      TEXT,
            ai_summary      TEXT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_id, file_path, version_num)
        );

        CREATE INDEX IF NOT EXISTS idx_versions_file
            ON file_versions(agent_id, file_path, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_versions_hash
            ON file_versions(agent_id, file_path, content_hash);

        CREATE TABLE IF NOT EXISTS tracked_files (
            agent_id      INTEGER NOT NULL REFERENCES agents(id),
            file_path     TEXT NOT NULL,
            current_hash  TEXT NOT NULL,
            last_scanned  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(agent_id, file_path)
        );
    """)
    await db.commit()


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def get_or_create_agent(workspace_name: str) -> int:
    db = await get_db()
    cursor = await db.execute(
        "SELECT id FROM agents WHERE workspace_name = ?", (workspace_name,)
    )
    row = await cursor.fetchone()
    if row:
        return row["id"]
    cursor = await db.execute(
        "INSERT INTO agents (workspace_name) VALUES (?)", (workspace_name,)
    )
    await db.commit()
    return cursor.lastrowid


async def get_next_version_num(agent_id: int, file_path: str) -> int:
    db = await get_db()
    cursor = await db.execute(
        "SELECT MAX(version_num) as max_ver FROM file_versions WHERE agent_id = ? AND file_path = ?",
        (agent_id, file_path),
    )
    row = await cursor.fetchone()
    current = row["max_ver"] if row and row["max_ver"] is not None else 0
    return current + 1


async def create_version(
    agent_id: int,
    file_path: str,
    content: str,
    content_hash: str,
    source: str,
    likely_openclaw: bool = False,
    commit_msg: str | None = None,
) -> dict:
    db = await get_db()
    version_num = await get_next_version_num(agent_id, file_path)
    cursor = await db.execute(
        """INSERT INTO file_versions
           (agent_id, file_path, version_num, content, content_hash, source, likely_openclaw, commit_msg)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (agent_id, file_path, version_num, content, content_hash, source, likely_openclaw, commit_msg),
    )
    await db.commit()
    return {
        "id": cursor.lastrowid,
        "agent_id": agent_id,
        "file_path": file_path,
        "version_num": version_num,
        "content_hash": content_hash,
        "source": source,
        "likely_openclaw": likely_openclaw,
        "commit_msg": commit_msg,
        "ai_summary": None,
    }


async def get_versions(agent_id: int, file_path: str, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM file_versions WHERE agent_id = ? AND file_path = ?",
        (agent_id, file_path),
    )
    row = await cursor.fetchone()
    total = row["cnt"]

    cursor = await db.execute(
        """SELECT id, version_num, source, likely_openclaw, commit_msg, ai_summary, created_at
           FROM file_versions
           WHERE agent_id = ? AND file_path = ?
           ORDER BY version_num DESC
           LIMIT ? OFFSET ?""",
        (agent_id, file_path, limit, offset),
    )
    rows = await cursor.fetchall()
    versions = [dict(r) for r in rows]
    return versions, total


async def get_version(version_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, agent_id, file_path, version_num, content, content_hash,
                  source, likely_openclaw, commit_msg, ai_summary, created_at
           FROM file_versions WHERE id = ?""",
        (version_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_previous_version(agent_id: int, file_path: str, version_num: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        """SELECT id, agent_id, file_path, version_num, content, content_hash,
                  source, likely_openclaw, commit_msg, ai_summary, created_at
           FROM file_versions
           WHERE agent_id = ? AND file_path = ? AND version_num < ?
           ORDER BY version_num DESC LIMIT 1""",
        (agent_id, file_path, version_num),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_summary(version_id: int, summary: str):
    db = await get_db()
    await db.execute(
        "UPDATE file_versions SET ai_summary = ? WHERE id = ?",
        (summary, version_id),
    )
    await db.commit()


async def get_tracked_file(agent_id: int, file_path: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT agent_id, file_path, current_hash, last_scanned FROM tracked_files WHERE agent_id = ? AND file_path = ?",
        (agent_id, file_path),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def upsert_tracked_file(agent_id: int, file_path: str, current_hash: str):
    db = await get_db()
    await db.execute(
        """INSERT INTO tracked_files (agent_id, file_path, current_hash, last_scanned)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(agent_id, file_path)
           DO UPDATE SET current_hash = excluded.current_hash, last_scanned = CURRENT_TIMESTAMP""",
        (agent_id, file_path, current_hash),
    )
    await db.commit()


async def get_all_tracked_files(agent_id: int) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT agent_id, file_path, current_hash, last_scanned FROM tracked_files WHERE agent_id = ?",
        (agent_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
