"""
GLAND ADMIN AUTH SERVICE
Local admin authentication helpers for the portfolio CMS.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional

import mysql.connector

try:
    import config
except Exception as exc:  # pragma: no cover
    raise RuntimeError(f"Unable to import config.py: {exc}") from exc


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000
SESSION_HOURS = 12


def get_connection():
    return mysql.connector.connect(
        host=getattr(config, "DB_HOST", "localhost"),
        port=int(getattr(config, "DB_PORT", 3306)),
        user=getattr(config, "DB_USER", "root"),
        password=getattr(config, "DB_PASSWORD", ""),
        database=getattr(config, "DB_NAME", "gland_portfolio_db"),
    )


def _stringify_datetime(value: Any) -> Any:
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat(sep=" ")
    return value


def safe_admin(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None

    return {
        "id": row.get("id"),
        "username": row.get("username"),
        "email": row.get("email"),
        "role": row.get("role"),
        "is_active": bool(row.get("is_active", 0)),
        "created_at": _stringify_datetime(row.get("created_at")),
        "updated_at": _stringify_datetime(row.get("updated_at")),
    }


def hash_password(password: str, *, salt: Optional[str] = None, iterations: int = PASSWORD_ITERATIONS) -> str:
    if not password:
        raise ValueError("Password must not be empty.")

    salt = salt or secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()

    return f"{PASSWORD_ALGORITHM}${int(iterations)}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False

    try:
        algorithm, iterations_raw, salt, expected_digest = stored_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != PASSWORD_ALGORITHM:
        return False

    try:
        iterations = int(iterations_raw)
    except ValueError:
        return False

    actual_hash = hash_password(password, salt=salt, iterations=iterations)
    return hmac.compare_digest(actual_hash, stored_hash)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_admin(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    identifier = (identifier or "").strip()

    if not identifier or not password:
        return None

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, username, email, password_hash, role, is_active, created_at, updated_at
            FROM admin_users
            WHERE (username = %s OR email = %s)
              AND is_active = 1
            LIMIT 1
            """,
            (identifier, identifier),
        )

        row = cursor.fetchone()

        if not row:
            return None

        if not verify_password(password, row.get("password_hash") or ""):
            return None

        return safe_admin(row)

    finally:
        connection.close()


def create_admin_session(admin_id: int, *, ip_address: str = "", user_agent: str = "") -> Dict[str, Any]:
    token = secrets.token_urlsafe(48)
    token_hash = _hash_token(token)
    expires_at = _dt.datetime.utcnow() + _dt.timedelta(hours=SESSION_HOURS)

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            DELETE FROM admin_sessions
            WHERE expires_at <= UTC_TIMESTAMP()
            """
        )

        cursor.execute(
            """
            INSERT INTO admin_sessions (
                admin_id,
                token_hash,
                expires_at,
                ip_address,
                user_agent
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                token_hash,
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                (ip_address or "")[:64],
                user_agent or "",
            ),
        )

        try:
            cursor.execute(
                """
                UPDATE admin_users
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (admin_id,),
            )
        except Exception:
            pass

        connection.commit()

        return {
            "token": token,
            "expires_at": expires_at.isoformat(sep=" "),
            "max_age_seconds": SESSION_HOURS * 60 * 60,
        }

    finally:
        connection.close()


def get_admin_by_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None

    token_hash = _hash_token(token)
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                admin_users.id,
                admin_users.username,
                admin_users.email,
                admin_users.role,
                admin_users.is_active,
                admin_users.created_at,
                admin_users.updated_at
            FROM admin_sessions
            INNER JOIN admin_users
                ON admin_users.id = admin_sessions.admin_id
            WHERE admin_sessions.token_hash = %s
              AND admin_sessions.expires_at > UTC_TIMESTAMP()
              AND admin_users.is_active = 1
            LIMIT 1
            """,
            (token_hash,),
        )

        row = cursor.fetchone()

        if not row:
            return None

        cursor.execute(
            """
            UPDATE admin_sessions
            SET last_seen_at = CURRENT_TIMESTAMP
            WHERE token_hash = %s
            """,
            (token_hash,),
        )

        connection.commit()

        return safe_admin(row)

    finally:
        connection.close()


def delete_admin_session(token: str) -> bool:
    if not token:
        return False

    token_hash = _hash_token(token)
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM admin_sessions
            WHERE token_hash = %s
            """,
            (token_hash,),
        )

        connection.commit()
        return cursor.rowcount > 0

    finally:
        connection.close()