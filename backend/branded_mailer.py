from __future__ import annotations

import html
import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import config
except Exception:
    config = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _get_config(name: str, default=None):
    if config is None:
        return default
    return getattr(config, name, default)


def _smtp_enabled() -> bool:
    return bool(_get_config("SMTP_ENABLED", False))


def _find_brand_icon_path() -> Optional[Path]:
    candidates = [
        "assets/img/logo/favicon.png",
        "assets/img/logo/favicon.ico",
        "assets/img/logo/gland-header-icon.gif",
        "favicon.ico",
        "favicon.png",
        "assets/favicon.ico",
        "assets/favicon.png",
        "assets/images/favicon.ico",
        "assets/images/favicon.png",
        "frontend/public/favicon.ico",
        "frontend/public/favicon.png",
        "frontend/public/assets/images/favicon.ico",
        "frontend/public/assets/images/favicon.png",
    ]

    for relative in candidates:
        path = PROJECT_ROOT / relative
        if path.exists() and path.is_file():
            return path

    return None


def _send_email_message(message: EmailMessage) -> Dict[str, Any]:
    if not _smtp_enabled():
        return {
            "sent": False,
            "skipped": True,
            "error": None,
        }

    host = str(_get_config("SMTP_HOST", "") or "").strip()
    port = int(_get_config("SMTP_PORT", 587) or 587)
    username = str(_get_config("SMTP_USERNAME", "") or "").strip()
    app_password = str(_get_config("SMTP_APP_PASSWORD", "") or _get_config("SMTP_PASSWORD", "") or "")
    timeout_seconds = int(_get_config("SMTP_TIMEOUT_SECONDS", 10) or 10)

    if not host or not username or not app_password:
        return {
            "sent": False,
            "skipped": True,
            "error": "SMTP config incomplete.",
        }

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP(host, port, timeout=timeout_seconds) as server:
            server.starttls(context=context)
            server.login(username, app_password)
            server.send_message(message)

        return {
            "sent": True,
            "skipped": False,
            "error": None,
        }

    except Exception as exc:
        return {
            "sent": False,
            "skipped": False,
            "error": str(exc),
        }


def send_admin_password_reset_email(payload: Dict[str, Any]) -> Dict[str, Any]:
    admin = payload.get("admin") or {}
    reset_url = str(payload.get("reset_url") or "").strip()
    expires_at = str(payload.get("expires_at") or "-").strip()
    ip_address = str(payload.get("ip_address") or "-").strip()
    user_agent = str(payload.get("user_agent") or "-").strip()

    to_email = str(admin.get("email") or _get_config("ADMIN_ALERT_EMAIL", "") or "").strip()
    from_email = str(_get_config("SMTP_FROM_EMAIL", "") or to_email).strip()

    if not to_email:
        return {
            "sent": False,
            "skipped": True,
            "error": "No destination email configured.",
        }

    escaped_username = html.escape(str(admin.get("username") or "-"))
    escaped_email = html.escape(str(admin.get("email") or "-"))
    escaped_expires = html.escape(expires_at)
    escaped_ip = html.escape(ip_address)
    escaped_user_agent = html.escape(user_agent)
    escaped_reset_url = html.escape(reset_url)

    subject = "GLAND Admin Password Reset"

    text_body = "\n".join(
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

    logo_path = _find_brand_icon_path()
    logo_html = """
        <div style="width:48px;height:48px;border-radius:14px;background:#c9f31d;color:#111111;
                    font-weight:800;font-size:20px;line-height:48px;text-align:center;
                    font-family:Arial,Helvetica,sans-serif;">
            GS
        </div>
    """

    logo_cid = "gland-favicon"

    if logo_path:
        logo_html = f'<img src="cid:{logo_cid}" alt="GLAND" width="48" height="48" style="display:block;border-radius:14px;" />'

    html_body = f"""
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f3f5f7;">
    <div style="padding:32px 16px;">
      <div style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:20px;
                  overflow:hidden;border:1px solid #e9edf1;box-shadow:0 12px 40px rgba(15,23,42,0.08);">
        
        <div style="padding:24px 28px;background:linear-gradient(135deg,#101010 0%,#1d1f21 100%);">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;">{logo_html}</td>
              <td style="width:14px;"></td>
              <td style="vertical-align:middle;">
                <div style="font-family:Arial,Helvetica,sans-serif;color:#c9f31d;font-size:12px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;">
                  GLAND Portfolio CMS
                </div>
                <div style="font-family:Arial,Helvetica,sans-serif;color:#ffffff;font-size:20px;font-weight:800;margin-top:6px;">
                  Admin Password Reset
                </div>
              </td>
            </tr>
          </table>
        </div>

        <div style="padding:30px 28px 10px 28px;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
          <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#111827;">
            Reset your admin password
          </h1>

          <p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;color:#4b5563;">
            A password reset was requested for your <strong>GLAND Portfolio Admin Dashboard</strong>.
            If this was you, use the button below to continue.
          </p>

          <div style="margin:28px 0;">
            <a href="{escaped_reset_url}"
               style="display:inline-block;padding:14px 24px;border-radius:999px;background:#c9f31d;
                      color:#111111;text-decoration:none;font-size:15px;font-weight:800;">
              Reset Password
            </a>
          </div>

          <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:16px;padding:18px 18px 4px 18px;">
            <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:12px;">
              Request details
            </div>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="font-size:14px;color:#374151;">
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;width:110px;">Username</td>
                <td style="padding:0 0 10px 0;">{escaped_username}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Email</td>
                <td style="padding:0 0 10px 0;">{escaped_email}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Expires</td>
                <td style="padding:0 0 10px 0;">{escaped_expires}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">IP</td>
                <td style="padding:0 0 10px 0;">{escaped_ip}</td>
              </tr>
            </table>
          </div>

          <p style="margin:22px 0 8px 0;font-size:14px;line-height:1.7;color:#4b5563;">
            If the button above does not work, use this link:
          </p>

          <p style="margin:0 0 18px 0;word-break:break-all;">
            <a href="{escaped_reset_url}" style="font-size:14px;color:#2563eb;text-decoration:none;">
              {escaped_reset_url}
            </a>
          </p>

          <p style="margin:0 0 18px 0;font-size:14px;line-height:1.7;color:#4b5563;">
            If you did not request this, you can safely ignore this email.
          </p>
        </div>

        <div style="padding:18px 28px 28px 28px;font-family:Arial,Helvetica,sans-serif;">
          <div style="border-top:1px solid #e5e7eb;padding-top:18px;color:#6b7280;font-size:12px;line-height:1.6;">
            <div><strong>User Agent:</strong> {escaped_user_agent}</div>
            <div style="margin-top:8px;">This email was sent by GLAND Portfolio Admin Dashboard.</div>
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if logo_path:
        guessed_type, _ = mimetypes.guess_type(str(logo_path))
        mime_type = guessed_type or "image/png"
        maintype, subtype = mime_type.split("/", 1)

        with open(logo_path, "rb") as image_file:
            image_data = image_file.read()

        html_part = message.get_payload()[-1]
        html_part.add_related(
            image_data,
            maintype=maintype,
            subtype=subtype,
            cid=f"<{logo_cid}>",
            filename=logo_path.name,
        )

    return _send_email_message(message)


# GLAND CONTACT ALERT MAILER START
def send_contact_message_alert(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not bool(_get_config("CONTACT_ALERTS_ENABLED", True)):
        return {
            "sent": False,
            "skipped": True,
            "error": "Contact alerts disabled.",
        }

    to_email = str(_get_config("ADMIN_ALERT_EMAIL", "") or "").strip()
    from_email = str(
        _get_config("SMTP_FROM_EMAIL", "")
        or _get_config("SMTP_USERNAME", "")
        or to_email
    ).strip()
    from_name = str(_get_config("SMTP_FROM_NAME", "GLAND Portfolio CMS") or "GLAND Portfolio CMS").strip()

    if not to_email:
        return {
            "sent": False,
            "skipped": True,
            "error": "No destination email configured.",
        }

    name = str(payload.get("name") or "-").strip()
    email = str(payload.get("email") or "-").strip()
    subject_text = str(payload.get("subject") or "Website Contact Message").strip()
    message_text = str(payload.get("message") or payload.get("content") or "-").strip()
    status = str(payload.get("status") or "new").strip()
    message_id = str(payload.get("id") or "-").strip()
    created_at = str(payload.get("created_at") or payload.get("createdAt") or "-").strip()
    ip_address = str(payload.get("ip_address") or "-").strip()
    user_agent = str(payload.get("user_agent") or "-").strip()

    configured_base_url = str(_get_config("PASSWORD_RESET_BASE_URL", "") or "").rstrip("/")
    fallback_admin_url = (
        configured_base_url + "/admin/messages.html"
        if configured_base_url
        else "http://127.0.0.1:8000/admin/messages.html"
    )
    admin_url = str(payload.get("admin_messages_url") or fallback_admin_url).strip()

    escaped_name = html.escape(name)
    escaped_email = html.escape(email)
    escaped_subject = html.escape(subject_text)
    escaped_message = html.escape(message_text)
    escaped_status = html.escape(status)
    escaped_message_id = html.escape(message_id)
    escaped_created_at = html.escape(created_at)
    escaped_ip = html.escape(ip_address)
    escaped_user_agent = html.escape(user_agent)
    escaped_admin_url = html.escape(admin_url)

    safe_subject = subject_text[:80] if subject_text else "Website Contact Message"
    subject = f"GLAND Contact Message: {safe_subject}"

    text_body = "\n".join(
        [
            "GLAND Portfolio CMS - New Contact Message",
            "",
            f"ID       : {message_id}",
            f"Name     : {name}",
            f"Email    : {email}",
            f"Subject  : {subject_text}",
            f"Status   : {status}",
            f"Created  : {created_at}",
            f"IP       : {ip_address}",
            "",
            "Message:",
            message_text,
            "",
            "Open admin inbox:",
            admin_url,
            "",
            "User Agent:",
            user_agent,
        ]
    )

    logo_path = _find_brand_icon_path()
    logo_html = """
        <div style="width:48px;height:48px;border-radius:14px;background:#c9f31d;color:#111111;
                    font-weight:800;font-size:20px;line-height:48px;text-align:center;
                    font-family:Arial,Helvetica,sans-serif;">
            GS
        </div>
    """

    logo_cid = "gland-contact-favicon"

    if logo_path:
        logo_html = f'<img src="cid:{logo_cid}" alt="GLAND" width="48" height="48" style="display:block;border-radius:14px;" />'

    html_body = f"""
<!DOCTYPE html>
<html>
  <body style="margin:0;padding:0;background:#f3f5f7;">
    <div style="padding:32px 16px;">
      <div style="max-width:680px;margin:0 auto;background:#ffffff;border-radius:20px;
                  overflow:hidden;border:1px solid #e9edf1;box-shadow:0 12px 40px rgba(15,23,42,0.08);">

        <div style="padding:24px 28px;background:linear-gradient(135deg,#101010 0%,#1d1f21 100%);">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0">
            <tr>
              <td style="vertical-align:middle;">{logo_html}</td>
              <td style="width:14px;"></td>
              <td style="vertical-align:middle;">
                <div style="font-family:Arial,Helvetica,sans-serif;color:#c9f31d;font-size:12px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;">
                  GLAND Portfolio CMS
                </div>
                <div style="font-family:Arial,Helvetica,sans-serif;color:#ffffff;font-size:20px;font-weight:800;margin-top:6px;">
                  New Contact Message
                </div>
              </td>
            </tr>
          </table>
        </div>

        <div style="padding:30px 28px 10px 28px;font-family:Arial,Helvetica,sans-serif;color:#1f2937;">
          <h1 style="margin:0 0 14px 0;font-size:28px;line-height:1.2;color:#111827;">
            Someone sent a message
          </h1>

          <p style="margin:0 0 22px 0;font-size:15px;line-height:1.7;color:#4b5563;">
            A new message was submitted from the public contact form and saved to your
            <strong>GLAND Portfolio Admin Dashboard</strong>.
          </p>

          <div style="background:#f8fafc;border:1px solid #e5e7eb;border-radius:16px;padding:18px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="font-size:14px;color:#374151;">
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;width:110px;">Message ID</td>
                <td style="padding:0 0 10px 0;">{escaped_message_id}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Name</td>
                <td style="padding:0 0 10px 0;">{escaped_name}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Email</td>
                <td style="padding:0 0 10px 0;">{escaped_email}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Subject</td>
                <td style="padding:0 0 10px 0;">{escaped_subject}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Status</td>
                <td style="padding:0 0 10px 0;">{escaped_status}</td>
              </tr>
              <tr>
                <td style="padding:0 0 10px 0;font-weight:700;">Created</td>
                <td style="padding:0 0 10px 0;">{escaped_created_at}</td>
              </tr>
              <tr>
                <td style="padding:0;font-weight:700;">IP</td>
                <td style="padding:0;">{escaped_ip}</td>
              </tr>
            </table>
          </div>

          <div style="margin:22px 0 0 0;background:#111827;border-radius:16px;padding:20px;">
            <div style="font-size:12px;font-weight:800;color:#c9f31d;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:10px;">
              Message
            </div>
            <div style="font-size:15px;line-height:1.8;color:#ffffff;white-space:pre-wrap;">
              {escaped_message}
            </div>
          </div>

          <div style="margin:28px 0;">
            <a href="{escaped_admin_url}"
               style="display:inline-block;padding:14px 24px;border-radius:999px;background:#c9f31d;
                      color:#111111;text-decoration:none;font-size:15px;font-weight:800;">
              Open Messages Dashboard
            </a>
          </div>
        </div>

        <div style="padding:18px 28px 28px 28px;font-family:Arial,Helvetica,sans-serif;">
          <div style="border-top:1px solid #e5e7eb;padding-top:18px;color:#6b7280;font-size:12px;line-height:1.6;">
            <div><strong>User Agent:</strong> {escaped_user_agent}</div>
            <div style="margin-top:8px;">This email was sent by GLAND Portfolio Admin Dashboard.</div>
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
""".strip()

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if logo_path:
        guessed_type, _ = mimetypes.guess_type(str(logo_path))
        mime_type = guessed_type or "image/png"
        maintype, subtype = mime_type.split("/", 1)

        with open(logo_path, "rb") as image_file:
            image_data = image_file.read()

        html_part = message.get_payload()[-1]
        html_part.add_related(
            image_data,
            maintype=maintype,
            subtype=subtype,
            cid=f"<{logo_cid}>",
            filename=logo_path.name,
        )

    return _send_email_message(message)
# GLAND CONTACT ALERT MAILER END

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
