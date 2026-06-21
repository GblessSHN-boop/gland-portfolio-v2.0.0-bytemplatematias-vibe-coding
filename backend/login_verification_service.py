from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import secrets
from typing import Any, Dict, Optional

try:
    import config
except Exception:
    config = None

from backend.auth_service import get_connection, safe_admin
from backend.notification_service import send_admin_login_verification_email


def _get_config(name: str, default=None):
    if config is None:
        return default
    return getattr(config, name, default)


def _hash_value(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _now() -> _dt.datetime:
    return _dt.datetime.now()


def _code_minutes() -> int:
    return max(1, min(int(_get_config("LOGIN_VERIFICATION_CODE_MINUTES", 10) or 10), 60))


def _max_attempts() -> int:
    return max(1, min(int(_get_config("LOGIN_VERIFICATION_MAX_ATTEMPTS", 5) or 5), 10))


def _debug_return_code(email_result: Optional[Dict[str, Any]] = None) -> bool:
    if bool(_get_config("LOGIN_VERIFICATION_DEBUG_RETURN_CODE", False)):
        return True

    # Safety net: show debug code only if email failed, so local admin is not locked out.
    if email_result and not bool(email_result.get("sent")):
        return True

    return False

    if bool(_get_config("APP_DEBUG", False)):
        return True

    # Local safety net: kalau SMTP belum beres, jangan kunci admin dari dashboard sendiri.
    if email_result and not bool(email_result.get("sent")):
        return True

    return False


def _mask_email(email: str) -> str:
    email = str(email or "").strip()

    if "@" not in email:
        return email or "-"

    name, domain = email.split("@", 1)

    if len(name) <= 2:
        masked_name = name[0:1] + "***"
    else:
        masked_name = name[0:2] + "***" + name[-1:]

    return masked_name + "@" + domain


def ensure_login_verification_schema() -> Dict[str, Any]:
    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_login_verification_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                admin_id INT NOT NULL,
                challenge_token_hash VARCHAR(128) NOT NULL UNIQUE,
                code_hash VARCHAR(128) NOT NULL,
                identifier VARCHAR(150) DEFAULT NULL,
                expires_at DATETIME NOT NULL,
                used_at DATETIME DEFAULT NULL,
                attempt_count INT NOT NULL DEFAULT 0,
                max_attempts INT NOT NULL DEFAULT 5,
                requested_ip VARCHAR(64) DEFAULT NULL,
                requested_user_agent TEXT DEFAULT NULL,
                email_sent TINYINT(1) DEFAULT 0,
                email_error TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_admin_login_verification_admin_id (admin_id),
                INDEX idx_admin_login_verification_token_hash (challenge_token_hash),
                INDEX idx_admin_login_verification_expires_at (expires_at),
                INDEX idx_admin_login_verification_used_at (used_at),
                CONSTRAINT fk_admin_login_verification_admin_id
                    FOREIGN KEY (admin_id)
                    REFERENCES admin_users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            DELETE FROM admin_login_verification_codes
            WHERE expires_at <= NOW()
               OR used_at IS NOT NULL
            """
        )

        connection.commit()

        cursor.execute("SELECT COUNT(*) AS total FROM admin_login_verification_codes")
        row = cursor.fetchone() or {"total": 0}

        return {
            "success": True,
            "table": "admin_login_verification_codes",
            "active_code_count": int(row.get("total") or 0),
        }
    finally:
        connection.close()


def create_login_verification_challenge(
    admin: Dict[str, Any],
    *,
    identifier: str = "",
    ip_address: str = "",
    user_agent: str = "",
) -> Dict[str, Any]:
    ensure_login_verification_schema()

    admin_id = int(admin.get("id") or 0)
    if admin_id <= 0:
        return {
            "success": False,
            "message": "Invalid admin account.",
            "status_code": 400,
        }

    code = f"{secrets.randbelow(1000000):06d}"
    challenge_token = secrets.token_urlsafe(32)
    code_hash = _hash_value(code)
    challenge_hash = _hash_value(challenge_token)
    expires_at = _now() + _dt.timedelta(minutes=_code_minutes())

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            DELETE FROM admin_login_verification_codes
            WHERE admin_id = %s
              AND (expires_at <= NOW() OR used_at IS NOT NULL)
            """,
            (admin_id,),
        )

        email_result = send_admin_login_verification_email(
            {
                "admin": admin,
                "code": code,
                "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )

        cursor.execute(
            """
            INSERT INTO admin_login_verification_codes (
                admin_id,
                challenge_token_hash,
                code_hash,
                identifier,
                expires_at,
                max_attempts,
                requested_ip,
                requested_user_agent,
                email_sent,
                email_error
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                challenge_hash,
                code_hash,
                str(identifier or "")[:150],
                expires_at.strftime("%Y-%m-%d %H:%M:%S"),
                _max_attempts(),
                str(ip_address or "")[:64],
                str(user_agent or ""),
                1 if email_result.get("sent") else 0,
                str(email_result.get("error") or "")[:500] if email_result.get("error") else None,
            ),
        )

        connection.commit()

        response = {
            "success": True,
            "message": "Verification code generated.",
            "challenge_token": challenge_token,
            "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            "email_sent": bool(email_result.get("sent")),
            "email_skipped": bool(email_result.get("skipped")),
            "email_error": str(email_result.get("error") or ""),
            "masked_email": _mask_email(str(admin.get("email") or "")),
        }

        if _debug_return_code(email_result):
            response["debug_code"] = code

        return response

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def verify_login_verification_challenge(
    challenge_token: str,
    code: str,
) -> Dict[str, Any]:
    ensure_login_verification_schema()

    challenge_token = str(challenge_token or "").strip()
    code = str(code or "").strip()

    if not challenge_token or not code:
        return {
            "success": False,
            "message": "Verification token and code are required.",
            "status_code": 400,
        }

    if not code.isdigit() or len(code) != 6:
        return {
            "success": False,
            "message": "Verification code must be 6 digits.",
            "status_code": 400,
        }

    challenge_hash = _hash_value(challenge_token)
    code_hash = _hash_value(code)

    connection = get_connection()

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                admin_login_verification_codes.id AS verification_id,
                admin_login_verification_codes.admin_id,
                admin_login_verification_codes.code_hash,
                admin_login_verification_codes.identifier,
                admin_login_verification_codes.attempt_count,
                admin_login_verification_codes.max_attempts,
                admin_login_verification_codes.expires_at,
                admin_users.id,
                admin_users.username,
                admin_users.email,
                admin_users.role,
                admin_users.is_active,
                admin_users.created_at,
                admin_users.updated_at
            FROM admin_login_verification_codes
            INNER JOIN admin_users
                ON admin_users.id = admin_login_verification_codes.admin_id
            WHERE admin_login_verification_codes.challenge_token_hash = %s
              AND admin_login_verification_codes.used_at IS NULL
              AND admin_login_verification_codes.expires_at > NOW()
              AND admin_users.is_active = 1
            LIMIT 1
            """,
            (challenge_hash,),
        )

        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "Verification code is invalid or expired.",
                "status_code": 400,
            }

        verification_id = int(row.get("verification_id") or 0)
        attempt_count = int(row.get("attempt_count") or 0)
        max_attempts = int(row.get("max_attempts") or _max_attempts())

        if attempt_count >= max_attempts:
            return {
                "success": False,
                "message": "Too many verification attempts. Please login again.",
                "status_code": 429,
                "identifier": row.get("identifier") or "",
            }

        stored_code_hash = str(row.get("code_hash") or "")
        is_valid = hmac.compare_digest(stored_code_hash, code_hash)

        if not is_valid:
            cursor.execute(
                """
                UPDATE admin_login_verification_codes
                SET attempt_count = attempt_count + 1
                WHERE id = %s
                """,
                (verification_id,),
            )
            connection.commit()

            return {
                "success": False,
                "message": "Invalid verification code.",
                "status_code": 401,
                "identifier": row.get("identifier") or "",
            }

        cursor.execute(
            """
            UPDATE admin_login_verification_codes
            SET used_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (verification_id,),
        )

        cursor.execute(
            """
            DELETE FROM admin_login_verification_codes
            WHERE admin_id = %s
              AND used_at IS NULL
              AND id <> %s
            """,
            (row.get("admin_id"), verification_id),
        )

        connection.commit()

        return {
            "success": True,
            "message": "Verification successful.",
            "status_code": 200,
            "admin": safe_admin(row),
            "identifier": row.get("identifier") or row.get("username") or row.get("email") or "",
        }

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()