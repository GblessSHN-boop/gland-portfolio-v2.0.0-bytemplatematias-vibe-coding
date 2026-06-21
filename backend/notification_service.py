"""
GLAND NOTIFICATION SERVICE
Optional email alerts for admin authentication activity.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any, Dict

try:
    import config
except Exception:
    config = None


def _get_config(name: str, default=None):
    if config is None:
        return default

    return getattr(config, name, default)


def is_email_alert_enabled() -> bool:
    if not bool(_get_config("SMTP_ENABLED", False)):
        return False

    required_values = [
        _get_config("SMTP_HOST", ""),
        _get_config("SMTP_PORT", ""),
        _get_config("SMTP_USERNAME", ""),
        _get_config("SMTP_APP_PASSWORD", "") or _get_config("SMTP_PASSWORD", ""),
        _get_config("ADMIN_ALERT_EMAIL", ""),
    ]

    return all(str(value or "").strip() for value in required_values)


def send_email(subject: str, body: str, to_email: str = "") -> Dict[str, Any]:
    if not is_email_alert_enabled():
        return {
            "sent": False,
            "skipped": True,
            "error": "",
            "message": "Email alert is disabled or SMTP config is incomplete.",
        }

    smtp_host = str(_get_config("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = int(_get_config("SMTP_PORT", 587))
    smtp_username = str(_get_config("SMTP_USERNAME", ""))
    smtp_password = str(_get_config("SMTP_APP_PASSWORD", "") or _get_config("SMTP_PASSWORD", ""))
    from_email = str(_get_config("SMTP_FROM_EMAIL", smtp_username) or smtp_username)
    to_email = str(to_email or _get_config("ADMIN_ALERT_EMAIL", ""))

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(body)

    timeout = int(_get_config("SMTP_TIMEOUT_SECONDS", 10) or 10)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)

        return {
            "sent": True,
            "skipped": False,
            "error": "",
            "message": "Email alert sent.",
        }

    except Exception as exc:
        return {
            "sent": False,
            "skipped": False,
            "error": str(exc),
            "message": "Email alert failed.",
        }


def send_admin_login_alert(event: Dict[str, Any]) -> Dict[str, Any]:
    event_type = str(event.get("event_type") or "login_event")
    identifier = str(event.get("identifier") or "-")
    ip_address = str(event.get("ip_address") or "-")
    user_agent = str(event.get("user_agent") or "-")
    created_at = str(event.get("created_at") or "-")
    event_message = str(event.get("message") or "-")
    success = "yes" if event.get("success") else "no"

    alert_success = bool(_get_config("ADMIN_ALERT_LOGIN_SUCCESS", True))
    alert_failed = bool(_get_config("ADMIN_ALERT_LOGIN_FAILED", True))
    alert_logout = bool(_get_config("ADMIN_ALERT_LOGOUT", True))

    if event_type == "login_success" and not alert_success:
        return {"sent": False, "skipped": True, "error": "", "message": "Login success alert disabled."}

    if event_type == "login_failed" and not alert_failed:
        return {"sent": False, "skipped": True, "error": "", "message": "Login failed alert disabled."}

    if event_type == "logout" and not alert_logout:
        return {"sent": False, "skipped": True, "error": "", "message": "Logout alert disabled."}

    subject = f"GLAND Admin Alert: {event_type}"

    body = "\n".join(
        [
            "GLAND Portfolio Admin Alert",
            "",
            f"Event     : {event_type}",
            f"Success   : {success}",
            f"Identifier: {identifier}",
            f"IP Address: {ip_address}",
            f"Time      : {created_at}",
            f"Message   : {event_message}",
            "",
            "User Agent:",
            user_agent,
        ]
    )

    return send_email(subject, body)


def send_admin_password_reset_email(payload: Dict[str, Any]) -> Dict[str, Any]:
    admin = payload.get("admin") or {}
    reset_url = str(payload.get("reset_url") or "")
    expires_at = str(payload.get("expires_at") or "-")
    ip_address = str(payload.get("ip_address") or "-")
    user_agent = str(payload.get("user_agent") or "-")

    to_email = str(admin.get("email") or _get_config("ADMIN_ALERT_EMAIL", "") or "")

    subject = "GLAND Admin Password Reset"

    body = "\n".join(
        [
            "GLAND Portfolio Admin Password Reset",
            "",
            "A password reset was requested for your admin account.",
            "",
            f"Username : {admin.get('username') or '-'}",
            f"Email    : {admin.get('email') or '-'}",
            f"Expires  : {expires_at}",
            f"IP       : {ip_address}",
            "",
            "Reset link:",
            reset_url,
            "",
            "If you did not request this, ignore this email.",
            "",
            "User Agent:",
            user_agent,
        ]
    )

    return send_email(subject, body, to_email=to_email)

# GLAND ACTIVITY LOG INTEGRATION START
def _gland_activity_log_payload(payload=None, **extra):
    data = {}

    if isinstance(payload, dict):
        data.update(payload)

    data.update(extra or {})
    return data


def _gland_activity_safe_log(category, event_name, payload=None):
    try:
        from backend.activity_log_service import log_activity
        return log_activity(
            category=category,
            event_name=str(event_name or "admin_activity"),
            payload=_gland_activity_log_payload(payload),
        )
    except Exception:
        return {
            "success": False,
            "error": "activity log skipped",
        }


def _gland_activity_wrap_security(fn):
    def _wrapped(event_name="admin_security_event", payload=None, *args, **kwargs):
        _gland_activity_safe_log("security", event_name, payload)
        return fn(event_name, payload, *args, **kwargs)

    _wrapped._gland_activity_log_wrapped = True
    return _wrapped


def _gland_activity_wrap_change(fn):
    def _wrapped(event_name="admin_change_event", payload=None, *args, **kwargs):
        _gland_activity_safe_log("change", event_name, payload)
        return fn(event_name, payload, *args, **kwargs)

    _wrapped._gland_activity_log_wrapped = True
    return _wrapped


def _gland_activity_wrap_contact(fn):
    def _wrapped(payload=None, *args, **kwargs):
        event_name = "contact_message_received"

        if isinstance(payload, dict):
            event_name = str(
                payload.get("event")
                or payload.get("event_name")
                or payload.get("subject")
                or event_name
            )

        _gland_activity_safe_log("contact", event_name, payload)
        return fn(payload, *args, **kwargs)

    _wrapped._gland_activity_log_wrapped = True
    return _wrapped


_gland_security_fn = globals().get("send_gland_security_alert")
if callable(_gland_security_fn) and not getattr(_gland_security_fn, "_gland_activity_log_wrapped", False):
    globals()["send_gland_security_alert"] = _gland_activity_wrap_security(_gland_security_fn)


_gland_change_fn = globals().get("send_gland_admin_change_alert")
if callable(_gland_change_fn) and not getattr(_gland_change_fn, "_gland_activity_log_wrapped", False):
    globals()["send_gland_admin_change_alert"] = _gland_activity_wrap_change(_gland_change_fn)


_gland_contact_fn = globals().get("send_gland_contact_alert")
if callable(_gland_contact_fn) and not getattr(_gland_contact_fn, "_gland_activity_log_wrapped", False):
    globals()["send_gland_contact_alert"] = _gland_activity_wrap_contact(_gland_contact_fn)
# GLAND ACTIVITY LOG INTEGRATION END

# GLAND ALERT EMAIL V3 BRIDGE START
try:
    from backend.gland_alert_email_v3 import (
        classify_alert_category as _gland_v3_classify_alert_category,
        collect_contact_payload as _gland_v3_collect_contact_payload,
        collect_payload as _gland_v3_collect_payload,
        extract_event_name as _gland_v3_extract_event_name,
        send_admin_change_alert as _gland_v3_send_admin_change_alert,
        send_contact_alert as _gland_v3_send_contact_alert,
        send_login_otp_email as _gland_v3_send_login_otp_email,
        send_security_alert as _gland_v3_send_security_alert,
    )

    def send_gland_security_alert(event_name="admin_security_event", payload=None, *args, **kwargs):
        data = {}

        if isinstance(payload, dict):
            data.update(payload)
            data.update(kwargs or {})
        elif payload is not None:
            data.update(_gland_v3_collect_payload(payload, *args, **kwargs))
        else:
            data.update(_gland_v3_collect_payload(*args, **kwargs))

        return _gland_v3_send_security_alert(event_name, data)


    def send_gland_admin_change_alert(event_name="admin_change_event", payload=None, *args, **kwargs):
        data = {}

        if isinstance(payload, dict):
            data.update(payload)
            data.update(kwargs or {})
        elif payload is not None:
            data.update(_gland_v3_collect_payload(payload, *args, **kwargs))
        else:
            data.update(_gland_v3_collect_payload(*args, **kwargs))

        return _gland_v3_send_admin_change_alert(event_name, data)


    def send_gland_contact_alert(payload=None, *args, **kwargs):
        if isinstance(payload, dict):
            data = dict(payload)
            data.update(kwargs or {})
        else:
            values = []

            if payload is not None:
                values.append(payload)

            values.extend(args)
            data = _gland_v3_collect_contact_payload(*values, **kwargs)

        return _gland_v3_send_contact_alert(data)


    def send_admin_login_verification_email(payload):
        return _gland_v3_send_login_otp_email(payload)


    def _gland_v3_wrap_alert_sender(fn):
        def _wrapped(*args, **kwargs):
            payload = _gland_v3_collect_payload(*args, **kwargs)
            event_name = _gland_v3_extract_event_name(payload)
            category = _gland_v3_classify_alert_category(event_name, payload)

            if category == "security":
                return _gland_v3_send_security_alert(event_name, payload)

            if category == "change":
                return _gland_v3_send_admin_change_alert(event_name, payload)

            return fn(*args, **kwargs)

        _wrapped._gland_v3_wrapped = True
        _wrapped.__name__ = getattr(fn, "__name__", "_wrapped")
        return _wrapped


    def _gland_v3_contact_adapter(*args, **kwargs):
        payload = _gland_v3_collect_contact_payload(*args, **kwargs)
        return _gland_v3_send_contact_alert(payload)


    for _gland_v3_name in [
        "send_admin_activity_alert",
        "send_admin_activity_email",
        "send_admin_alert",
        "send_admin_alert_email",
        "send_admin_event_alert",
        "send_admin_notification",
        "send_activity_alert",
        "send_activity_log_alert",
        "send_auth_alert",
        "send_login_alert",
        "send_security_alert",
        "send_branded_admin_alert",
        "send_branded_admin_email",
        "send_branded_activity_alert",
        "send_notification_email",
        "send_email_notification",
    ]:
        _gland_v3_candidate = globals().get(_gland_v3_name)

        if callable(_gland_v3_candidate) and not getattr(_gland_v3_candidate, "_gland_v3_wrapped", False):
            globals()[_gland_v3_name] = _gland_v3_wrap_alert_sender(_gland_v3_candidate)


    for _gland_v3_contact_name in [
        "send_contact_alert",
        "send_contact_alert_email",
        "send_contact_message_alert",
        "send_contact_notification",
        "send_branded_contact_alert",
        "send_branded_contact_email",
        "send_gland_contact_message_alert",
    ]:
        globals()[_gland_v3_contact_name] = _gland_v3_contact_adapter

except Exception as _gland_v3_error:
    print("GLAND alert email v3 bridge failed:", _gland_v3_error)
# GLAND ALERT EMAIL V3 BRIDGE END
