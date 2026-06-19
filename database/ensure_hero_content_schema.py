"""ensure_hero_content_schema for GLAND hero section table."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


HERO_CONTENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hero_content (
    id INT AUTO_INCREMENT PRIMARY KEY,
    eyebrow VARCHAR(160) NOT NULL DEFAULT '',
    title_line_1 VARCHAR(160) NOT NULL DEFAULT '',
    title_line_2 VARCHAR(160) NOT NULL DEFAULT '',
    description TEXT NULL,
    availability_text VARCHAR(255) NOT NULL DEFAULT '',
    availability_location VARCHAR(120) NOT NULL DEFAULT '',
    phone_label VARCHAR(80) NOT NULL DEFAULT '',
    phone_url VARCHAR(255) NOT NULL DEFAULT '',
    intro_video_label VARCHAR(80) NOT NULL DEFAULT '',
    intro_video_url VARCHAR(255) NOT NULL DEFAULT '',
    hero_media_type VARCHAR(20) NOT NULL DEFAULT 'video',
    hero_media_path VARCHAR(255) NOT NULL DEFAULT '',
    background_image_path VARCHAR(255) NOT NULL DEFAULT '',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


REQUIRED_COLUMNS = {
    "eyebrow": "VARCHAR(160) NOT NULL DEFAULT ''",
    "title_line_1": "VARCHAR(160) NOT NULL DEFAULT ''",
    "title_line_2": "VARCHAR(160) NOT NULL DEFAULT ''",
    "description": "TEXT NULL",
    "availability_text": "VARCHAR(255) NOT NULL DEFAULT ''",
    "availability_location": "VARCHAR(120) NOT NULL DEFAULT ''",
    "phone_label": "VARCHAR(80) NOT NULL DEFAULT ''",
    "phone_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "intro_video_label": "VARCHAR(80) NOT NULL DEFAULT ''",
    "intro_video_url": "VARCHAR(255) NOT NULL DEFAULT ''",
    "hero_media_type": "VARCHAR(20) NOT NULL DEFAULT 'video'",
    "hero_media_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "background_image_path": "VARCHAR(255) NOT NULL DEFAULT ''",
    "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
}


DEFAULT_HERO_CONTENT = {
    "eyebrow": "Hello, I'm Gland",
    "title_line_1": "AI Engineer",
    "title_line_2": "Creative Designer",
    "description": "I build digital experiences through AI, design, and clear web strategy.",
    "availability_text": "Available for AI, Vibe Coding, UI/UX, and Design Projects",
    "availability_location": "Worldwide",
    "phone_label": "(+62)-895-4048-71011",
    "phone_url": "https://wa.me/62895404871011",
    "intro_video_label": "Intro Video",
    "intro_video_url": "https://www.youtube.com/watch?v=YuBB8pYAv-8",
    "hero_media_type": "video",
    "hero_media_path": "assets/video/hero-right-iklan-4k.mp4",
    "background_image_path": "",
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
          AND TABLE_NAME = 'hero_content'
        """,
        (config.DB_NAME,),
    )

    return {row[0] for row in cursor.fetchall()}


def ensure_default_row(cursor):
    cursor.execute("SELECT COUNT(*) FROM hero_content")
    count = cursor.fetchone()[0]

    if count > 0:
        return False

    cursor.execute(
        """
        INSERT INTO hero_content (
            eyebrow, title_line_1, title_line_2, description,
            availability_text, availability_location, phone_label, phone_url,
            intro_video_label, intro_video_url, hero_media_type, hero_media_path,
            background_image_path, is_active
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            DEFAULT_HERO_CONTENT["eyebrow"],
            DEFAULT_HERO_CONTENT["title_line_1"],
            DEFAULT_HERO_CONTENT["title_line_2"],
            DEFAULT_HERO_CONTENT["description"],
            DEFAULT_HERO_CONTENT["availability_text"],
            DEFAULT_HERO_CONTENT["availability_location"],
            DEFAULT_HERO_CONTENT["phone_label"],
            DEFAULT_HERO_CONTENT["phone_url"],
            DEFAULT_HERO_CONTENT["intro_video_label"],
            DEFAULT_HERO_CONTENT["intro_video_url"],
            DEFAULT_HERO_CONTENT["hero_media_type"],
            DEFAULT_HERO_CONTENT["hero_media_path"],
            DEFAULT_HERO_CONTENT["background_image_path"],
            DEFAULT_HERO_CONTENT["is_active"],
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
        cursor.execute(HERO_CONTENT_TABLE_SQL)

        existing_columns = get_existing_columns(cursor)

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE hero_content "
                f"ADD COLUMN {quote_identifier(column_name)} {column_definition}"
            )
            added_columns.append(column_name)

        inserted_default = ensure_default_row(cursor)

        connection.commit()

        print("Hero content schema ensured successfully.")
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