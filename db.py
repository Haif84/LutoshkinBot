import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "lutoshkin.db")


def _get_connection() -> sqlite3.Connection:
    """
    Create a new SQLite connection.
    check_same_thread=False to allow usage from different threads
    (python-telegram-bot may run handlers in thread pool).
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables() -> None:
    """Create required tables if they do not exist."""
    try:
        conn = _get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                username TEXT,
                is_super BOOLEAN DEFAULT 0
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                description TEXT,
                created_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY,
                test_code TEXT,
                user_id INTEGER,
                last_name TEXT,
                answers TEXT,
                is_completed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP
            )
            """
        )

        # Basic migration for older DBs: add missing columns if they don't exist
        try:
            cur.execute("ALTER TABLE results ADD COLUMN user_id INTEGER")
        except sqlite3.OperationalError:
            # Column already exists or other non-fatal issue
            pass

        try:
            cur.execute(
                "ALTER TABLE results ADD COLUMN is_completed BOOLEAN DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute(
                "ALTER TABLE admins ADD COLUMN is_super BOOLEAN DEFAULT 0"
            )
        except sqlite3.OperationalError:
            # Column already exists or other non-fatal issue
            pass

        try:
            cur.execute(
                "ALTER TABLE tests ADD COLUMN owner_user_id INTEGER"
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()
        logger.info("Database tables created or already exist.")
    except Exception:
        logger.exception("Failed to create database tables.")
        raise


def add_admin(user_id: int, username: Optional[str]) -> None:
    """
    Add administrator to admins table.
    Intended to be used manually / from separate script.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Error while adding admin with user_id=%s", user_id)
        raise


def add_admin_by_username(username: str) -> None:
    """
    Add administrator record with only username.
    user_id will be filled automatically when this user first
    заходит к боту и выбирает роль администратора.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (None, username),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Error while adding admin with username=%s", username)
        raise


def has_any_admin() -> bool:
    """Return True if there is at least one admin in the table."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins LIMIT 1")
        row = cur.fetchone()
        conn.close()
        return row is not None
    except Exception:
        logger.exception("Error while checking if any admins exist.")
        return False


def get_admin(user_id: int) -> Optional[Dict[str, Any]]:
    """Get full admin record by user_id."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception("Error while getting admin with user_id=%s", user_id)
        return None


def get_admin_by_id(admin_id: int) -> Optional[Dict[str, Any]]:
    """Get full admin record by table primary key id."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE id = ?", (admin_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception("Error while getting admin by id=%s", admin_id)
        return None


def get_active_tests_count(owner_user_id: Optional[int]) -> int:
    """Return count of active tests created by the given owner (admin user_id)."""
    if owner_user_id is None:
        return 0
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM tests WHERE is_active = 1 AND owner_user_id = ?",
            (owner_user_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else 0
    except Exception:
        logger.exception(
            "Error while getting test count for owner_user_id=%s", owner_user_id
        )
        return 0


def get_all_admins() -> List[Dict[str, Any]]:
    """Return all admins."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM admins ORDER BY username IS NULL, username"
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        logger.exception("Error while getting all admins.")
        return []


def set_admin_super(admin_id: int, is_super: bool) -> bool:
    """Update is_super flag for given admin row id."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE admins SET is_super = ? WHERE id = ?",
            (int(is_super), admin_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        logger.exception(
            "Error while updating is_super for admin_id=%s", admin_id
        )
        return False


def check_admin(user_id: int, username: Optional[str] = None) -> bool:
    """
    Return True if user is in admins table.

    First tries to match by user_id. If нет, и передан username,
    пытается найти запись по username и привязывает к ней user_id.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        # 1. По user_id
        cur.execute("SELECT id FROM admins WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            conn.close()
            return True

        # 2. При необходимости – по username
        if username:
            cur.execute(
                "SELECT id FROM admins WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE admins SET user_id = ? WHERE id = ?",
                    (user_id, row["id"]),
                )
                conn.commit()
                conn.close()
                return True

        conn.close()
        return False
    except Exception:
        logger.exception(
            "Error while checking admin with user_id=%s, username=%s",
            user_id,
            username,
        )
        return False


def _generate_random_code(length: int = 6) -> str:
    """Generate random numeric code (only digits)."""
    import random
    import string

    digits = string.digits
    return "".join(random.choice(digits) for _ in range(length))


def get_test_by_code(code: str) -> Optional[Dict[str, Any]]:
    """Get test by its unique code."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM tests WHERE code = ?", (code,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception("Error while getting test by code=%s", code)
        return None


def create_test(description: str, owner_user_id: Optional[int] = None) -> Optional[str]:
    """
    Create new test with unique 6-character code.
    owner_user_id: Telegram user_id of the admin who created the test.
    Returns generated code or None on failure.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()

        # Try several times to generate a unique code
        code: Optional[str] = None
        for _ in range(20):
            generated = _generate_random_code(6)
            if get_test_by_code(generated) is None:
                code = generated
                break

        if code is None:
            logger.error("Failed to generate unique test code after many attempts.")
            return None

        cur.execute(
            """
            INSERT INTO tests (code, description, created_at, is_active, owner_user_id)
            VALUES (?, ?, ?, 1, ?)
            """,
            (code, description, datetime.utcnow().isoformat(), owner_user_id),
        )
        conn.commit()
        conn.close()
        logger.info("Created new test with code=%s", code)
        return code
    except Exception:
        logger.exception("Error while creating new test.")
        return None


def get_active_tests(owner_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Return list of active tests.
    If owner_user_id is set, only tests created by that admin are returned.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if owner_user_id is not None:
            cur.execute(
                "SELECT code, description, created_at, owner_user_id FROM tests "
                "WHERE is_active = 1 AND owner_user_id = ? ORDER BY created_at DESC",
                (owner_user_id,),
            )
        else:
            cur.execute(
                "SELECT code, description, created_at, owner_user_id FROM tests "
                "WHERE is_active = 1 ORDER BY created_at DESC"
            )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        logger.exception("Error while getting active tests.")
        return []


def deactivate_test(code: str, owner_user_id: Optional[int] = None) -> bool:
    """
    Deactivate (soft delete) a test by its code.
    If owner_user_id is set, only the test belonging to that admin can be deactivated.
    Returns True if at least one row was updated.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        if owner_user_id is not None:
            cur.execute(
                "UPDATE tests SET is_active = 0 WHERE code = ? AND is_active = 1 "
                "AND owner_user_id = ?",
                (code, owner_user_id),
            )
        else:
            cur.execute(
                "UPDATE tests SET is_active = 0 WHERE code = ? AND is_active = 1",
                (code,),
            )
        affected = cur.rowcount
        conn.commit()
        conn.close()
        if affected:
            logger.info("Deactivated test with code=%s", code)
            return True
        logger.info("No active test found to deactivate for code=%s", code)
        return False
    except Exception:
        logger.exception("Error while deactivating test with code=%s", code)
        return False


def get_results_by_test_code(test_code: str) -> List[Dict[str, Any]]:
    """Return all results rows for a given test code."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM results WHERE test_code = ?",
            (test_code,),
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception:
        logger.exception(
            "Error while getting results list for test_code=%s",
            test_code,
        )
        return []


def get_user_result(test_code: str, user_id: int) -> Optional[Dict[str, Any]]:
    """Get a single result row for given test and user."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM results WHERE test_code = ? AND user_id = ?",
            (test_code, user_id),
        )
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception(
            "Error while getting result for test_code=%s, user_id=%s",
            test_code,
            user_id,
        )
        return None


def upsert_result(
    test_code: str,
    user_id: int,
    answers_json: str,
    is_completed: bool,
    last_name: str = "",
) -> bool:
    """
    Insert or update result for given test and user.

    Used both for partial progress (is_completed=False) and final result.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM results WHERE test_code = ? AND user_id = ?",
            (test_code, user_id),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE results
                SET answers = ?, is_completed = ?, last_name = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    answers_json,
                    int(is_completed),
                    last_name,
                    datetime.utcnow().isoformat(),
                    row["id"],
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO results (test_code, user_id, last_name, answers, is_completed, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    test_code,
                    user_id,
                    last_name,
                    answers_json,
                    int(is_completed),
                    datetime.utcnow().isoformat(),
                ),
            )

        conn.commit()
        conn.close()
        logger.info(
            "Saved result for test_code=%s, user_id=%s, is_completed=%s",
            test_code,
            user_id,
            is_completed,
        )
        return True
    except Exception:
        logger.exception(
            "Error while saving result for test_code=%s, user_id=%s",
            test_code,
            user_id,
        )
        return False


def reset_result(test_code: str, user_id: int) -> None:
    """Delete any existing result for given test and user (used for restart)."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM results WHERE test_code = ? AND user_id = ?",
            (test_code, user_id),
        )
        conn.commit()
        conn.close()
        logger.info("Reset result for test_code=%s, user_id=%s", test_code, user_id)
    except Exception:
        logger.exception(
            "Error while resetting result for test_code=%s, user_id=%s",
            test_code,
            user_id,
        )

