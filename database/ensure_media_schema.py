"""ensure_media_schema for GLAND media files table."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


MEDIA_FILES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS media_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(180) NOT NULL DEFAULT '',
    alt_text VARCHAR(255) NOT NULL DEFAULT '',
    media_type VARCHAR(20) NOT NULL DEFAULT '',
    file_name VARCHAR(255) NOT NULL DEFAULT '',
    file_path VARCHAR(255) NOT NULL DEFAULT '',
    mime_type VARCHAR(120) NOT NULL DEFAULT '',
    file_size BIGINT NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


REQUIRED_COLUMNS = {
    "title": "VARCHAR(180) NOT NULL DEFAULT ''",
    "alt_text": "VARCHAR(255) NOT NULL DEFAULT ''",
    "media_type": "VARCHAR(20) NOT NULL DEFAULT ''",
    "file_name": "VARCHAR(255) NOT NULL DEFAULT ''",
    "file_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "mime_type": "VARCHAR(120) NOT NULL DEFAULT ''",
    "file_size": "BIGINT NOT NULL DEFAULT 0",
    "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
}


def quote_identifier(identifier):
    safe_identifier = identifier.replace("_", "")

    if not safe_identifier.isalnum():
        raise ValueError(f"Unsafe identifier: {identifier}")

    return f"`{identifier}`"


def get_existing_columns(cursor):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = 'media_files'
        """,
        (config.DB_NAME,),
    )

    return {row[0] for row in cursor.fetchall()}


def main():
    database_name = quote_identifier(config.DB_NAME)

    connection = get_connection(use_database=False)
    cursor = connection.cursor()

    added_columns = []

    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {database_name} "
            "DEFAULT CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE {database_name}")
        cursor.execute(MEDIA_FILES_TABLE_SQL)

        existing_columns = get_existing_columns(cursor)

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE media_files "
                f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
            )
            added_columns.append(column_name)

        connection.commit()

        print("Media files schema ensured successfully.")
        print(f"Database name: {config.DB_NAME}")
        print(f"Added columns: {', '.join(added_columns) if added_columns else 'none'}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()