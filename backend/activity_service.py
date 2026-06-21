from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.db import get_connection


ACTIVITY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS admin_activity_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NULL,
    admin_username VARCHAR(150) NOT NULL DEFAULT '',
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(80) NOT NULL DEFAULT '',
    entity_id VARCHAR(80) NOT NULL DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'success',
    description VARCHAR(255) NOT NULL DEFAULT '',
    metadata_json LONGTEXT NULL,
    ip_address VARCHAR(64) NOT NULL DEFAULT '',
    user_agent TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_admin_activity_admin_id (admin_id),
    INDEX idx_admin_activity_action (action),
    INDEX idx_admin_activity_entity (entity_type, entity_id),
    INDEX idx_admin_activity_status (status),
    INDEX idx_admin_activity_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def _normalize_datetime(value: Any) -> str:
    if not value:
        return ""

    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")

    return str(value)


def _safe_json(value: Optional[Dict[str, Any]]) -> str:
    try:
        return json.dumps(value or {}, ensure_ascii=False, default=str)
    except Exception:
        return "{}"


def ensure_admin_activity_schema() -> Dict[str, Any]:
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(ACTIVITY_TABLE_SQL)
        connection.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM admin_activity_events")
        row = cursor.fetchone() or {"total": 0}

        return {
            "success": True,
            "table": "admin_activity_events",
            "event_count": int(row.get("total") or 0),
        }
    finally:
        connection.close()


def create_admin_activity(
    action: str,
    entity_type: str = "",
    entity_id: Any = "",
    status: str = "success",
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    admin_id: Optional[int] = None,
    admin_username: str = "",
    ip_address: str = "",
    user_agent: str = "",
) -> Dict[str, Any]:
    action = str(action or "").strip()
    if not action:
        action = "activity"

    ensure_admin_activity_schema()

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            INSERT INTO admin_activity_events (
                admin_id,
                admin_username,
                action,
                entity_type,
                entity_id,
                status,
                description,
                metadata_json,
                ip_address,
                user_agent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                str(admin_username or "")[:150],
                action[:80],
                str(entity_type or "")[:80],
                str(entity_id or "")[:80],
                str(status or "success")[:30],
                str(description or "")[:255],
                _safe_json(metadata),
                str(ip_address or "")[:64],
                str(user_agent or ""),
            ),
        )

        connection.commit()
        event_id = cursor.lastrowid

        return {
            "success": True,
            "id": event_id,
            "action": action,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def _decode_metadata(value: Any) -> Dict[str, Any]:
    if not value:
        return {}

    if isinstance(value, dict):
        return value

    try:
        return json.loads(str(value))
    except Exception:
        return {}


def get_recent_admin_activity(limit: int = 80) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 80), 200))
    ensure_admin_activity_schema()

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)
        items: List[Dict[str, Any]] = []

        cursor.execute(
            """
            SELECT
                id,
                admin_id,
                admin_username,
                action,
                entity_type,
                entity_id,
                status,
                description,
                metadata_json,
                ip_address,
                user_agent,
                created_at
            FROM admin_activity_events
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

        for row in cursor.fetchall():
            created_at = row.get("created_at")
            items.append(
                {
                    "source": "activity",
                    "id": row.get("id"),
                    "admin_id": row.get("admin_id"),
                    "admin_username": row.get("admin_username") or "",
                    "action": row.get("action") or "",
                    "entity_type": row.get("entity_type") or "",
                    "entity_id": row.get("entity_id") or "",
                    "status": row.get("status") or "",
                    "description": row.get("description") or "",
                    "metadata": _decode_metadata(row.get("metadata_json")),
                    "ip_address": row.get("ip_address") or "",
                    "user_agent": row.get("user_agent") or "",
                    "created_at": _normalize_datetime(created_at),
                    "_sort": created_at or datetime.min,
                }
            )

        if _table_exists(cursor, "admin_login_events"):
            cursor.execute(
                """
                SELECT
                    id,
                    admin_id,
                    event_type,
                    identifier,
                    success,
                    ip_address,
                    user_agent,
                    message,
                    alert_email_sent,
                    alert_error,
                    created_at
                FROM admin_login_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )

            for row in cursor.fetchall():
                created_at = row.get("created_at")
                event_type = row.get("event_type") or "auth_event"
                success = bool(row.get("success"))

                items.append(
                    {
                        "source": "auth",
                        "id": row.get("id"),
                        "admin_id": row.get("admin_id"),
                        "admin_username": row.get("identifier") or "",
                        "action": event_type,
                        "entity_type": "auth",
                        "entity_id": str(row.get("admin_id") or ""),
                        "status": "success" if success else "failed",
                        "description": row.get("message") or event_type,
                        "metadata": {
                            "identifier": row.get("identifier") or "",
                            "alert_email_sent": bool(row.get("alert_email_sent")),
                            "alert_error": row.get("alert_error") or "",
                        },
                        "ip_address": row.get("ip_address") or "",
                        "user_agent": row.get("user_agent") or "",
                        "created_at": _normalize_datetime(created_at),
                        "_sort": created_at or datetime.min,
                    }
                )

        items.sort(key=lambda item: item.get("_sort") or datetime.min, reverse=True)

        normalized = []
        for item in items[:limit]:
            item.pop("_sort", None)
            normalized.append(item)

        return normalized
    finally:
        connection.close()


def get_admin_activity_summary() -> Dict[str, Any]:
    ensure_admin_activity_schema()

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM admin_activity_events")
        total_activity = int((cursor.fetchone() or {}).get("total") or 0)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM admin_activity_events
            WHERE created_at >= (NOW() - INTERVAL 1 DAY)
            """
        )
        activity_24h = int((cursor.fetchone() or {}).get("total") or 0)

        cursor.execute(
            """
            SELECT COUNT(*) AS total
            FROM admin_activity_events
            WHERE entity_type = 'message'
            """
        )
        message_events = int((cursor.fetchone() or {}).get("total") or 0)

        auth_events = 0
        auth_24h = 0

        if _table_exists(cursor, "admin_login_events"):
            cursor.execute("SELECT COUNT(*) AS total FROM admin_login_events")
            auth_events = int((cursor.fetchone() or {}).get("total") or 0)

            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM admin_login_events
                WHERE created_at >= (NOW() - INTERVAL 1 DAY)
                """
            )
            auth_24h = int((cursor.fetchone() or {}).get("total") or 0)

        return {
            "total_events": total_activity + auth_events,
            "events_24h": activity_24h + auth_24h,
            "message_events": message_events,
            "auth_events": auth_events,
        }
    finally:
        connection.close()