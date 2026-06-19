"""
Ensure admin authentication schema and a local default admin user.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from typing import Any, Dict

# GLAND ENSURE AUTH ROOT PATH START
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# GLAND ENSURE AUTH ROOT PATH END
try:
    import config
except Exception as exc:
    raise SystemExit(f"Unable to import config.py: {exc}")

from backend.auth_service import get_connection, hash_password


def _default_username() -> str:
    return str(getattr(config, "ADMIN_DEFAULT_USERNAME", "admin") or "admin").strip() or "admin"


def _default_email() -> str:
    return (
        str(getattr(config, "ADMIN_DEFAULT_EMAIL", "admin@example.local") or "admin@example.local")
        .strip()
        or "admin@example.local"
    )


def ensure_auth_schema(reset_default_admin: bool = False) -> Dict[str, Any]:
    username = _default_username()
    email = _default_email()
    password = os.environ.get("GLAND_ADMIN_DEFAULT_PASSWORD") or f"Gland-{secrets.token_urlsafe(12)}!26"

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                token_hash VARCHAR(128) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                ip_address VARCHAR(64) DEFAULT NULL,
                user_agent TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_admin_sessions_token_hash (token_hash),
                INDEX idx_admin_sessions_admin_id (admin_id),
                INDEX idx_admin_sessions_expires_at (expires_at),
                CONSTRAINT fk_admin_sessions_admin_id
                    FOREIGN KEY (admin_id)
                    REFERENCES admin_users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            DELETE FROM admin_sessions
            WHERE expires_at <= UTC_TIMESTAMP()
            """
        )

        cursor.execute(
            """
            SELECT id, username, email, role, is_active
            FROM admin_users
            WHERE username = %s OR email = %s
            LIMIT 1
            """,
            (username, email),
        )

        existing = cursor.fetchone()
        password_hash = hash_password(password)

        created_default_admin = False
        reset_default_password = False

        if existing:
            if reset_default_admin:
                cursor.execute(
                    """
                    UPDATE admin_users
                    SET
                        username = %s,
                        email = %s,
                        password_hash = %s,
                        role = 'owner',
                        is_active = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (username, email, password_hash, existing["id"]),
                )
                reset_default_password = True
        else:
            cursor.execute(
                """
                INSERT INTO admin_users (
                    username,
                    email,
                    password_hash,
                    role,
                    is_active
                )
                VALUES (%s, %s, %s, 'owner', 1)
                """,
                (username, email, password_hash),
            )
            created_default_admin = True
            reset_default_password = True

        connection.commit()

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM admin_users
            """
        )

        total_users = int(cursor.fetchone()["total"])

        return {
            "success": True,
            "username": username,
            "email": email,
            "admin_user_count": total_users,
            "created_default_admin": created_default_admin,
            "reset_default_password": reset_default_password,
            "default_password": password if reset_default_password else None,
        }

    finally:
        connection.close()


def main() -> None:
    reset_default_admin = "--reset-default-admin" in sys.argv
    result = ensure_auth_schema(reset_default_admin=reset_default_admin)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()