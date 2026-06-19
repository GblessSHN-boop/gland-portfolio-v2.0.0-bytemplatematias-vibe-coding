"""ensure_projects_schema for GLAND projects table."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


PROJECTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(160) NOT NULL DEFAULT '',
    category VARCHAR(120) NOT NULL DEFAULT '',
    description TEXT NULL,
    image_path VARCHAR(255) NULL,
    project_url VARCHAR(255) NULL,
    repo_url VARCHAR(255) NULL,
    technologies VARCHAR(255) NULL,
    display_order INT NOT NULL DEFAULT 0,
    is_featured TINYINT(1) NOT NULL DEFAULT 1,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


REQUIRED_COLUMNS = {
    "title": "VARCHAR(160) NOT NULL DEFAULT ''",
    "category": "VARCHAR(120) NOT NULL DEFAULT ''",
    "description": "TEXT NULL",
    "image_path": "VARCHAR(255) NULL",
    "project_url": "VARCHAR(255) NULL",
    "repo_url": "VARCHAR(255) NULL",
    "technologies": "VARCHAR(255) NULL",
    "display_order": "INT NOT NULL DEFAULT 0",
    "is_featured": "TINYINT(1) NOT NULL DEFAULT 1",
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
          AND TABLE_NAME = 'projects'
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
        cursor.execute(PROJECTS_TABLE_SQL)

        existing_columns = get_existing_columns(cursor)

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE projects "
                f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
            )
            added_columns.append(column_name)

        connection.commit()

        print("Projects schema ensured successfully.")
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