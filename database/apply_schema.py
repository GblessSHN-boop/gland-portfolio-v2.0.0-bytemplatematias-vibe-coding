from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config
from backend.db import get_connection


SCHEMA_FILE = PROJECT_ROOT / "database" / "schema.sql"


def quote_identifier(identifier):
    safe_identifier = identifier.replace("_", "")

    if not safe_identifier.isalnum():
        raise ValueError(f"Unsafe database identifier: {identifier}")

    return f"`{identifier}`"


def split_sql_statements(sql_text):
    sql_text = sql_text.lstrip("\ufeff")

    statements = []
    buffer = []
    quote = None
    escape = False
    index = 0

    while index < len(sql_text):
        char = sql_text[index]
        next_char = sql_text[index + 1] if index + 1 < len(sql_text) else ""

        if quote:
            buffer.append(char)

            if char == "\\" and not escape:
                escape = True
                index += 1
                continue

            if char == quote and not escape:
                quote = None

            escape = False
            index += 1
            continue

        if char in ("'", '"', "`"):
            quote = char
            buffer.append(char)
            index += 1
            continue

        if char == "-" and next_char == "-":
            while index < len(sql_text) and sql_text[index] not in ("\n", "\r"):
                index += 1
            continue

        if char == "#":
            while index < len(sql_text) and sql_text[index] not in ("\n", "\r"):
                index += 1
            continue

        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(sql_text) and not (sql_text[index] == "*" and sql_text[index + 1] == "/"):
                index += 1
            index += 2
            continue

        if char == ";":
            statement = "".join(buffer).strip()

            if statement:
                statements.append(statement)

            buffer = []
            index += 1
            continue

        buffer.append(char)
        index += 1

    statement = "".join(buffer).strip()

    if statement:
        statements.append(statement)

    return statements


def is_database_control_statement(statement):
    normalized = " ".join(statement.split()).lower()

    return (
        normalized.startswith("create database")
        or normalized.startswith("create schema")
        or normalized.startswith("use ")
    )


def main():
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"schema.sql tidak ditemukan: {SCHEMA_FILE}")

    database_name = quote_identifier(config.DB_NAME)
    sql_text = SCHEMA_FILE.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)

    connection = get_connection(use_database=False)
    cursor = connection.cursor()

    executed = 0
    skipped = 0

    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {database_name} "
            "DEFAULT CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )

        cursor.execute(f"USE {database_name}")

        for statement in statements:
            if is_database_control_statement(statement):
                skipped += 1
                continue

            cursor.execute(statement)
            executed += 1

        connection.commit()

        print("Database schema applied successfully.")
        print(f"Database name: {config.DB_NAME}")
        print(f"Statements executed: {executed}")
        print(f"Statements skipped: {skipped}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()