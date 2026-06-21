"""
Ensure admin password reset schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth_service import get_connection


def ensure_password_reset_schema():
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_password_reset_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                token_hash VARCHAR(128) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                used_at DATETIME DEFAULT NULL,
                requested_ip VARCHAR(64) DEFAULT NULL,
                requested_user_agent TEXT DEFAULT NULL,
                email_sent TINYINT(1) DEFAULT 0,
                email_error TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_admin_password_reset_tokens_admin_id (admin_id),
                INDEX idx_admin_password_reset_tokens_token_hash (token_hash),
                INDEX idx_admin_password_reset_tokens_expires_at (expires_at),
                INDEX idx_admin_password_reset_tokens_used_at (used_at),
                CONSTRAINT fk_admin_password_reset_tokens_admin_id
                    FOREIGN KEY (admin_id)
                    REFERENCES admin_users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            DELETE FROM admin_password_reset_tokens
            WHERE expires_at <= UTC_TIMESTAMP()
               OR used_at IS NOT NULL
            """
        )

        connection.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM admin_password_reset_tokens")
        row = cursor.fetchone() or {"total": 0}

        return {
            "success": True,
            "table": "admin_password_reset_tokens",
            "active_token_count": int(row["total"]),
        }

    finally:
        connection.close()


def main():
    print(json.dumps(ensure_password_reset_schema(), indent=2, default=str))


if __name__ == "__main__":
    main()