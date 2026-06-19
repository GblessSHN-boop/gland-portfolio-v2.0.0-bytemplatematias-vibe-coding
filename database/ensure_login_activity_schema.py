"""
Ensure admin login activity audit table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.auth_service import get_connection


def ensure_login_activity_schema():
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_login_events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NULL,
                event_type VARCHAR(50) NOT NULL,
                identifier VARCHAR(150) DEFAULT NULL,
                success TINYINT(1) DEFAULT 0,
                ip_address VARCHAR(64) DEFAULT NULL,
                user_agent TEXT DEFAULT NULL,
                message VARCHAR(255) DEFAULT NULL,
                alert_email_sent TINYINT(1) DEFAULT 0,
                alert_error TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_admin_login_events_admin_id (admin_id),
                INDEX idx_admin_login_events_event_type (event_type),
                INDEX idx_admin_login_events_success (success),
                INDEX idx_admin_login_events_created_at (created_at),
                CONSTRAINT fk_admin_login_events_admin_id
                    FOREIGN KEY (admin_id)
                    REFERENCES admin_users(id)
                    ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        connection.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM admin_login_events")
        row = cursor.fetchone() or {"total": 0}

        return {
            "success": True,
            "table": "admin_login_events",
            "event_count": int(row["total"]),
        }

    finally:
        connection.close()


def main():
    print(json.dumps(ensure_login_activity_schema(), indent=2, default=str))


if __name__ == "__main__":
    main()