
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "bot.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(get_db()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                subject_code TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                exam_form TEXT,
                official_scoring_mode TEXT NOT NULL DEFAULT 'none',
                official_paes_score INTEGER,
                estimated_paes_score INTEGER,
                raw_correct_valid INTEGER NOT NULL DEFAULT 0,
                valid_questions_total INTEGER NOT NULL DEFAULT 0,
                answered_questions_total INTEGER NOT NULL DEFAULT 0,
                omitted_questions_total INTEGER NOT NULL DEFAULT 0,
                score_percent REAL NOT NULL DEFAULT 0,
                current_sequence INTEGER NOT NULL DEFAULT 1,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                notes TEXT,
                FOREIGN KEY(phone) REFERENCES users(phone)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS session_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                sequence INTEGER NOT NULL,
                question_id TEXT NOT NULL,
                question_number INTEGER,
                context_id TEXT,
                is_scored INTEGER NOT NULL DEFAULT 1,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                max_options INTEGER NOT NULL DEFAULT 4,
                response_option TEXT,
                is_correct INTEGER,
                answered_at TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                UNIQUE(session_id, sequence)
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_phone_status ON sessions(phone, status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_session_questions_session ON session_questions(session_id, sequence)"
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS menu_state (
                phone TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                subject_code TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(phone) REFERENCES users(phone)
            )
            """
        )
        conn.commit()


def upsert_user(phone: str, name: Optional[str]) -> None:
    now = utc_now_iso()
    with closing(get_db()) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT phone FROM users WHERE phone = ?", (phone,)).fetchone()
        if row:
            cur.execute(
                "UPDATE users SET name = COALESCE(?, name), last_seen_at = ? WHERE phone = ?",
                (name, now, phone),
            )
        else:
            cur.execute(
                "INSERT INTO users(phone, name, created_at, last_seen_at) VALUES (?, ?, ?, ?)",
                (phone, name, now, now),
            )
        conn.commit()



def set_menu_state(phone: str, state: str, subject_code: Optional[str] = None) -> None:
    now = utc_now_iso()
    with closing(get_db()) as conn:
        conn.execute(
            """
            INSERT INTO menu_state(phone, state, subject_code, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                state = excluded.state,
                subject_code = excluded.subject_code,
                updated_at = excluded.updated_at
            """,
            (phone, state, subject_code, now),
        )
        conn.commit()


def get_menu_state(phone: str):
    with closing(get_db()) as conn:
        return conn.execute(
            "SELECT phone, state, subject_code, updated_at FROM menu_state WHERE phone = ?",
            (phone,),
        ).fetchone()


def clear_menu_state(phone: str) -> None:
    with closing(get_db()) as conn:
        conn.execute("DELETE FROM menu_state WHERE phone = ?", (phone,))
        conn.commit()
