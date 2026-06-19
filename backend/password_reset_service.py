from __future__ import annotations

import datetime as _dt
import hashlib
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

try:
    import config
except Exception:
    config = None

from backend.auth_service import get_connection, hash_password, safe_admin
from backend.branded_mailer import send_admin_password_reset_email


def _get_config(name: str, default=None):
    if config is None:
        return default
    return getattr(config, name, default)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> _dt.datetime:
    return _dt.datetime.now()


def _token_minutes() -> int:
    return int(_get_config("PASSWORD_RESET_TOKEN_MINUTES", 30) or 30)


def _cooldown_seconds() -> int:
    return int(_get_config("PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS", 90) or 90)


def _debug_return_token() -> bool:
    return bool(_get_config("PASSWORD_RESET_DEBUG_RETURN_TOKEN", bool(_get_config("APP_DEBUG", False))))


def _base_url(base_url: str = "") -> str:
    configured = str(_get_config("PASSWORD_RESET_BASE_URL", "") or "").strip()
    value = (base_url or configured or "http://127.0.0.1:8000").strip()
    return value.rstrip("/")


def _build_reset_url(token: str, base_url: str = "") -> str:
    query = urlencode({"token": token})
    return f"{_base_url(base_url)}/admin/reset-password.html?{query}"


def _find_active_admin(identifier: str) -> Optional[Dict[str, Any]]:
    identifier = (identifier or "").strip()

    if not identifier:
        return None

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                role,
                is_active,
                created_at,
                updated_at
            FROM admin_users
            WHERE (username = %s OR email = %s)
              AND is_active = 1
            LIMIT 1
            """,
            (identifier, identifier),
        )
        return cursor.fetchone()
    finally:
        connection.close()


def _get_retry_after_seconds(admin_id: int) -> int:
    cooldown = _cooldown_seconds()
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                TIMESTAMPDIFF(SECOND, created_at, NOW()) AS elapsed_seconds
            FROM admin_password_reset_tokens
            WHERE admin_id = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (admin_id,),
        )
        row = cursor.fetchone()

        if not row or row.get("elapsed_seconds") is None:
            return 0

        elapsed = int(row["elapsed_seconds"] or 0)
        retry_after = cooldown - elapsed
        return retry_after if retry_after > 0 else 0
    finally:
        connection.close()


def request_admin_password_reset(
    identifier: str,
    *,
    base_url: str = "",
    ip_address: str = "",
    user_agent: str = "",
) -> Dict[str, Any]:
    identifier = (identifier or "").strip()

    generic_response: Dict[str, Any] = {
        "success": True,
        "status_code": 200,
        "message": "If the admin account exists, a password reset email has been sent.",
        "email_sent": False,
        "email_skipped": True,
        "debug_reset_url": None,
        "retry_after_seconds": 0,
        "cooldown_seconds": _cooldown_seconds(),
    }

    admin = _find_active_admin(identifier)

    if not admin:
        return generic_response

    retry_after_seconds = _get_retry_after_seconds(int(admin["id"]))

    if retry_after_seconds > 0:
        return {
            "success": False,
            "status_code": 429,
            "message": f"Please wait {retry_after_seconds} seconds before requesting another reset email.",
            "email_sent": False,
            "email_skipped": True,
            "debug_reset_url": None,
            "retry_after_seconds": retry_after_seconds,
            "cooldown_seconds": _cooldown_seconds(),
        }

    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = _now() + _dt.timedelta(minutes=_token_minutes())
    reset_url = _build_reset_url(token, base_url=base_url)

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            DELETE FROM admin_password_reset_tokens
            WHERE expires_at <= NOW()
               OR used_at IS NOT NULL
            """
        )

        cursor.execute(
            """
            INSERT INTO admin_password_reset_tokens (
                admin_id,
                token_hash,
                expires_at,
                requested_ip,
                requested_user_agent
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                admin["id"],
                token_hash,
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                (ip_address or "")[:64],
                user_agent or "",
            ),
        )

        reset_id = cursor.lastrowid
        connection.commit()

    finally:
        connection.close()

    email_result = send_admin_password_reset_email(
        {
            "admin": safe_admin(admin),
            "reset_url": reset_url,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": ip_address,
            "user_agent": user_agent,
        }
    )

    try:
        connection = get_connection()

        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE admin_password_reset_tokens
                SET
                    email_sent = %s,
                    email_error = %s
                WHERE id = %s
                """,
                (
                    1 if email_result.get("sent") else 0,
                    (email_result.get("error") or "")[:500] if email_result.get("error") else None,
                    reset_id,
                ),
            )
            connection.commit()
        finally:
            connection.close()
    except Exception:
        pass

    return {
        "success": True,
        "status_code": 200,
        "message": "If the admin account exists, a password reset email has been sent.",
        "email_sent": bool(email_result.get("sent")),
        "email_skipped": bool(email_result.get("skipped")),
        "debug_reset_url": reset_url if _debug_return_token() else None,
        "retry_after_seconds": 0,
        "cooldown_seconds": _cooldown_seconds(),
    }


def reset_admin_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
    token = (token or "").strip()
    new_password = new_password or ""

    if not token:
        return {
            "success": False,
            "message": "Reset token is required.",
            "status_code": 400,
        }

    if len(new_password) < 10:
        return {
            "success": False,
            "message": "New password must be at least 10 characters.",
            "status_code": 400,
        }

    token_hash = _hash_token(token)
    password_hash = hash_password(new_password)

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                admin_password_reset_tokens.id AS reset_id,
                admin_password_reset_tokens.admin_id,
                admin_users.id,
                admin_users.username,
                admin_users.email,
                admin_users.role,
                admin_users.is_active,
                admin_users.created_at,
                admin_users.updated_at
            FROM admin_password_reset_tokens
            INNER JOIN admin_users
                ON admin_users.id = admin_password_reset_tokens.admin_id
            WHERE admin_password_reset_tokens.token_hash = %s
              AND admin_password_reset_tokens.expires_at > NOW()
              AND admin_password_reset_tokens.used_at IS NULL
              AND admin_users.is_active = 1
            LIMIT 1
            """,
            (token_hash,),
        )

        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "Reset token is invalid or expired.",
                "status_code": 400,
            }

        admin_id = row["admin_id"]
        reset_id = row["reset_id"]

        cursor.execute(
            """
            UPDATE admin_users
            SET
                password_hash = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (password_hash, admin_id),
        )

        cursor.execute(
            """
            UPDATE admin_password_reset_tokens
            SET used_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (reset_id,),
        )

        cursor.execute(
            """
            DELETE FROM admin_sessions
            WHERE admin_id = %s
            """,
            (admin_id,),
        )

        connection.commit()

        return {
            "success": True,
            "message": "Password has been reset. Please login with the new password.",
            "status_code": 200,
            "admin": safe_admin(row),
        }

    finally:
        connection.close()