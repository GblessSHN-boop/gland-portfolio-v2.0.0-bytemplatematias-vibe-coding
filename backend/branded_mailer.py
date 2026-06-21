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

# GLAND ALERT ROUTING START
def _gland_cfg(name, default=None):
    try:
        getter = globals().get("_get_config")
        if callable(getter):
            return getter(name, default)
    except Exception:
        pass

    try:
        import config
        return getattr(config, name, default)
    except Exception:
        return default


def _gland_as_list(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = str(value).replace(";", ",").split(",")

    items = []
    seen = set()

    for item in raw_items:
        email = str(item or "").strip()

        if not email or "@" not in email:
            continue

        key = email.lower()

        if key in seen:
            continue

        seen.add(key)
        items.append(email)

    return items


def _gland_recipients(config_name, fallback_config_name=None):
    recipients = _gland_as_list(_gland_cfg(config_name, None))

    if not recipients and fallback_config_name:
        recipients = _gland_as_list(_gland_cfg(fallback_config_name, None))

    return recipients


def _gland_security_recipients():
    return _gland_recipients("SECURITY_ALERT_EMAILS", "ADMIN_ALERT_EMAIL")


def _gland_admin_change_recipients():
    return _gland_recipients("ADMIN_CHANGE_ALERT_EMAILS", "ADMIN_ALERT_EMAIL")


def _gland_contact_recipients():
    return _gland_recipients("CONTACT_ALERT_EMAILS", "ADMIN_ALERT_EMAIL")


def _gland_request_metadata():
    meta = {}

    try:
        from flask import has_request_context, request

        if has_request_context():
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            forwarded_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""

            meta["ip_address"] = (
                forwarded_ip
                or request.headers.get("X-Real-IP", "")
                or request.remote_addr
                or ""
            )
            meta["user_agent"] = request.headers.get("User-Agent", "")
            meta["method"] = request.method
            meta["path"] = request.path
    except Exception:
        pass

    return meta


def _gland_is_private_ip(ip_address):
    try:
        import ipaddress

        parsed = ipaddress.ip_address(str(ip_address or "").strip())
        return parsed.is_private or parsed.is_loopback or parsed.is_reserved or parsed.is_link_local
    except Exception:
        return True


def _gland_ip_location(ip_address):
    ip_address = str(ip_address or "").strip()

    if not ip_address:
        return {
            "ip_location": "Unavailable. IP address is empty.",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }

    if _gland_is_private_ip(ip_address):
        return {
            "ip_location": "Localhost or private network. Public location is not available.",
            "network_org": "Private network",
            "timezone": "-",
            "coordinates": "-",
        }

    if not bool(_gland_cfg("IP_GEOLOCATION_ENABLED", False)):
        return {
            "ip_location": "Geolocation disabled. Enable IP_GEOLOCATION_ENABLED in config.py for public IP lookup.",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }

    try:
        import json
        import urllib.parse
        import urllib.request

        token = str(_gland_cfg("IPINFO_TOKEN", "") or "").strip()
        encoded_ip = urllib.parse.quote(ip_address)

        if token:
            url = "https://ipinfo.io/{}/json?token={}".format(
                encoded_ip,
                urllib.parse.quote(token),
            )
        else:
            url = "https://ipinfo.io/{}/json".format(encoded_ip)

        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))

        city = data.get("city") or "-"
        region = data.get("region") or "-"
        country = data.get("country") or "-"
        location = ", ".join([part for part in [city, region, country] if part and part != "-"])

        return {
            "ip_location": location or "Unknown public IP location.",
            "network_org": data.get("org") or "-",
            "timezone": data.get("timezone") or "-",
            "coordinates": data.get("loc") or "-",
        }
    except Exception as error:
        return {
            "ip_location": "Lookup failed: {}".format(error),
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }


def _gland_parse_user_agent(user_agent):
    text = str(user_agent or "")
    lower = text.lower()

    os_name = "Unknown OS"
    browser = "Unknown browser"
    device = "Desktop"

    if "windows nt 10" in lower:
        os_name = "Windows 10 or Windows 11"
    elif "windows" in lower:
        os_name = "Windows"
    elif "android" in lower:
        os_name = "Android"
    elif "iphone" in lower:
        os_name = "iOS iPhone"
    elif "ipad" in lower:
        os_name = "iPadOS"
    elif "mac os x" in lower or "macintosh" in lower:
        os_name = "macOS"
    elif "linux" in lower:
        os_name = "Linux"

    if "edg/" in lower or "edga/" in lower:
        browser = "Microsoft Edge"
    elif "opr/" in lower or "opera" in lower:
        browser = "Opera"
    elif "crios/" in lower or "chrome/" in lower:
        browser = "Google Chrome"
    elif "firefox/" in lower or "fxios/" in lower:
        browser = "Mozilla Firefox"
    elif "safari/" in lower:
        browser = "Safari"

    if "ipad" in lower or "tablet" in lower:
        device = "Tablet"
    elif "mobile" in lower or "android" in lower or "iphone" in lower:
        device = "Mobile"

    return {
        "device_type": device,
        "browser": browser,
        "operating_system": os_name,
    }


def _gland_now_text():
    try:
        import datetime as _dt
        return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"


def _gland_safe_key(key):
    text = str(key or "").lower()
    blocked = [
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
    ]

    return not any(word in text for word in blocked)


def _gland_trim(value, limit=800):
    text = str(value if value is not None else "-")

    if len(text) > limit:
        return text[:limit] + "... [trimmed]"

    return text


def _gland_safe_payload(payload):
    safe = {}

    for key, value in dict(payload or {}).items():
        key_text = str(key)

        if not _gland_safe_key(key_text):
            safe[key_text] = "[redacted]"
        else:
            safe[key_text] = _gland_trim(value)

    return safe


def _gland_collect_payload(*args, **kwargs):
    payload = {}

    for index, arg in enumerate(args):
        if isinstance(arg, dict):
            payload.update(arg)
        elif isinstance(arg, str):
            if index == 0:
                payload.setdefault("event", arg)
            else:
                payload.setdefault("arg_{}".format(index), arg)
        elif arg is not None:
            payload.setdefault("arg_{}".format(index), repr(arg))

    payload.update(kwargs or {})
    return payload


def _gland_collect_contact_payload(*args, **kwargs):
    payload = _gland_collect_payload(*args, **kwargs)

    if len(args) >= 4 and not isinstance(args[0], dict):
        payload.setdefault("name", args[0])
        payload.setdefault("email", args[1])
        payload.setdefault("subject", args[2])
        payload.setdefault("message", args[3])

    return payload


def _gland_extract_event_name(payload):
    payload = dict(payload or {})

    for key in [
        "event",
        "event_name",
        "event_type",
        "activity",
        "action",
        "type",
        "name",
        "title",
        "subject",
    ]:
        value = str(payload.get(key) or "").strip()

        if value:
            return value

    return "admin_activity"


def _gland_category(event_name, payload):
    text = (str(event_name or "") + " " + repr(payload or {})).lower()

    security_keywords = [
        "login",
        "logout",
        "otp",
        "verification",
        "auth",
        "session",
        "sign in",
        "signin",
        "signout",
        "failed",
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
        "password_changed",
    ]

    if any(keyword in text for keyword in security_keywords):
        return "security"

    if any(keyword in text for keyword in change_keywords):
        return "change"

    return "other"


def _gland_html_escape(value):
    try:
        import html
        return html.escape(str(value if value is not None else "-"))
    except Exception:
        return str(value if value is not None else "-")


def _gland_send_email_message(recipients, subject, title, rows, intro=""):
    recipients = _gland_as_list(recipients)

    if not recipients:
        return {
            "sent": False,
            "skipped": True,
            "error": "No recipients configured.",
            "recipients": [],
        }

    try:
        import smtplib
        import ssl
        from email.message import EmailMessage

        smtp_host = str(_gland_cfg("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
        smtp_port = int(_gland_cfg("SMTP_PORT", 587) or 587)
        smtp_username = str(_gland_cfg("SMTP_USERNAME", "") or "").strip()
        smtp_password = str(
            _gland_cfg("SMTP_APP_PASSWORD", "")
            or _gland_cfg("SMTP_PASSWORD", "")
            or ""
        ).strip()

        from_email = str(
            _gland_cfg("SMTP_FROM_EMAIL", "")
            or smtp_username
            or ""
        ).strip()

        from_name = str(
            _gland_cfg("SMTP_FROM_NAME", "GLAND Portfolio CMS")
            or "GLAND Portfolio CMS"
        ).strip()

        if not smtp_username or not smtp_password:
            return {
                "sent": False,
                "skipped": False,
                "error": "SMTP username or password is missing.",
                "recipients": recipients,
            }

        if not from_email:
            from_email = smtp_username

        plain_lines = [title, ""]

        if intro:
            plain_lines.extend([intro, ""])

        for label, value in rows:
            plain_lines.append("{} : {}".format(label, value))

        plain = "\n".join(plain_lines)

        html_rows = "\n".join(
            [
                "<tr><td style=\"padding:10px 12px;color:#64748b;border-bottom:1px solid #e5e7eb;width:190px;vertical-align:top;\">{}</td><td style=\"padding:10px 12px;color:#0f172a;border-bottom:1px solid #e5e7eb;white-space:pre-wrap;\">{}</td></tr>".format(
                    _gland_html_escape(label),
                    _gland_html_escape(value),
                )
                for label, value in rows
            ]
        )

        html_intro = ""

        if intro:
            html_intro = "<p style=\"margin:0 0 18px;color:#475569;font-size:14px;line-height:1.6;\">{}</p>".format(
                _gland_html_escape(intro)
            )

        html_body = """<!doctype html>
<html>
  <body style="margin:0;background:#f8fafc;padding:24px;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;overflow:hidden;">
      <div style="padding:22px 24px;background:#0f172a;color:#ffffff;">
        <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#a3e635;font-weight:700;">GLAND Portfolio CMS</div>
        <h1 style="margin:8px 0 0;font-size:22px;line-height:1.35;">{title}</h1>
      </div>
      <div style="padding:24px;">
        {intro}
        <table role="presentation" style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;">
          {rows}
        </table>
        <p style="margin:18px 0 0;color:#94a3b8;font-size:12px;line-height:1.5;">This is an automated alert from GLAND Portfolio CMS.</p>
      </div>
    </div>
  </body>
</html>""".format(
            title=_gland_html_escape(title),
            intro=html_intro,
            rows=html_rows,
        )

        message = EmailMessage()
        message["Subject"] = str(subject)
        message["From"] = "{} <{}>".format(from_name, from_email) if from_name else from_email
        message["To"] = ", ".join(recipients)
        message["Reply-To"] = from_email
        message["X-GLAND-Alert"] = "true"
        message.set_content(plain)
        message.add_alternative(html_body, subtype="html")

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
            "recipients": recipients,
            "subject": str(subject),
        }
    except Exception as error:
        return {
            "sent": False,
            "skipped": False,
            "error": str(error),
            "recipients": recipients,
            "subject": str(subject),
        }


def _gland_enriched_payload(payload):
    payload = dict(payload or {})
    request_meta = _gland_request_metadata()

    for key, value in request_meta.items():
        payload.setdefault(key, value)

    user_agent = str(payload.get("user_agent") or payload.get("userAgent") or "")
    ip_address = str(payload.get("ip_address") or payload.get("ip") or payload.get("remote_addr") or "")

    payload.setdefault("time", _gland_now_text())

    parsed_device = _gland_parse_user_agent(user_agent)
    ip_location = _gland_ip_location(ip_address)

    payload.update(parsed_device)
    payload.update(ip_location)

    if ip_address:
        payload["ip_address"] = ip_address

    if user_agent:
        payload["user_agent"] = user_agent

    return payload


def send_gland_security_alert(event_name="admin_security_event", payload=None):
    payload = _gland_enriched_payload(payload or {})
    safe = _gland_safe_payload(payload)

    rows = [
        ("Event", event_name),
        ("Time", safe.get("time", "-")),
        ("Identifier", safe.get("identifier", safe.get("username", safe.get("email", "-")))),
        ("Admin email", safe.get("email", safe.get("admin_email", "-"))),
        ("Success", safe.get("success", safe.get("status", "-"))),
        ("IP address", safe.get("ip_address", "-")),
        ("Network location", safe.get("ip_location", "-")),
        ("Network provider", safe.get("network_org", "-")),
        ("Timezone", safe.get("timezone", "-")),
        ("Coordinates", safe.get("coordinates", "-")),
        ("Device type", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Operating system", safe.get("operating_system", "-")),
        ("Request path", safe.get("path", "-")),
        ("User agent", safe.get("user_agent", "-")),
    ]

    extra_keys = sorted(
        [
            key for key in safe.keys()
            if key not in {
                "event",
                "event_name",
                "event_type",
                "activity",
                "action",
                "type",
                "name",
                "title",
                "subject",
                "time",
                "identifier",
                "username",
                "email",
                "admin_email",
                "success",
                "status",
                "ip",
                "ip_address",
                "remote_addr",
                "ip_location",
                "network_org",
                "timezone",
                "coordinates",
                "device_type",
                "browser",
                "operating_system",
                "path",
                "user_agent",
                "userAgent",
            }
        ]
    )

    for key in extra_keys:
        rows.append((key, safe.get(key, "-")))

    return _gland_send_email_message(
        _gland_security_recipients(),
        "GLAND Security Alert: {}".format(event_name),
        "Security Alert: {}".format(event_name),
        rows,
        "A security related admin event was recorded. OTP codes and passwords are never included in this alert.",
    )


def send_gland_admin_change_alert(event_name="admin_change_event", payload=None):
    payload = _gland_enriched_payload(payload or {})
    safe = _gland_safe_payload(payload)

    rows = [
        ("Event", event_name),
        ("Time", safe.get("time", "-")),
        ("Admin", safe.get("username", safe.get("identifier", safe.get("email", "-")))),
        ("Admin email", safe.get("email", safe.get("admin_email", "-"))),
        ("Target", safe.get("target", safe.get("resource", safe.get("table", "-")))),
        ("Action", safe.get("action", event_name)),
        ("IP address", safe.get("ip_address", "-")),
        ("Network location", safe.get("ip_location", "-")),
        ("Device type", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Operating system", safe.get("operating_system", "-")),
        ("Request path", safe.get("path", "-")),
        ("User agent", safe.get("user_agent", "-")),
    ]

    extra_keys = sorted(
        [
            key for key in safe.keys()
            if key not in {
                "event",
                "event_name",
                "event_type",
                "activity",
                "action",
                "type",
                "name",
                "title",
                "subject",
                "time",
                "identifier",
                "username",
                "email",
                "admin_email",
                "target",
                "resource",
                "table",
                "ip",
                "ip_address",
                "remote_addr",
                "ip_location",
                "network_org",
                "timezone",
                "coordinates",
                "device_type",
                "browser",
                "operating_system",
                "path",
                "user_agent",
                "userAgent",
            }
        ]
    )

    for key in extra_keys:
        rows.append((key, safe.get(key, "-")))

    return _gland_send_email_message(
        _gland_admin_change_recipients(),
        "GLAND Admin Change: {}".format(event_name),
        "Admin Change: {}".format(event_name),
        rows,
        "An admin CMS change event was recorded.",
    )


def send_gland_contact_alert(payload=None):
    payload = _gland_enriched_payload(payload or {})
    safe = _gland_safe_payload(payload)
    subject_text = safe.get("subject", safe.get("name", "New contact message"))

    rows = [
        ("Time", safe.get("time", "-")),
        ("Name", safe.get("name", "-")),
        ("Email", safe.get("email", "-")),
        ("Phone", safe.get("phone", safe.get("telephone", "-"))),
        ("Subject", safe.get("subject", "-")),
        ("Message", safe.get("message", safe.get("content", "-"))),
        ("IP address", safe.get("ip_address", "-")),
        ("Network location", safe.get("ip_location", "-")),
        ("Network provider", safe.get("network_org", "-")),
        ("Device type", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Operating system", safe.get("operating_system", "-")),
        ("User agent", safe.get("user_agent", "-")),
    ]

    return _gland_send_email_message(
        _gland_contact_recipients(),
        "GLAND Contact Message: {}".format(subject_text),
        "New Contact Message",
        rows,
        "A new message was submitted from the portfolio contact form.",
    )


def _gland_wrap_alert_sender(fn):
    def _wrapped(*args, **kwargs):
        payload = _gland_collect_payload(*args, **kwargs)
        event_name = _gland_extract_event_name(payload)
        category = _gland_category(event_name, payload)

        if category == "security":
            return send_gland_security_alert(event_name, payload)

        if category == "change":
            return send_gland_admin_change_alert(event_name, payload)

        return fn(*args, **kwargs)

    _wrapped._gland_alert_router_wrapped = True
    return _wrapped


def _gland_wrap_contact_sender(fn):
    def _wrapped(*args, **kwargs):
        payload = _gland_collect_contact_payload(*args, **kwargs)
        return send_gland_contact_alert(payload)

    _wrapped._gland_contact_router_wrapped = True
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
]:
    _gland_candidate = globals().get(_gland_alert_fn_name)

    if callable(_gland_candidate) and not getattr(_gland_candidate, "_gland_alert_router_wrapped", False):
        globals()[_gland_alert_fn_name] = _gland_wrap_alert_sender(_gland_candidate)


for _gland_contact_fn_name in [
    "send_contact_alert",
    "send_contact_alert_email",
    "send_contact_message_alert",
    "send_contact_notification",
    "send_branded_contact_alert",
    "send_branded_contact_email",
]:
    _gland_contact_candidate = globals().get(_gland_contact_fn_name)

    if callable(_gland_contact_candidate) and not getattr(_gland_contact_candidate, "_gland_contact_router_wrapped", False):
        globals()[_gland_contact_fn_name] = _gland_wrap_contact_sender(_gland_contact_candidate)
# GLAND ALERT ROUTING END

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
