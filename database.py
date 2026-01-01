import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "meter.db")


def init_db():
    """Initialize the database schema."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens_in INTEGER NOT NULL,
            tokens_out INTEGER NOT NULL,
            cost REAL NOT NULL,
            latency_ms INTEGER NOT NULL,
            team TEXT NOT NULL,
            feature TEXT NOT NULL,
            environment TEXT NOT NULL,
            prompt_hash TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_team ON usage_logs(team)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_feature ON usage_logs(feature)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_environment ON usage_logs(environment)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON usage_logs(timestamp)
    """)

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
