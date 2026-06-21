import datetime as _dt
import hashlib as _hashlib
import ipaddress as _ipaddress
import json as _json
import re as _re
from typing import Any, Dict, List, Optional, Tuple

from backend.auth_service import get_connection


_BLOCKED_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "cookie",
    "session",
    "csrf",
    "code",
    "otp",
    "verification_code",
    "reset_token",
    "smtp_password",
    "smtp_app_password",
}


def ensure_activity_logs_table() -> None:
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_activity_logs (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                category VARCHAR(32) NOT NULL DEFAULT 'other',
                event_name VARCHAR(191) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'info',
                severity VARCHAR(32) NOT NULL DEFAULT 'normal',
                summary VARCHAR(500) NULL,
                admin_id INT NULL,
                admin_username VARCHAR(191) NULL,
                admin_email VARCHAR(191) NULL,
                identifier VARCHAR(191) NULL,
                ip_address VARCHAR(64) NULL,
                ip_location VARCHAR(255) NULL,
                network_org VARCHAR(255) NULL,
                device_type VARCHAR(80) NULL,
                browser VARCHAR(120) NULL,
                operating_system VARCHAR(120) NULL,
                request_method VARCHAR(16) NULL,
                request_path VARCHAR(255) NULL,
                user_agent TEXT NULL,
                metadata_json LONGTEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                INDEX idx_activity_category_created (category, created_at),
                INDEX idx_activity_status_created (status, created_at),
                INDEX idx_activity_event_created (event_name, created_at),
                INDEX idx_activity_identifier (identifier),
                INDEX idx_activity_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        connection.commit()
    finally:
        connection.close()


def _now_text() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _trim(value: Any, limit: int = 1200) -> str:
    if value is None:
        return ""

    text = str(value)

    if len(text) > limit:
        return text[:limit] + "... [trimmed]"

    return text


def _is_safe_key(key: str) -> bool:
    lowered = str(key or "").lower()
    return not any(blocked in lowered for blocked in _BLOCKED_KEYS)


def _safe_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}

    for key, value in dict(payload or {}).items():
        key_text = str(key)

        if not _is_safe_key(key_text):
            safe[key_text] = "[redacted]"
            continue

        if isinstance(value, (dict, list, tuple)):
            safe[key_text] = _trim(_json.dumps(value, ensure_ascii=False, default=str), 1600)
        else:
            safe[key_text] = _trim(value, 1600)

    return safe


def _first(payload: Dict[str, Any], keys: List[str], default: str = "") -> str:
    for key in keys:
        value = payload.get(key)

        if value is not None and str(value).strip() != "":
            return str(value).strip()

    return default


def _request_metadata() -> Dict[str, Any]:
    try:
        from flask import request
        path = request.path
    except Exception:
        return {}

    try:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else (request.remote_addr or "")

        return {
            "ip_address": ip_address,
            "method": request.method,
            "path": path,
            "user_agent": request.headers.get("User-Agent", ""),
            "referer": request.headers.get("Referer", ""),
        }
    except Exception:
        return {}


def _parse_user_agent(user_agent: str) -> Dict[str, str]:
    lower = str(user_agent or "").lower()

    device_type = "Desktop"
    browser = "Unknown browser"
    operating_system = "Unknown OS"

    if "windows nt" in lower:
        operating_system = "Windows"
    elif "android" in lower:
        operating_system = "Android"
    elif "iphone" in lower:
        operating_system = "iOS iPhone"
    elif "ipad" in lower:
        operating_system = "iPadOS"
    elif "mac os x" in lower or "macintosh" in lower:
        operating_system = "macOS"
    elif "linux" in lower:
        operating_system = "Linux"

    if "edg/" in lower or "edga/" in lower:
        browser = "Microsoft Edge"
    elif "opr/" in lower or "opera" in lower:
        browser = "Opera"
    elif "firefox/" in lower or "fxios/" in lower:
        browser = "Mozilla Firefox"
    elif "crios/" in lower or "chrome/" in lower:
        browser = "Google Chrome"
    elif "safari/" in lower:
        browser = "Safari"

    if "ipad" in lower or "tablet" in lower:
        device_type = "Tablet"
    elif "mobile" in lower or "android" in lower or "iphone" in lower:
        device_type = "Mobile"

    return {
        "device_type": device_type,
        "browser": browser,
        "operating_system": operating_system,
    }


def _ip_location(ip_address: str) -> Dict[str, str]:
    ip_text = str(ip_address or "").strip()

    if not ip_text:
        return {
            "ip_location": "-",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }

    try:
        parsed = _ipaddress.ip_address(ip_text)

        if parsed.is_loopback:
            return {
                "ip_location": "Localhost device",
                "network_org": "Local machine",
                "timezone": "-",
                "coordinates": "-",
            }

        if parsed.is_private:
            return {
                "ip_location": "Private local network",
                "network_org": "Private LAN or WiFi",
                "timezone": "-",
                "coordinates": "-",
            }

        return {
            "ip_location": "Public IP address. Enable IPINFO_TOKEN for exact location.",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }
    except Exception:
        return {
            "ip_location": "Unknown network",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }


def _infer_category(event_name: str, payload: Dict[str, Any]) -> str:
    text = (str(event_name or "") + " " + _json.dumps(_safe_payload(payload), default=str)).lower()

    security_keywords = [
        "login",
        "logout",
        "otp",
        "verification",
        "auth",
        "session",
        "signin",
        "signout",
        "failed",
        "password",
    ]

    change_keywords = [
        "create",
        "created",
        "update",
        "updated",
        "delete",
        "deleted",
        "upload",
        "uploaded",
        "edit",
        "edited",
        "change",
        "changed",
        "project",
        "media",
        "content",
        "profile",
        "settings",
        "admin_user",
    ]

    contact_keywords = [
        "contact",
        "message",
        "inbox",
        "visitor",
    ]

    if any(keyword in text for keyword in security_keywords):
        return "security"

    if any(keyword in text for keyword in contact_keywords):
        return "contact"

    if any(keyword in text for keyword in change_keywords):
        return "change"

    return "other"


def _infer_status(event_name: str, payload: Dict[str, Any]) -> str:
    text = (str(event_name or "") + " " + str(payload.get("status") or "") + " " + str(payload.get("success") or "")).lower()

    failed_words = ["false", "no", "failed", "fail", "error", "denied", "invalid", "blocked"]
    success_words = ["true", "yes", "success", "sent", "created", "updated", "deleted", "ok"]

    if any(word in text for word in failed_words):
        return "failed"

    if any(word in text for word in success_words):
        return "success"

    return "info"


def _infer_severity(event_name: str, status: str, payload: Dict[str, Any]) -> str:
    text = (str(event_name or "") + " " + str(status or "") + " " + repr(payload or {})).lower()

    if "failed" in text or "invalid" in text or "denied" in text:
        return "high"

    if "delete" in text or "password" in text or "admin_user" in text:
        return "medium"

    return "normal"


def _build_summary(event_name: str, category: str, status: str, payload: Dict[str, Any]) -> str:
    identifier = _first(payload, ["identifier", "username_or_email", "username", "email", "admin_email"], "-")
    path = _first(payload, ["path", "request_path"], "-")
    ip = _first(payload, ["ip_address", "ip", "remote_addr"], "-")

    if category == "security":
        return _trim(f"{event_name} for {identifier}. Status: {status}. IP: {ip}.", 500)

    if category == "contact":
        subject = _first(payload, ["subject", "title"], "New contact message")
        visitor = _first(payload, ["name", "email"], "-")
        return _trim(f"{subject} from {visitor}. IP: {ip}.", 500)

    if category == "change":
        target = _first(payload, ["target", "resource", "table", "model"], "-")
        return _trim(f"{event_name} on {target}. Admin: {identifier}. Path: {path}.", 500)

    return _trim(f"{event_name}. Status: {status}. IP: {ip}.", 500)


def log_activity(
    category: str = "other",
    event_name: str = "admin_activity",
    status: Optional[str] = None,
    severity: Optional[str] = None,
    summary: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ensure_activity_logs_table()

    payload = dict(payload or {})

    request_meta = _request_metadata()
    for key, value in request_meta.items():
        payload.setdefault(key, value)

    event_name = _trim(event_name or _first(payload, ["event", "event_name", "action", "type"], "admin_activity"), 191)
    category = _trim(category or _infer_category(event_name, payload), 32)
    status = _trim(status or _infer_status(event_name, payload), 32)
    severity = _trim(severity or _infer_severity(event_name, status, payload), 32)

    user_agent = _first(payload, ["user_agent", "userAgent"], "")
    ip_address = _first(payload, ["ip_address", "ip", "remote_addr"], "")

    device = _parse_user_agent(user_agent)
    network = _ip_location(ip_address)

    payload.update(device)
    payload.update(network)
    payload.setdefault("time", _now_text())

    admin = payload.get("admin") if isinstance(payload.get("admin"), dict) else {}

    admin_id = payload.get("admin_id") or admin.get("id")
    admin_username = payload.get("admin_username") or payload.get("username") or admin.get("username")
    admin_email = payload.get("admin_email") or payload.get("email") or admin.get("email")
    identifier = _first(
        payload,
        ["identifier", "username_or_email", "username", "admin_username", "email", "admin_email"],
        "",
    )

    request_method = _first(payload, ["method", "request_method"], "")
    request_path = _first(payload, ["path", "request_path"], "")

    safe = _safe_payload(payload)
    metadata_json = _json.dumps(safe, ensure_ascii=False, default=str)

    if not summary:
        summary = _build_summary(event_name, category, status, payload)

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO admin_activity_logs (
                category,
                event_name,
                status,
                severity,
                summary,
                admin_id,
                admin_username,
                admin_email,
                identifier,
                ip_address,
                ip_location,
                network_org,
                device_type,
                browser,
                operating_system,
                request_method,
                request_path,
                user_agent,
                metadata_json
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                category,
                event_name,
                status,
                severity,
                _trim(summary, 500),
                admin_id,
                _trim(admin_username, 191),
                _trim(admin_email, 191),
                _trim(identifier, 191),
                _trim(ip_address, 64),
                _trim(network.get("ip_location", ""), 255),
                _trim(network.get("network_org", ""), 255),
                _trim(device.get("device_type", ""), 80),
                _trim(device.get("browser", ""), 120),
                _trim(device.get("operating_system", ""), 120),
                _trim(request_method, 16),
                _trim(request_path, 255),
                _trim(user_agent, 5000),
                metadata_json,
            ),
        )

        connection.commit()

        return {
            "success": True,
            "id": cursor.lastrowid,
            "category": category,
            "event_name": event_name,
            "status": status,
        }
    finally:
        connection.close()


def _row_to_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(row or {})

    created_at = result.get("created_at")
    if hasattr(created_at, "strftime"):
        result["created_at"] = created_at.strftime("%Y-%m-%d %H:%M:%S")

    metadata_json = result.get("metadata_json")
    if metadata_json:
        try:
            result["metadata"] = _json.loads(metadata_json)
        except Exception:
            result["metadata"] = {}
    else:
        result["metadata"] = {}

    return result


def list_activity_logs(filters: Optional[Dict[str, Any]] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    ensure_activity_logs_table()

    filters = dict(filters or {})
    where: List[str] = []
    params: List[Any] = []

    category = str(filters.get("category") or "").strip().lower()
    status = str(filters.get("status") or "").strip().lower()
    severity = str(filters.get("severity") or "").strip().lower()
    q = str(filters.get("q") or "").strip()

    if category and category != "all":
        where.append("category = %s")
        params.append(category)

    if status and status != "all":
        where.append("status = %s")
        params.append(status)

    if severity and severity != "all":
        where.append("severity = %s")
        params.append(severity)

    if q:
        like = "%" + q + "%"
        where.append(
            """
            (
                event_name LIKE %s
                OR summary LIKE %s
                OR identifier LIKE %s
                OR admin_username LIKE %s
                OR admin_email LIKE %s
                OR ip_address LIKE %s
                OR request_path LIKE %s
            )
            """
        )
        params.extend([like, like, like, like, like, like, like])

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            f"SELECT COUNT(*) AS total FROM admin_activity_logs {where_sql}",
            tuple(params),
        )
        total_row = cursor.fetchone() or {}
        total = int(total_row.get("total") or 0)

        cursor.execute(
            f"""
            SELECT
                id,
                category,
                event_name,
                status,
                severity,
                summary,
                admin_id,
                admin_username,
                admin_email,
                identifier,
                ip_address,
                ip_location,
                network_org,
                device_type,
                browser,
                operating_system,
                request_method,
                request_path,
                user_agent,
                metadata_json,
                created_at
            FROM admin_activity_logs
            {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset]),
        )

        rows = [_row_to_dict(row) for row in cursor.fetchall()]

        return {
            "success": True,
            "data": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    finally:
        connection.close()


def get_activity_log_stats() -> Dict[str, Any]:
    ensure_activity_logs_table()

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM admin_activity_logs")
        total = int((cursor.fetchone() or {}).get("total") or 0)

        cursor.execute(
            """
            SELECT category, COUNT(*) AS total
            FROM admin_activity_logs
            GROUP BY category
            """
        )
        category_counts = {
            str(row.get("category") or "other"): int(row.get("total") or 0)
            for row in cursor.fetchall()
        }

        cursor.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM admin_activity_logs
            GROUP BY status
            """
        )
        status_counts = {
            str(row.get("status") or "info"): int(row.get("total") or 0)
            for row in cursor.fetchall()
        }

        cursor.execute(
            """
            SELECT id, category, event_name, status, summary, created_at
            FROM admin_activity_logs
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
        latest = cursor.fetchone()

        if latest and hasattr(latest.get("created_at"), "strftime"):
            latest["created_at"] = latest["created_at"].strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "total": total,
            "categories": category_counts,
            "statuses": status_counts,
            "latest": latest,
        }
    finally:
        connection.close()


def prune_old_logs(days: int = 180) -> Dict[str, Any]:
    ensure_activity_logs_table()

    days = max(7, int(days or 180))
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM admin_activity_logs
            WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
            """,
            (days,),
        )
        deleted = cursor.rowcount
        connection.commit()

        return {
            "success": True,
            "deleted": deleted,
            "days": days,
        }
    finally:
        connection.close()
