"""
GLAND ADMIN LOGIN ACTIVITY SERVICE
Records admin authentication events for audit and notification.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, Optional

from backend.auth_service import get_connection


def _stringify_datetime(value: Any) -> Any:
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat(sep=" ")
    return value


def normalize_login_event(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None

    return {
        "id": row.get("id"),
        "admin_id": row.get("admin_id"),
        "event_type": row.get("event_type"),
        "identifier": row.get("identifier"),
        "success": bool(row.get("success", 0)),
        "ip_address": row.get("ip_address"),
        "user_agent": row.get("user_agent"),
        "message": row.get("message"),
        "alert_email_sent": bool(row.get("alert_email_sent", 0)),
        "alert_error": row.get("alert_error"),
        "created_at": _stringify_datetime(row.get("created_at")),
    }


def create_login_event(
    *,
    event_type: str,
    identifier: str = "",
    admin_id: Optional[int] = None,
    success: bool = False,
    ip_address: str = "",
    user_agent: str = "",
    message: str = "",
) -> Dict[str, Any]:
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            INSERT INTO admin_login_events (
                admin_id,
                event_type,
                identifier,
                success,
                ip_address,
                user_agent,
                message
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                (event_type or "")[:50],
                (identifier or "")[:150],
                1 if success else 0,
                (ip_address or "")[:64],
                user_agent or "",
                (message or "")[:255],
            ),
        )

        event_id = cursor.lastrowid
        connection.commit()

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
            WHERE id = %s
            LIMIT 1
            """,
            (event_id,),
        )

        return normalize_login_event(cursor.fetchone()) or {}

    finally:
        connection.close()


def update_login_event_alert_status(
    event_id: int,
    *,
    sent: bool,
    error: str = "",
) -> bool:
    if not event_id:
        return False

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE admin_login_events
            SET
                alert_email_sent = %s,
                alert_error = %s
            WHERE id = %s
            """,
            (
                1 if sent else 0,
                (error or "")[:500] if error else None,
                event_id,
            ),
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()


def get_latest_login_events(limit: int = 25):
    safe_limit = max(1, min(int(limit or 25), 100))

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            f"""
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
            ORDER BY id DESC
            LIMIT {safe_limit}
            """
        )

        return [
            normalize_login_event(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()