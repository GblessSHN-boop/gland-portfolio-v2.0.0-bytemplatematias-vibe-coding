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

# GLAND ANALYTICS SUMMARY SAFE FALLBACK START

from datetime import date as _gland_date, datetime as _gland_datetime
from decimal import Decimal as _gland_Decimal


def _gland_make_json_safe(value):
    if isinstance(value, _gland_Decimal):
        try:
            if value == value.to_integral_value():
                return int(value)
        except Exception:
            pass
        return float(value)

    if isinstance(value, (_gland_datetime, _gland_date)):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(key): _gland_make_json_safe(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_gland_make_json_safe(item) for item in value]

    return value


def _gland_config_value(name, default=None):
    try:
        import config as _gland_config
        return getattr(_gland_config, name, default)
    except Exception:
        return default


def _gland_open_connection():
    import mysql.connector

    return mysql.connector.connect(
        host=_gland_config_value("DB_HOST", "localhost"),
        port=int(_gland_config_value("DB_PORT", 3306)),
        user=_gland_config_value("DB_USER", "root"),
        password=_gland_config_value("DB_PASSWORD", ""),
        database=_gland_config_value("DB_NAME", "gland_portfolio_db"),
    )


def _gland_fetch_one(cursor, query, params=None):
    cursor.execute(query, params or ())
    row = cursor.fetchone()
    return row or {}


def _gland_fetch_all(cursor, query, params=None):
    cursor.execute(query, params or ())
    return cursor.fetchall() or []


def _gland_table_exists(cursor, table_name):
    row = _gland_fetch_one(
        cursor,
        "SELECT COUNT(*) AS total FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s",
        (table_name,),
    )
    return int(row.get("total") or 0) > 0


def _gland_column_exists(cursor, table_name, column_name):
    row = _gland_fetch_one(
        cursor,
        "SELECT COUNT(*) AS total FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
        (table_name, column_name),
    )
    return int(row.get("total") or 0) > 0


def _gland_first_existing_table(cursor, table_names):
    for table_name in table_names:
        if _gland_table_exists(cursor, table_name):
            return table_name
    return None


def _gland_count_table(cursor, table_name):
    if not table_name or not _gland_table_exists(cursor, table_name):
        return 0

    row = _gland_fetch_one(cursor, f"SELECT COUNT(*) AS total FROM {table_name}")
    return int(row.get("total") or 0)


def _gland_count_distinct(cursor, table_name, column_name):
    if not table_name or not _gland_table_exists(cursor, table_name):
        return 0

    if not _gland_column_exists(cursor, table_name, column_name):
        return 0

    row = _gland_fetch_one(cursor, f"SELECT COUNT(DISTINCT {column_name}) AS total FROM {table_name}")
    return int(row.get("total") or 0)


def _gland_count_equals(cursor, table_name, column_name, value):
    if not table_name or not _gland_table_exists(cursor, table_name):
        return 0

    if not _gland_column_exists(cursor, table_name, column_name):
        return 0

    row = _gland_fetch_one(
        cursor,
        f"SELECT COUNT(*) AS total FROM {table_name} WHERE {column_name} = %s",
        (value,),
    )
    return int(row.get("total") or 0)


def _gland_count_event(cursor, event_value):
    table_name = "analytics_events"

    if not _gland_table_exists(cursor, table_name):
        return 0

    for column_name in ("event_type", "event_name", "name", "type"):
        if _gland_column_exists(cursor, table_name, column_name):
            return _gland_count_equals(cursor, table_name, column_name, event_value)

    return 0


def _gland_average_duration(cursor):
    table_name = "analytics_visits"

    if not _gland_table_exists(cursor, table_name):
        return 0

    if not _gland_column_exists(cursor, table_name, "duration_seconds"):
        return 0

    row = _gland_fetch_one(
        cursor,
        "SELECT AVG(duration_seconds) AS average_duration FROM analytics_visits WHERE duration_seconds IS NOT NULL",
    )

    value = row.get("average_duration")

    if value is None:
        return 0

    return round(float(value), 2)


def _gland_top_pages(cursor):
    table_name = "analytics_visits"

    if not _gland_table_exists(cursor, table_name):
        return []

    if not _gland_column_exists(cursor, table_name, "page_path"):
        return []

    rows = _gland_fetch_all(
        cursor,
        """
        SELECT page_path, COUNT(*) AS views
        FROM analytics_visits
        WHERE page_path IS NOT NULL AND page_path <> ''
        GROUP BY page_path
        ORDER BY views DESC
        LIMIT 5
        """,
    )

    return [
        {
            "page_path": row.get("page_path") or "",
            "views": int(row.get("views") or 0),
            "total": int(row.get("views") or 0),
        }
        for row in rows
    ]


def _gland_top_events(cursor):
    table_name = "analytics_events"

    if not _gland_table_exists(cursor, table_name):
        return []

    event_column = None

    for column_name in ("event_type", "event_name", "name", "type"):
        if _gland_column_exists(cursor, table_name, column_name):
            event_column = column_name
            break

    if not event_column:
        return []

    rows = _gland_fetch_all(
        cursor,
        f"""
        SELECT {event_column} AS event_type, COUNT(*) AS total
        FROM analytics_events
        WHERE {event_column} IS NOT NULL AND {event_column} <> ''
        GROUP BY {event_column}
        ORDER BY total DESC
        LIMIT 5
        """,
    )

    return [
        {
            "event_type": row.get("event_type") or "",
            "event_name": row.get("event_type") or "",
            "total": int(row.get("total") or 0),
            "count": int(row.get("total") or 0),
        }
        for row in rows
    ]


def _gland_build_summary_fallback(reason=""):
    connection = None

    try:
        connection = _gland_open_connection()
        cursor = connection.cursor(dictionary=True)

        visits = _gland_count_table(cursor, "analytics_visits")
        unique_visitors = _gland_count_distinct(cursor, "analytics_visits", "visitor_id")
        events = _gland_count_table(cursor, "analytics_events")

        messages_table = _gland_first_existing_table(cursor, ("messages", "contact_messages"))
        messages = _gland_count_table(cursor, messages_table)

        new_messages = 0
        approved_messages = 0

        if messages_table:
            for status_column in ("status", "message_status"):
                if _gland_column_exists(cursor, messages_table, status_column):
                    new_messages = (
                        _gland_count_equals(cursor, messages_table, status_column, "new")
                        + _gland_count_equals(cursor, messages_table, status_column, "unread")
                        + _gland_count_equals(cursor, messages_table, status_column, "pending")
                    )
                    approved_messages = _gland_count_equals(cursor, messages_table, status_column, "approved")
                    break

        projects = _gland_count_table(cursor, "projects")
        media_files = _gland_count_table(cursor, "media_files")
        social_clicks = _gland_count_event(cursor, "social_click")
        intro_video_views = _gland_count_event(cursor, "intro_video_view")
        average_duration = _gland_average_duration(cursor)
        top_pages = _gland_top_pages(cursor)
        top_events = _gland_top_events(cursor)

        return {
            "visits": visits,
            "total_visits": visits,
            "unique_visitors": unique_visitors,
            "events": events,
            "total_events": events,
            "messages": messages,
            "total_messages": messages,
            "new_messages": new_messages,
            "approved_messages": approved_messages,
            "projects": projects,
            "total_projects": projects,
            "media_files": media_files,
            "total_media_files": media_files,
            "social_clicks": social_clicks,
            "intro_video_views": intro_video_views,
            "average_duration": average_duration,
            "average_duration_seconds": average_duration,
            "avg_duration_seconds": average_duration,
            "top_pages": top_pages,
            "top_events": top_events,
            "summary_source": "fallback",
            "summary_fallback_reason": reason,
        }

    except Exception as fallback_error:
        return {
            "visits": 0,
            "total_visits": 0,
            "unique_visitors": 0,
            "events": 0,
            "total_events": 0,
            "messages": 0,
            "total_messages": 0,
            "new_messages": 0,
            "approved_messages": 0,
            "projects": 0,
            "total_projects": 0,
            "media_files": 0,
            "total_media_files": 0,
            "social_clicks": 0,
            "intro_video_views": 0,
            "average_duration": 0,
            "average_duration_seconds": 0,
            "avg_duration_seconds": 0,
            "top_pages": [],
            "top_events": [],
            "summary_source": "fallback_empty",
            "summary_fallback_reason": reason,
            "summary_error": str(fallback_error),
        }

    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

_gland_original_get_analytics_summary = get_analytics_summary
def get_analytics_summary(*args, **kwargs):
    try:
        return _gland_make_json_safe(_gland_original_get_analytics_summary(*args, **kwargs))
    except Exception as exc:
        return _gland_make_json_safe(_gland_build_summary_fallback(str(exc)))

# GLAND ANALYTICS SUMMARY SAFE FALLBACK END
