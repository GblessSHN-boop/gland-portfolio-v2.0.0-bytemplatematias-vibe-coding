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

# GLAND ADMIN LOGIN VERIFICATION EMAIL START
def send_admin_login_verification_email(payload):
    import smtplib
    import ssl
    from email.message import EmailMessage

    try:
        config_getter = _get_config
    except NameError:
        import config

        def config_getter(name, default=None):
            return getattr(config, name, default)

    payload = payload or {}
    admin = payload.get("admin") or {}

    code = str(payload.get("code") or "").strip()
    expires_at = str(payload.get("expires_at") or "-")
    ip_address = str(payload.get("ip_address") or "-")
    user_agent = str(payload.get("user_agent") or "-")

    # FIX:
    # OTP wajib dikirim ke email akun yang sedang login.
    # Tidak boleh fallback ke ADMIN_ALERT_EMAIL.
    # Tidak boleh fallback ke SMTP_USERNAME.
    to_email = str(admin.get("email") or "").strip().lower()

    if not to_email:
        return {
            "sent": False,
            "skipped": True,
            "error": "Admin account does not have an email address.",
            "recipient": "",
        }

    if not code:
        return {
            "sent": False,
            "skipped": True,
            "error": "Missing verification code.",
            "recipient": to_email,
        }

    if not bool(config_getter("SMTP_ENABLED", True)):
        return {
            "sent": False,
            "skipped": True,
            "error": "SMTP is disabled.",
            "recipient": to_email,
        }

    smtp_host = str(config_getter("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
    smtp_port = int(config_getter("SMTP_PORT", 587) or 587)
    smtp_username = str(config_getter("SMTP_USERNAME", "") or "").strip()
    smtp_password = str(
        config_getter("SMTP_APP_PASSWORD", "")
        or config_getter("SMTP_PASSWORD", "")
        or ""
    ).strip()

    from_email = str(
        config_getter("SMTP_FROM_EMAIL", "")
        or smtp_username
        or ""
    ).strip()

    from_name = str(
        config_getter("SMTP_FROM_NAME", "GLAND Portfolio CMS")
        or "GLAND Portfolio CMS"
    ).strip()

    if not smtp_username or not smtp_password:
        return {
            "sent": False,
            "skipped": False,
            "error": "SMTP username or password is missing.",
            "recipient": to_email,
        }

    if not from_email:
        from_email = smtp_username

    subject = f"GLAND Login Code: {code}"

    body = "\n".join(
        [
            "GLAND Portfolio Admin",
            "",
            "Your 6-digit login verification code is:",
            "",
            f"    {code}",
            "",
            f"Username : {admin.get('username') or '-'}",
            f"Email    : {admin.get('email') or '-'}",
            f"Expires  : {expires_at}",
            f"IP       : {ip_address}",
            "",
            "Enter this code on the admin login page to finish signing in.",
            "",
            "If you did not try to sign in, change your admin password and review Admin Activity.",
            "",
            "User Agent:",
            user_agent,
        ]
    )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = to_email
    message["Reply-To"] = from_email
    message["X-GLAND-OTP-Recipient"] = to_email
    message.set_content(body)

    try:
        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=context) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(message)

        return {
            "sent": True,
            "skipped": False,
            "error": "",
            "message": f"OTP email sent only to login account email: {to_email}",
            "recipient": to_email,
        }

    except Exception as error:
        return {
            "sent": False,
            "skipped": False,
            "error": str(error),
            "message": "Failed to send OTP email to login account email.",
            "recipient": to_email,
        }
# GLAND ADMIN LOGIN VERIFICATION EMAIL END


# GLAND OTP ALERT SUPPRESS START
def _gland_should_suppress_login_verification_sent_alert(*args, **kwargs):
    text = (repr(args) + " " + repr(kwargs)).lower()
    return "login_verification_sent" in text

def _gland_wrap_alert_sender(fn):
    def _wrapped(*args, **kwargs):
        if _gland_should_suppress_login_verification_sent_alert(*args, **kwargs):
            return {
                "sent": False,
                "skipped": True,
                "error": "",
                "message": "login_verification_sent admin alert suppressed. OTP is sent only to the login account email.",
            }

        return fn(*args, **kwargs)

    _wrapped._gland_wrapped = True
    return _wrapped

for _gland_alert_fn_name in [
    "send_admin_activity_alert",
    "send_admin_alert",
    "send_admin_alert_email",
    "send_admin_event_alert",
    "send_admin_notification",
    "send_branded_admin_alert",
    "send_branded_admin_email",
    "send_notification_email",
    "send_email_notification",
    "send_email",
]:
    _gland_candidate = globals().get(_gland_alert_fn_name)

    if callable(_gland_candidate) and not getattr(_gland_candidate, "_gland_wrapped", False):
        globals()[_gland_alert_fn_name] = _gland_wrap_alert_sender(_gland_candidate)
# GLAND OTP ALERT SUPPRESS END

