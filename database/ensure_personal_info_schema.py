"""ensure_personal_info_schema for GLAND personal profile table."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


PERSONAL_INFO_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS personal_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL DEFAULT '',
    role_title VARCHAR(160) NOT NULL DEFAULT '',
    description TEXT NULL,
    email VARCHAR(160) NOT NULL DEFAULT '',
    phone VARCHAR(80) NOT NULL DEFAULT '',
    address VARCHAR(160) NOT NULL DEFAULT '',
    photo_path VARCHAR(255) NULL,
    resume_url VARCHAR(255) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


REQUIRED_COLUMNS = {
    "full_name": "VARCHAR(160) NOT NULL DEFAULT ''",
    "role_title": "VARCHAR(160) NOT NULL DEFAULT ''",
    "description": "TEXT NULL",
    "email": "VARCHAR(160) NOT NULL DEFAULT ''",
    "phone": "VARCHAR(80) NOT NULL DEFAULT ''",
    "address": "VARCHAR(160) NOT NULL DEFAULT ''",
    "photo_path": "VARCHAR(255) NULL",
    "resume_url": "VARCHAR(255) NULL",
    "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
}


DEFAULT_PERSONAL_INFO = {
    "full_name": "Gland Jermano Blessed Siahaan",
    "role_title": "AI Engineer & Creative Designer",
    "description": "I'm a college student from Medan, Indonesia, shaping digital ideas through AI, design, and strategy. I enjoy building clean web experiences, creative visuals, and meaningful digital solutions that feel alive and professional.",
    "email": "glandjermanoblessedsiahaan@gmail.com",
    "phone": "(+62)-895-4048-71011",
    "address": "Medan, Indonesia",
    "photo_path": "assets/img/about/gland-personal-info.png",
    "resume_url": "",
    "is_active": 1,
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
          AND TABLE_NAME = 'personal_info'
        """,
        (config.DB_NAME,),
    )

    return {row[0] for row in cursor.fetchall()}


def ensure_default_row(cursor):
    cursor.execute("SELECT COUNT(*) FROM personal_info")
    count = cursor.fetchone()[0]

    if count > 0:
        return False

    cursor.execute(
        """
        INSERT INTO personal_info (
            full_name, role_title, description, email, phone, address,
            photo_path, resume_url, is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            DEFAULT_PERSONAL_INFO["full_name"],
            DEFAULT_PERSONAL_INFO["role_title"],
            DEFAULT_PERSONAL_INFO["description"],
            DEFAULT_PERSONAL_INFO["email"],
            DEFAULT_PERSONAL_INFO["phone"],
            DEFAULT_PERSONAL_INFO["address"],
            DEFAULT_PERSONAL_INFO["photo_path"],
            DEFAULT_PERSONAL_INFO["resume_url"],
            DEFAULT_PERSONAL_INFO["is_active"],
        ),
    )

    return True


def main():
    database_name = quote_identifier(config.DB_NAME)

    connection = get_connection(use_database=False)
    cursor = connection.cursor()

    added_columns = []
    inserted_default = False

    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {database_name} "
            "DEFAULT CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE {database_name}")
        cursor.execute(PERSONAL_INFO_TABLE_SQL)

        existing_columns = get_existing_columns(cursor)

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE personal_info "
                f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
            )
            added_columns.append(column_name)

        inserted_default = ensure_default_row(cursor)

        connection.commit()

        print("Personal info schema ensured successfully.")
        print(f"Database name: {config.DB_NAME}")
        print(f"Added columns: {', '.join(added_columns) if added_columns else 'none'}")
        print(f"Inserted default row: {'yes' if inserted_default else 'no'}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()