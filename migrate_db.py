#!/usr/bin/env python3
"""
Database migration script for Telegram Nick Assistant.
Adds UNIQUE(chat_id, message_id) constraint to boat_events table,
eliminating existing duplicates and preventing future ones.
"""

import sqlite3
import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("migration")

DB_PATH = "boats.db"
BAK_PATH = "boats.db.bak"

def migrate():
    if not os.path.exists(DB_PATH):
        logger.info("Database file '%s' does not exist. Nothing to migrate.", DB_PATH)
        return

    # 1. Create a backup
    logger.info("Creating backup of '%s' -> '%s'...", DB_PATH, BAK_PATH)
    try:
        shutil.copy2(DB_PATH, BAK_PATH)
        logger.info("Backup created successfully.")
    except Exception as e:
        logger.error("Failed to create backup: %s. Migration aborted.", e)
        return

    # 2. Connect and migrate
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        
        # Check if UNIQUE constraint already exists in the table schema
        cursor.execute("PRAGMA table_info(boat_events)")
        columns = cursor.fetchall()
        
        # In SQLite, we can inspect if UNIQUE exists by trying to find it in the SQL representation of the schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='boat_events'")
        sql_res = cursor.fetchone()
        
        if not sql_res:
            logger.error("Table 'boat_events' not found in database. Migration aborted.")
            conn.close()
            return
            
        sql_schema = sql_res[0]
        if "UNIQUE" in sql_schema or "unique" in sql_schema.lower():
            logger.info("Table 'boat_events' already has UNIQUE constraint. No migration needed.")
            conn.close()
            return

        logger.info("Starting database migration...")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Rename old table
        logger.info("Renaming old 'boat_events' table to 'boat_events_old'...")
        cursor.execute("ALTER TABLE boat_events RENAME TO boat_events_old;")
        
        # Create new table with UNIQUE constraint
        logger.info("Creating new 'boat_events' table with UNIQUE constraint...")
        cursor.execute("""
            CREATE TABLE boat_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                boat_name TEXT NOT NULL,
                status TEXT NOT NULL,
                pier TEXT,
                program TEXT,
                chat_id INTEGER,
                message_id INTEGER,
                UNIQUE(chat_id, message_id)
            );
        """)
        
        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_boat_name ON boat_events(boat_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON boat_events(timestamp);")
        
        # Copy data, ignoring duplicates
        logger.info("Copying data into the new table (pruning duplicates)...")
        cursor.execute("""
            INSERT OR IGNORE INTO boat_events (id, timestamp, boat_name, status, pier, program, chat_id, message_id)
            SELECT id, timestamp, boat_name, status, pier, program, chat_id, message_id 
            FROM boat_events_old;
        """)
        
        # Drop old table
        logger.info("Dropping temporary table 'boat_events_old'...")
        cursor.execute("DROP TABLE boat_events_old;")
        
        # Commit transaction
        conn.commit()
        logger.info("Migration completed successfully!")
        
        # Verify row counts
        cursor.execute("SELECT count(*) FROM boat_events")
        new_count = cursor.fetchone()[0]
        logger.info("Remaining unique events in database: %s", new_count)

    except Exception as e:
        logger.error("Error occurred during migration: %s. Rolling back changes...", e)
        try:
            conn.rollback()
        except Exception:
            pass
        # Restore backup if failed
        logger.info("Restoring backup from '%s'...", BAK_PATH)
        shutil.copy2(BAK_PATH, DB_PATH)
        logger.info("Backup restored.")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
