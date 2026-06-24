"""
SQLite storage for boat events.
"""

import sqlite3
import datetime
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class BoatStorage:
    """Handles persistent storage of boat events in SQLite."""

    def __init__(self, db_path: str = "boats.db"):
        """Initialize database and create tables if they don't exist."""
        self.db_path = Path("/home/nick/Projects/Telegram Nick Assistant") / db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Create boat_events table if it doesn't exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS boat_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    boat_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pier TEXT,
                    program TEXT,
                    chat_id INTEGER,
                    message_id INTEGER,
                    UNIQUE(chat_id, message_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_boat_name ON boat_events(boat_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON boat_events(timestamp)")
            
            # Diary entries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER NOT NULL,
                    file_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_diary_timestamp ON diary_entries(timestamp)")

            logger.info("BoatStorage initialized at %s", self.db_path)

    def log_event(
        self,
        boat_name: str,
        status: str,
        pier: str = None,
        program: str = None,
        chat_id: int = None,
        message_id: int = None,
        timestamp: datetime.datetime = None,
    ):
        """Log a new boat event. Ignores duplicates based on chat_id/message_id."""
        with self._get_connection() as conn:
            if timestamp:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO boat_events (boat_name, status, pier, program, chat_id, message_id, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (boat_name, status, pier, program, chat_id, message_id, timestamp),
                )
            else:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO boat_events (boat_name, status, pier, program, chat_id, message_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (boat_name, status, pier, program, chat_id, message_id),
                )
            logger.debug("Logged boat event: %s - %s", boat_name, status)

    def get_todays_events(self) -> List[Dict[str, Any]]:
        """Get all events logged in the last 24 hours."""
        # Use 24-hour window instead of strict UTC date to catch shifts
        threshold = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24))
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM boat_events 
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
                """,
                (threshold,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Diary Methods ---
    def log_diary_entry(self, message_id: int, file_id: str = None, timestamp: datetime.datetime = None):
        """Save a new diary entry."""
        with self._get_connection() as conn:
            if timestamp:
                conn.execute(
                    "INSERT INTO diary_entries (timestamp, message_id, file_id) VALUES (?, ?, ?)",
                    (timestamp, message_id, file_id)
                )
            else:
                conn.execute(
                    "INSERT INTO diary_entries (message_id, file_id) VALUES (?, ?)",
                    (message_id, file_id)
                )
            logger.debug("Logged diary entry: %s", message_id)

    def get_recent_diary_entries(self, limit: int = 7) -> List[Dict[str, Any]]:
        """Get the most recent diary entries, ordered by timestamp descending."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM diary_entries ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def has_diary_entry_for_today(self, tz_offset_hours: int = 7) -> bool:
        """Check if there is a diary entry for the current day (with given timezone offset)."""
        now = datetime.datetime.now(datetime.timezone.utc)
        start_of_day = (now + datetime.timedelta(hours=tz_offset_hours)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - datetime.timedelta(hours=tz_offset_hours)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM diary_entries WHERE timestamp >= ? LIMIT 1",
                (start_of_day,)
            )
            return cursor.fetchone() is not None

    def get_latest_status_all_boats(self) -> List[Dict[str, Any]]:
        """Get the latest status for each boat logged in the last 24 hours."""
        threshold = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24))
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM boat_events e1
                WHERE id = (
                    SELECT id FROM boat_events e2 
                    WHERE e1.boat_name = e2.boat_name AND timestamp >= ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT 1
                )
                ORDER BY boat_name ASC
                """,
                (threshold,),
            )
            return [dict(row) for row in cursor.fetchall()]
