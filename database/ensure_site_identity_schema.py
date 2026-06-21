"""ensure_site_identity_schema for GLAND site identity table."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


SITE_IDENTITY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS site_identity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_title VARCHAR(180) NOT NULL DEFAULT '',
    meta_description TEXT NULL,
    canonical_url VARCHAR(255) NOT NULL DEFAULT '',
    logo_path VARCHAR(255) NOT NULL DEFAULT '',
    header_icon_path VARCHAR(255) NOT NULL DEFAULT '',
    favicon_path VARCHAR(255) NOT NULL DEFAULT '',
    preloader_text VARCHAR(80) NOT NULL DEFAULT '',
    youtube_url VARCHAR(255) NOT NULL DEFAULT '',
    github_url VARCHAR(255) NOT NULL DEFAULT '',
    instagram_url VARCHAR(255) NOT NULL DEFAULT '',
    linkedin_url VARCHAR(255) NOT NULL DEFAULT '',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


REQUIRED_COLUMNS = {
    "site_title": "VARCHAR(180) NOT NULL DEFAULT ''",
    "meta_description": "TEXT NULL",
    "canonical_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "logo_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "header_icon_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "favicon_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "preloader_text": "VARCHAR(80) NOT NULL DEFAULT ''",
    "youtube_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "github_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "instagram_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "linkedin_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
}


DEFAULT_SITE_IDENTITY = {
    "site_title": "Gland Siahaan | AI Engineer & UI/UX Web Designer in Medan",
    "meta_description": "Gland Siahaan is a Medan-based AI Engineering and UI/UX Web Design student creating clear web experiences, automation ideas, and digital branding.",
    "canonical_url": "https://gblessshn-boop.github.io/gland-portfolio-v2.0.0-bytemplatematias-vibe-coding/",
    "logo_path": "assets/img/logo/gland-header-icon.gif",
    "header_icon_path": "assets/img/logo/gland-header-icon.gif",
    "favicon_path": "assets/img/logo/favicon.png",
    "preloader_text": "GLAND",
    "youtube_url": "https://www.youtube.com/@glandjermanoblessedsiahaan",
    "github_url": "https://github.com/GblessSHN-boop",
    "instagram_url": "https://www.instagram.com/glandshn?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw==",
    "linkedin_url": "https://www.linkedin.com/in/glandsiahaan",
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
          AND TABLE_NAME = 'site_identity'
        """,
        (config.DB_NAME,),
    )

    return {row[0] for row in cursor.fetchall()}


def ensure_default_row(cursor):
    cursor.execute("SELECT COUNT(*) FROM site_identity")
    count = cursor.fetchone()[0]

    if count > 0:
        return False

    cursor.execute(
        """
        INSERT INTO site_identity (
            site_title, meta_description, canonical_url,
            logo_path, header_icon_path, favicon_path, preloader_text,
            youtube_url, github_url, instagram_url, linkedin_url,
            is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            DEFAULT_SITE_IDENTITY["site_title"],
            DEFAULT_SITE_IDENTITY["meta_description"],
            DEFAULT_SITE_IDENTITY["canonical_url"],
            DEFAULT_SITE_IDENTITY["logo_path"],
            DEFAULT_SITE_IDENTITY["header_icon_path"],
            DEFAULT_SITE_IDENTITY["favicon_path"],
            DEFAULT_SITE_IDENTITY["preloader_text"],
            DEFAULT_SITE_IDENTITY["youtube_url"],
            DEFAULT_SITE_IDENTITY["github_url"],
            DEFAULT_SITE_IDENTITY["instagram_url"],
            DEFAULT_SITE_IDENTITY["linkedin_url"],
            DEFAULT_SITE_IDENTITY["is_active"],
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
        cursor.execute(SITE_IDENTITY_TABLE_SQL)

        existing_columns = get_existing_columns(cursor)

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE site_identity "
                f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
            )
            added_columns.append(column_name)

        inserted_default = ensure_default_row(cursor)

        connection.commit()

        print("Site identity schema ensured successfully.")
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