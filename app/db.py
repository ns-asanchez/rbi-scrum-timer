"""Database layer — SQLite schema management and CRUD operations for participants, config, sessions."""

import random
import sqlite3
import sys
from pathlib import Path

from app.models import FOOD_ICONS, MeetingConfig, Participant, SessionRecord

def _get_db_path() -> Path:
    """Return DB path — ~/Library/Application Support when running as .app, else data/ locally."""
    if getattr(sys, "frozen", False):
        # Running as py2app bundle
        app_support = Path.home() / "Library" / "Application Support" / "RBI Scrum Timer"
    else:
        # Running from source
        app_support = Path(__file__).parent.parent / "data"
    app_support.mkdir(parents=True, exist_ok=True)
    return app_support / "scrum.db"


DB_PATH = _get_db_path()


def _connect() -> sqlite3.Connection:
    """Open and return a database connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:  # noqa: C901
    """Create all tables and run migrations (food_icon, bell settings, Jira IDs, etc.)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        # participants table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT    NOT NULL UNIQUE,
                is_jefote INTEGER NOT NULL DEFAULT 0,
                food_icon TEXT    NOT NULL DEFAULT ''
            )
        """)
        # Migrate participants: food_icon column
        cols = [
            r[1] for r in conn.execute("PRAGMA table_info(participants)").fetchall()
        ]
        if "food_icon" not in cols:
            conn.execute(
                "ALTER TABLE participants ADD COLUMN food_icon TEXT NOT NULL DEFAULT ''"
            )
            rows = conn.execute("SELECT id FROM participants").fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE participants SET food_icon = ? WHERE id = ?",
                    (random.choice(FOOD_ICONS), row[0]),
                )

        # meeting_config table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meeting_config (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                duration_minutes INTEGER NOT NULL DEFAULT 15
            )
        """)
        # Migrate meeting_config: meeting_name, bell_enabled, bell_volume columns
        cfg_cols = [
            r[1] for r in conn.execute("PRAGMA table_info(meeting_config)").fetchall()
        ]
        if "meeting_name" not in cfg_cols:
            conn.execute(
                "ALTER TABLE meeting_config ADD COLUMN meeting_name TEXT NOT NULL DEFAULT 'Polaris Rising [Ab+B]'"
            )
        if "bell_enabled" not in cfg_cols:
            conn.execute(
                "ALTER TABLE meeting_config ADD COLUMN bell_enabled INTEGER NOT NULL DEFAULT 1"
            )
        if "bell_volume" not in cfg_cols:
            conn.execute(
                "ALTER TABLE meeting_config ADD COLUMN bell_volume INTEGER NOT NULL DEFAULT 70"
            )
        # Seed default row
        conn.execute(
            "INSERT OR IGNORE INTO meeting_config (id, duration_minutes) VALUES (1, 15)"
        )
        # tokens table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # app_settings table (generic key-value)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Migrate participants: jira_account_id + avatar_path
        pcols = [
            r[1] for r in conn.execute("PRAGMA table_info(participants)").fetchall()
        ]
        if "jira_account_id" not in pcols:
            conn.execute(
                "ALTER TABLE participants ADD COLUMN jira_account_id TEXT NOT NULL DEFAULT ''"
            )
        if "avatar_path" not in pcols:
            conn.execute(
                "ALTER TABLE participants ADD COLUMN avatar_path TEXT NOT NULL DEFAULT ''"
            )

        conn.executescript("""

            CREATE TABLE IF NOT EXISTS meeting_sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                date             TEXT    NOT NULL,
                planned_duration INTEGER NOT NULL,
                actual_duration  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS participant_times (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       INTEGER NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
                participant_name TEXT    NOT NULL,
                is_jefote        INTEGER NOT NULL DEFAULT 0,
                allocated_time   INTEGER NOT NULL,
                actual_time      INTEGER NOT NULL
            );
        """)


# ── App Settings ─────────────────────────────────────────────────────────────


def get_setting(key: str, default: str = "") -> str:
    """Get an app setting by key, or return default if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Insert or replace an app setting."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value),
        )


# ── Tokens ───────────────────────────────────────────────────────────────────


def get_all_tokens() -> dict[str, str]:
    """Fetch all stored tokens as a dict."""
    with _connect() as conn:
        rows = conn.execute("SELECT key, value FROM tokens").fetchall()
    return {r["key"]: r["value"] for r in rows}


def set_token(key: str, value: str) -> None:
    """Insert or replace a token."""
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tokens (key, value) VALUES (?, ?)", (key, value)
        )


def delete_token(key: str) -> None:
    """Delete a token by key."""
    with _connect() as conn:
        conn.execute("DELETE FROM tokens WHERE key = ?", (key,))


# ── Participants ──────────────────────────────────────────────────────────────


def get_all_participants() -> list[Participant]:
    """Fetch all participants sorted by name."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, is_jefote, food_icon, jira_account_id, avatar_path FROM participants ORDER BY name"
        ).fetchall()
    return [
        Participant(
            r["id"],
            r["name"],
            bool(r["is_jefote"]),
            r["food_icon"],
            r["jira_account_id"] or "",
            r["avatar_path"] or "",
        )
        for r in rows
    ]


def add_participant(
    name: str, is_jefote: bool, jira_account_id: str = "", avatar_path: str = ""
) -> Participant:
    """Create a new participant with a random food icon."""
    icon = random.choice(FOOD_ICONS)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO participants (name, is_jefote, food_icon, jira_account_id, avatar_path) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), int(is_jefote), icon, jira_account_id, avatar_path),
        )
        return Participant(
            cur.lastrowid, name.strip(), is_jefote, icon, jira_account_id, avatar_path
        )


def update_participant(
    pid: int,
    name: str,
    is_jefote: bool,
    jira_account_id: str = "",
    avatar_path: str = "",
) -> None:
    """Update a participant's fields."""
    with _connect() as conn:
        conn.execute(
            "UPDATE participants SET name = ?, is_jefote = ?, jira_account_id = ?, avatar_path = ? WHERE id = ?",
            (name.strip(), int(is_jefote), jira_account_id, avatar_path, pid),
        )


def delete_participant(pid: int) -> None:
    """Delete a participant by ID."""
    with _connect() as conn:
        conn.execute("DELETE FROM participants WHERE id = ?", (pid,))


# ── Config ────────────────────────────────────────────────────────────────────


def get_config() -> MeetingConfig:
    """Fetch the current meeting configuration."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT duration_minutes, meeting_name, bell_enabled, bell_volume FROM meeting_config WHERE id = 1"
        ).fetchone()
    return MeetingConfig(
        duration_minutes=row["duration_minutes"],
        meeting_name=row["meeting_name"],
        bell_enabled=bool(row["bell_enabled"]),
        bell_volume=int(row["bell_volume"]),
    )


def set_config(
    duration_minutes: int,
    meeting_name: str,
    bell_enabled: bool = True,
    bell_volume: int = 70,
) -> None:
    """Update the meeting configuration (duration, name, bell settings)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE meeting_config SET duration_minutes = ?, meeting_name = ?, bell_enabled = ?, bell_volume = ? WHERE id = 1",
            (
                duration_minutes,
                meeting_name.strip(),
                int(bell_enabled),
                int(bell_volume),
            ),
        )


# ── Sessions ──────────────────────────────────────────────────────────────────


def save_session(
    date: str,  # ISO datetime string: "YYYY-MM-DD HH:MM"
    planned_duration: int,
    actual_duration: int,
    participant_times: list[dict],
) -> int:
    """Save a completed meeting session and return the new session ID."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO meeting_sessions (date, planned_duration, actual_duration) VALUES (?, ?, ?)",
            (date, planned_duration, actual_duration),
        )
        session_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO participant_times (session_id, participant_name, is_jefote, allocated_time, actual_time) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    session_id,
                    p["name"],
                    int(p["is_jefote"]),
                    p["allocated_time"],
                    p["actual_time"],
                )
                for p in participant_times
            ],
        )
    return session_id


def delete_session(session_id: int) -> None:
    """Delete a session and cascade-delete its participant times."""
    with _connect() as conn:
        conn.execute("DELETE FROM meeting_sessions WHERE id = ?", (session_id,))


def get_participant_time_ranking() -> list[tuple[str, int]]:
    """Return all participants sorted by cumulative speaking time descending."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT participant_name, SUM(actual_time) AS total
            FROM participant_times
            WHERE is_jefote = 0
            GROUP BY participant_name
            ORDER BY total DESC
            """
        ).fetchall()
    return [(r["participant_name"], r["total"]) for r in rows]


def get_sessions() -> list[SessionRecord]:
    """Fetch all sessions with their participant times, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, date, planned_duration, actual_duration FROM meeting_sessions ORDER BY date DESC"
        ).fetchall()
        sessions = []
        for r in rows:
            times = conn.execute(
                "SELECT participant_name, is_jefote, allocated_time, actual_time FROM participant_times WHERE session_id = ?",
                (r["id"],),
            ).fetchall()
            sessions.append(
                SessionRecord(
                    id=r["id"],
                    date=r["date"],
                    planned_duration=r["planned_duration"],
                    actual_duration=r["actual_duration"],
                    participants=[dict(t) for t in times],
                )
            )
    return sessions
