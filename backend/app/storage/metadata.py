import sqlite3
from pathlib import Path
from datetime import datetime
import os

DB_PATH = "data/metadata.db"

def init_db():
    """Initializes the SQLite database and creates the 'files' table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) # Ensure data directory exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT UNIQUE NOT NULL,
        last_modified_timestamp DATETIME,
        indexed_at_timestamp DATETIME,
        num_chunks_indexed INTEGER
    )
    """)
    conn.commit()
    conn.close()
    print(f"[Metadata] Database initialized at {DB_PATH}")

def save_file_metadata(file_path: str, last_modified_os: datetime, indexed_at: datetime, num_chunks: int):
    """
    Saves or updates metadata for a file.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO files (file_path, last_modified_timestamp, indexed_at_timestamp, num_chunks_indexed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            last_modified_timestamp = ?,
            indexed_at_timestamp = ?,
            num_chunks_indexed = ?
        """,
        (file_path, last_modified_os, indexed_at, num_chunks,
         last_modified_os, indexed_at, num_chunks)
    )
    conn.commit()
    conn.close()
    # print(f"[Metadata] Saved/Updated metadata for {file_path}")

def get_file_metadata(file_path: str) -> dict | None:
    """
    Retrieves metadata for a specific file path.
    Returns a dictionary or None if not found.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, last_modified_timestamp, indexed_at_timestamp, num_chunks_indexed FROM files WHERE file_path = ?", (file_path,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "file_path": row[0],
            "last_modified_timestamp": datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1],
            "indexed_at_timestamp": datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2],
            "num_chunks_indexed": row[3]
        }
    return None

def update_file_metadata(file_path: str, last_modified_os: datetime, indexed_at: datetime, num_chunks: int):
    """
    Updates the metadata for an existing file.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE files SET last_modified_timestamp = ?, indexed_at_timestamp = ?, num_chunks_indexed = ?
        WHERE file_path = ?
        """,
        (last_modified_os, indexed_at, num_chunks, file_path)
    )
    conn.commit()
    conn.close()
    # print(f"[Metadata] Updated metadata for {file_path}")

def delete_file_metadata(file_path: str):
    """Deletes metadata for a file."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()
    print(f"[Metadata] Deleted metadata for {file_path}")


def file_is_indexed(file_path: str, current_last_modified_os: datetime) -> bool:
    """
    Checks if a file is already indexed and up-to-date based on its last modified timestamp.
    """
    metadata = get_file_metadata(file_path)
    if metadata:
        # Check if the stored last_modified_timestamp is greater than or equal to the current OS timestamp
        # Using >= because OS timestamps might have less precision and a newly written file could have the same timestamp
        return metadata["last_modified_timestamp"] >= current_last_modified_os
    return False

def get_all_indexed_files_metadata() -> list[dict]:
    """
    Retrieves metadata for all files currently in the database.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, last_modified_timestamp, indexed_at_timestamp, num_chunks_indexed FROM files")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "file_path": row[0],
            "last_modified_timestamp": datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1],
            "indexed_at_timestamp": datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2],
            "num_chunks_indexed": row[3]
        })
    return result