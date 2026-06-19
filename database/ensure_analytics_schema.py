"""ensure_analytics_schema for GLAND analytics tables."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


ANALYTICS_VISITS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analytics_visits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id VARCHAR(120) NOT NULL DEFAULT '',
    session_id VARCHAR(120) NOT NULL DEFAULT '',
    ip_address VARCHAR(80) NOT NULL DEFAULT '',
    user_agent TEXT NULL,
    page_path VARCHAR(255) NOT NULL DEFAULT '',
    referrer VARCHAR(255) NOT NULL DEFAULT '',
    device_type VARCHAR(80) NOT NULL DEFAULT '',
    browser_name VARCHAR(120) NOT NULL DEFAULT '',
    duration_seconds INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


ANALYTICS_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id VARCHAR(120) NOT NULL DEFAULT '',
    session_id VARCHAR(120) NOT NULL DEFAULT '',
    event_type VARCHAR(120) NOT NULL DEFAULT '',
    event_name VARCHAR(180) NOT NULL DEFAULT '',
    event_value VARCHAR(255) NOT NULL DEFAULT '',
    page_path VARCHAR(255) NOT NULL DEFAULT '',
    target_url VARCHAR(255) NOT NULL DEFAULT '',
    metadata_json LONGTEXT NULL,
    ip_address VARCHAR(80) NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


VISIT_COLUMNS = {
    "visitor_id": "VARCHAR(120) NOT NULL DEFAULT ''",
    "session_id": "VARCHAR(120) NOT NULL DEFAULT ''",
    "ip_address": "VARCHAR(80) NOT NULL DEFAULT ''",
    "user_agent": "TEXT NULL",
    "page_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "referrer": "VARCHAR(255) NOT NULL DEFAULT ''",
    "device_type": "VARCHAR(80) NOT NULL DEFAULT ''",
    "browser_name": "VARCHAR(120) NOT NULL DEFAULT ''",
    "duration_seconds": "INT NOT NULL DEFAULT 0",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}


EVENT_COLUMNS = {
    "visitor_id": "VARCHAR(120) NOT NULL DEFAULT ''",
    "session_id": "VARCHAR(120) NOT NULL DEFAULT ''",
    "event_type": "VARCHAR(120) NOT NULL DEFAULT ''",
    "event_name": "VARCHAR(180) NOT NULL DEFAULT ''",
    "event_value": "VARCHAR(255) NOT NULL DEFAULT ''",
    "page_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "target_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "metadata_json": "LONGTEXT NULL",
    "ip_address": "VARCHAR(80) NOT NULL DEFAULT ''",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
}


def quote_identifier(identifier):
    safe_identifier = identifier.replace("_", "")

    if not safe_identifier.isalnum():
        raise ValueError(f"Unsafe identifier: {identifier}")

    return f"`{identifier}`"


def get_existing_columns(cursor, table_name):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
        """,
        (config.DB_NAME, table_name),
    )

    return {row[0] for row in cursor.fetchall()}


def ensure_columns(cursor, table_name, required_columns):
    existing_columns = get_existing_columns(cursor, table_name)
    added_columns = []

    for column_name, column_definition in required_columns.items():
        if column_name in existing_columns:
            continue

        cursor.execute(
            f"ALTER TABLE {quote_identifier(table_name)} "
            f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
        )
        added_columns.append(f"{table_name}.{column_name}")

    return added_columns


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

        cursor.execute(ANALYTICS_VISITS_TABLE_SQL)
        cursor.execute(ANALYTICS_EVENTS_TABLE_SQL)

        added_columns.extend(ensure_columns(cursor, "analytics_visits", VISIT_COLUMNS))
        added_columns.extend(ensure_columns(cursor, "analytics_events", EVENT_COLUMNS))

        connection.commit()

        print("Analytics schema ensured successfully.")
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