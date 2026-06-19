from datetime import datetime
import json

from backend.db import get_connection


def normalize_datetime(row):
    if not row:
        return None

    for key, value in list(row.items()):
        if isinstance(value, datetime):
            row[key] = value.isoformat(sep=" ")

    return row


def clean_text(value, default=""):
    return str(value if value is not None else default).strip()


def to_int(value, default=0):
    try:
        if value is None or value == "":
            return default

        return int(value)
    except (TypeError, ValueError):
        return default


def safe_json(value):
    if value is None:
        return "{}"

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            return json.dumps({"value": value}, ensure_ascii=False)

    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return json.dumps({"value": str(value)}, ensure_ascii=False)


def record_visit(data, ip_address=""):
    payload = {
        "visitor_id": clean_text(data.get("visitor_id"), "anonymous"),
        "session_id": clean_text(data.get("session_id"), ""),
        "ip_address": clean_text(ip_address),
        "user_agent": clean_text(data.get("user_agent")),
        "page_path": clean_text(data.get("page_path"), "/"),
        "referrer": clean_text(data.get("referrer")),
        "device_type": clean_text(data.get("device_type"), "unknown"),
        "browser_name": clean_text(data.get("browser_name"), "unknown"),
        "duration_seconds": to_int(data.get("duration_seconds"), 0),
    }

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO analytics_visits (
                visitor_id, session_id, ip_address, user_agent, page_path,
                referrer, device_type, browser_name, duration_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["visitor_id"],
                payload["session_id"],
                payload["ip_address"],
                payload["user_agent"],
                payload["page_path"],
                payload["referrer"],
                payload["device_type"],
                payload["browser_name"],
                payload["duration_seconds"],
            ),
        )

        connection.commit()

        return get_visit_by_id(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_visit_by_id(visit_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, visitor_id, session_id, ip_address, user_agent, page_path,
                   referrer, device_type, browser_name, duration_seconds, created_at
            FROM analytics_visits
            WHERE id = %s
            LIMIT 1
            """,
            (visit_id,),
        )

        return normalize_datetime(cursor.fetchone())
    finally:
        cursor.close()
        connection.close()


def record_event(data, ip_address=""):
    metadata_json = safe_json(data.get("metadata"))

    payload = {
        "visitor_id": clean_text(data.get("visitor_id"), "anonymous"),
        "session_id": clean_text(data.get("session_id"), ""),
        "event_type": clean_text(data.get("event_type"), "custom"),
        "event_name": clean_text(data.get("event_name"), "event"),
        "event_value": clean_text(data.get("event_value")),
        "page_path": clean_text(data.get("page_path"), "/"),
        "target_url": clean_text(data.get("target_url")),
        "metadata_json": metadata_json,
        "ip_address": clean_text(ip_address),
    }

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO analytics_events (
                visitor_id, session_id, event_type, event_name, event_value,
                page_path, target_url, metadata_json, ip_address
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["visitor_id"],
                payload["session_id"],
                payload["event_type"],
                payload["event_name"],
                payload["event_value"],
                payload["page_path"],
                payload["target_url"],
                payload["metadata_json"],
                payload["ip_address"],
            ),
        )

        connection.commit()

        return get_event_by_id(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_event_by_id(event_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, visitor_id, session_id, event_type, event_name, event_value,
                   page_path, target_url, metadata_json, ip_address, created_at
            FROM analytics_events
            WHERE id = %s
            LIMIT 1
            """,
            (event_id,),
        )

        row = normalize_datetime(cursor.fetchone())

        if row and row.get("metadata_json"):
            try:
                row["metadata"] = json.loads(row["metadata_json"])
            except json.JSONDecodeError:
                row["metadata"] = {}

        return row
    finally:
        cursor.close()
        connection.close()


def list_recent_events(limit=100):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, visitor_id, session_id, event_type, event_name, event_value,
                   page_path, target_url, metadata_json, ip_address, created_at
            FROM analytics_events
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

        rows = cursor.fetchall()

        return [normalize_datetime(row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def fetch_one_value(cursor, query, params=None, default=0):
    cursor.execute(query, params or ())
    row = cursor.fetchone()

    if not row:
        return default

    value = list(row.values())[0]

    return value if value is not None else default


def fetch_group_rows(cursor, query, params=None):
    cursor.execute(query, params or ())
    return [normalize_datetime(row) for row in cursor.fetchall()]


def get_analytics_summary():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        total_visits = fetch_one_value(cursor, "SELECT COUNT(*) AS count_value FROM analytics_visits")
        unique_visitors = fetch_one_value(
            cursor,
            """
            SELECT COUNT(DISTINCT visitor_id) AS count_value
            FROM analytics_visits
            WHERE visitor_id IS NOT NULL AND visitor_id <> ''
            """,
        )
        total_events = fetch_one_value(cursor, "SELECT COUNT(*) AS count_value FROM analytics_events")
        total_messages = fetch_one_value(cursor, "SELECT COUNT(*) AS count_value FROM messages")
        new_messages = fetch_one_value(
            cursor,
            "SELECT COUNT(*) AS count_value FROM messages WHERE status = 'new'",
        )
        approved_messages = fetch_one_value(
            cursor,
            "SELECT COUNT(*) AS count_value FROM messages WHERE status = 'approved'",
        )
        total_projects = fetch_one_value(cursor, "SELECT COUNT(*) AS count_value FROM projects")
        total_media = fetch_one_value(cursor, "SELECT COUNT(*) AS count_value FROM media_files")
        avg_duration_seconds = fetch_one_value(
            cursor,
            """
            SELECT COALESCE(ROUND(AVG(duration_seconds)), 0) AS count_value
            FROM analytics_visits
            WHERE duration_seconds > 0
            """,
        )
        social_clicks = fetch_one_value(
            cursor,
            """
            SELECT COUNT(*) AS count_value
            FROM analytics_events
            WHERE event_type = 'social_click'
            """,
        )
        intro_video_views = fetch_one_value(
            cursor,
            """
            SELECT COUNT(*) AS count_value
            FROM analytics_events
            WHERE event_type = 'intro_video_view'
               OR event_name = 'intro_video'
            """,
        )

        top_pages = fetch_group_rows(
            cursor,
            """
            SELECT page_path, COUNT(*) AS total
            FROM analytics_visits
            GROUP BY page_path
            ORDER BY total DESC, page_path ASC
            LIMIT 10
            """,
        )

        top_events = fetch_group_rows(
            cursor,
            """
            SELECT event_type, event_name, COUNT(*) AS total
            FROM analytics_events
            GROUP BY event_type, event_name
            ORDER BY total DESC, event_type ASC
            LIMIT 10
            """,
        )

        latest_events = list_recent_events(limit=10)

        return {
            "totals": {
                "visits": total_visits,
                "unique_visitors": unique_visitors,
                "events": total_events,
                "messages": total_messages,
                "new_messages": new_messages,
                "approved_messages": approved_messages,
                "projects": total_projects,
                "media_files": total_media,
                "social_clicks": social_clicks,
                "intro_video_views": intro_video_views,
                "avg_duration_seconds": avg_duration_seconds,
            },
            "top_pages": top_pages,
            "top_events": top_events,
            "latest_events": latest_events,
        }
    finally:
        cursor.close()
        connection.close()