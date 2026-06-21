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

# GLAND CLEAR SECURITY ALERT V2 START
def _gland_clear_cfg(name, default=None):
    try:
        existing = globals().get("_gland_cfg")
        if callable(existing):
            return existing(name, default)
    except Exception:
        pass

    try:
        existing = globals().get("_get_config")
        if callable(existing):
            return existing(name, default)
    except Exception:
        pass

    try:
        import config
        return getattr(config, name, default)
    except Exception:
        return default


def _gland_clear_as_list(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = str(value).replace(";", ",").split(",")

    cleaned = []

    for item in items:
        text = str(item or "").strip()

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned


def _gland_clear_security_recipients():
    recipients = _gland_clear_as_list(_gland_clear_cfg("SECURITY_ALERT_EMAILS", []))

    if recipients:
        return recipients

    recipients = _gland_clear_as_list(_gland_clear_cfg("ADMIN_SECURITY_EMAILS", []))

    if recipients:
        return recipients

    recipients = _gland_clear_as_list(_gland_clear_cfg("ADMIN_ALERT_EMAILS", []))

    if recipients:
        return recipients

    recipients = _gland_clear_as_list(_gland_clear_cfg("ADMIN_ALERT_EMAIL", ""))

    if recipients:
        return recipients

    fallback = str(_gland_clear_cfg("SMTP_USERNAME", "") or "").strip()

    return [fallback] if fallback else []


def _gland_clear_change_recipients():
    recipients = _gland_clear_as_list(_gland_clear_cfg("ADMIN_CHANGE_ALERT_EMAILS", []))

    if recipients:
        return recipients

    recipients = _gland_clear_as_list(_gland_clear_cfg("ADMIN_CHANGE_EMAILS", []))

    if recipients:
        return recipients

    return ["official.arcdev@gmail.com"]


def _gland_clear_html_escape(value):
    try:
        import html
        return html.escape(str(value if value is not None else "-"))
    except Exception:
        return str(value if value is not None else "-")


def _gland_clear_trim(value, limit=900):
    text = str(value if value is not None else "-")

    if len(text) > limit:
        return text[:limit] + "... [dipotong]"

    return text


def _gland_clear_safe_key(key):
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


def _gland_clear_safe_payload(payload):
    safe = {}

    for key, value in dict(payload or {}).items():
        key_text = str(key)

        if not _gland_clear_safe_key(key_text):
            safe[key_text] = "[redacted]"
        else:
            safe[key_text] = _gland_clear_trim(value)

    return safe


def _gland_clear_collect_payload(*args, **kwargs):
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


def _gland_clear_extract_event_name(payload):
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


def _gland_clear_bool_text(value):
    text = str(value if value is not None else "").strip().lower()

    if text in {"1", "true", "yes", "y", "success", "successful", "ok", "berhasil"}:
        return "success"

    if text in {"0", "false", "no", "n", "failed", "fail", "error", "denied", "invalid", "gagal"}:
        return "failed"

    return ""


def _gland_clear_event_details(event_name, payload):
    payload = dict(payload or {})
    event_text = str(event_name or "").strip()
    text = (event_text + " " + repr(payload)).lower()

    explicit_status = (
        _gland_clear_bool_text(payload.get("success"))
        or _gland_clear_bool_text(payload.get("status"))
        or _gland_clear_bool_text(payload.get("result"))
    )

    details = {
        "label": "Aktivitas Keamanan Admin",
        "subject_label": "Aktivitas Keamanan Admin",
        "status": explicit_status or "info",
        "stage": "Aktivitas admin.",
        "meaning": "Sistem mencatat aktivitas keamanan pada area admin.",
        "impact": "Periksa detail perangkat, IP, dan akun terkait.",
        "severity": "normal",
    }

    if "login_verification_sent" in text or "verification_sent" in text or "otp_sent" in text or "code_sent" in text:
        details.update({
            "label": "Kode OTP Login Dikirim",
            "subject_label": "OTP Dikirim, Belum Login Penuh",
            "status": "info",
            "stage": "Email dan password sudah benar. Sistem mengirim kode OTP.",
            "meaning": "Ini baru percobaan login yang lolos password. Akun belum masuk dashboard sebelum OTP benar.",
            "impact": "Belum ada session admin final yang dibuat.",
            "severity": "normal",
        })
    elif "login_verification_success" in text or "verification_success" in text or "otp_success" in text:
        details.update({
            "label": "OTP Login Benar",
            "subject_label": "OTP Benar",
            "status": "success",
            "stage": "Verifikasi OTP berhasil.",
            "meaning": "Kode OTP yang dimasukkan valid.",
            "impact": "Sistem dapat melanjutkan proses pembuatan session login.",
            "severity": "normal",
        })
    elif "login_verification_failed" in text or "verification_failed" in text or "otp_failed" in text or "invalid_otp" in text or "wrong_otp" in text:
        details.update({
            "label": "OTP Login Gagal",
            "subject_label": "OTP Salah atau Gagal",
            "status": "failed",
            "stage": "Verifikasi OTP gagal.",
            "meaning": "Kode OTP yang dimasukkan salah, sudah kedaluwarsa, atau melewati batas percobaan.",
            "impact": "Login ditolak. Session admin tidak dibuat dari percobaan ini.",
            "severity": "high",
        })
    elif "login_success" in text or "signin_success" in text or "sign_in_success" in text:
        details.update({
            "label": "Login Berhasil",
            "subject_label": "Login Berhasil, Session Dibuat",
            "status": "success",
            "stage": "Login final berhasil.",
            "meaning": "Akun admin berhasil masuk setelah proses autentikasi selesai.",
            "impact": "Session admin aktif dibuat untuk perangkat ini.",
            "severity": "normal",
        })
    elif "login_failed" in text or "signin_failed" in text or "sign_in_failed" in text or "invalid_password" in text or "auth_failed" in text:
        details.update({
            "label": "Login Gagal",
            "subject_label": "Login Gagal",
            "status": "failed",
            "stage": "Cek kredensial login gagal.",
            "meaning": "Email, username, password, atau syarat login tidak valid.",
            "impact": "Login ditolak. Session admin tidak dibuat.",
            "severity": "high",
        })
    elif "logout" in text or "signout" in text or "sign_out" in text:
        details.update({
            "label": "Logout Admin",
            "subject_label": "Logout Admin",
            "status": explicit_status or "success",
            "stage": "Admin keluar dari dashboard.",
            "meaning": "Session admin diakhiri dari perangkat ini.",
            "impact": "Akses dashboard pada session tersebut dihentikan.",
            "severity": "normal",
        })
    elif "session_expired" in text or "session_invalid" in text or "session_revoked" in text:
        details.update({
            "label": "Session Admin Ditolak",
            "subject_label": "Session Admin Ditolak",
            "status": "failed",
            "stage": "Validasi session gagal.",
            "meaning": "Session hilang, kedaluwarsa, atau dicabut.",
            "impact": "Akses dashboard ditolak sampai login ulang.",
            "severity": "high",
        })
    elif "password_reset" in text or "reset_password" in text:
        details.update({
            "label": "Password Reset Admin",
            "subject_label": "Password Reset Admin",
            "status": explicit_status or "info",
            "stage": "Proses reset password admin.",
            "meaning": "Sistem mencatat tindakan terkait reset password.",
            "impact": "Periksa apakah tindakan ini memang dilakukan oleh pemilik akun.",
            "severity": "high",
        })

    return details


def _gland_clear_category(event_name, payload):
    text = (str(event_name or "") + " " + repr(payload or {})).lower()

    security_keywords = [
        "login",
        "logout",
        "otp",
        "verification",
        "auth",
        "session",
        "signin",
        "signout",
        "sign in",
        "sign out",
        "password",
        "reset",
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
        "page",
        "hero",
        "site_identity",
    ]

    if any(keyword in text for keyword in security_keywords):
        return "security"

    if any(keyword in text for keyword in change_keywords):
        return "change"

    return "other"


def _gland_clear_enrich_payload(payload):
    payload = dict(payload or {})

    existing = globals().get("_gland_enriched_payload")

    if callable(existing):
        try:
            return existing(payload)
        except Exception:
            pass

    try:
        from flask import request, has_request_context

        if has_request_context():
            payload.setdefault("ip_address", request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip())
            payload.setdefault("user_agent", request.headers.get("User-Agent", ""))
            payload.setdefault("request_path", request.path)
            payload.setdefault("request_method", request.method)
    except Exception:
        pass

    try:
        import datetime as _dt
        payload.setdefault("time", _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        payload.setdefault("time", "-")

    user_agent = str(payload.get("user_agent") or payload.get("userAgent") or "")
    lower = user_agent.lower()

    device_type = "Desktop"
    browser = "Unknown browser"
    os_name = "Unknown OS"

    if "android" in lower:
        os_name = "Android"
    elif "iphone" in lower:
        os_name = "iOS iPhone"
    elif "ipad" in lower:
        os_name = "iPadOS"
    elif "windows nt 10" in lower:
        os_name = "Windows 10 or Windows 11"
    elif "windows" in lower:
        os_name = "Windows"
    elif "mac os x" in lower or "macintosh" in lower:
        os_name = "macOS"
    elif "linux" in lower:
        os_name = "Linux"

    if "edg/" in lower:
        browser = "Microsoft Edge"
    elif "opr/" in lower or "opera" in lower:
        browser = "Opera"
    elif "chrome/" in lower or "crios/" in lower:
        browser = "Google Chrome"
    elif "firefox/" in lower or "fxios/" in lower:
        browser = "Mozilla Firefox"
    elif "safari/" in lower:
        browser = "Safari"

    if "mobile" in lower or "android" in lower or "iphone" in lower:
        device_type = "Mobile"
    elif "ipad" in lower or "tablet" in lower:
        device_type = "Tablet"

    ip_address = str(payload.get("ip_address") or payload.get("ip") or payload.get("remote_addr") or "").strip()

    payload.setdefault("device_type", device_type)
    payload.setdefault("browser", browser)
    payload.setdefault("operating_system", os_name)

    if ip_address in {"127.0.0.1", "::1"} or ip_address.startswith("192.168.") or ip_address.startswith("10.") or ip_address.startswith("172.16."):
        payload.setdefault("ip_location", "Localhost atau private network. Lokasi publik tidak tersedia.")
        payload.setdefault("network_org", "Private network")
    else:
        payload.setdefault("ip_location", "-")
        payload.setdefault("network_org", "-")

    return payload


def _gland_clear_send_email(recipients, subject, title, rows, intro=""):
    recipients = _gland_clear_as_list(recipients)

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

        smtp_host = str(_gland_clear_cfg("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
        smtp_port = int(_gland_clear_cfg("SMTP_PORT", 587) or 587)
        smtp_username = str(_gland_clear_cfg("SMTP_USERNAME", "") or "").strip()
        smtp_password = str(
            _gland_clear_cfg("SMTP_APP_PASSWORD", "")
            or _gland_clear_cfg("SMTP_PASSWORD", "")
            or ""
        ).strip()

        from_email = str(
            _gland_clear_cfg("SMTP_FROM_EMAIL", "")
            or smtp_username
            or ""
        ).strip()

        from_name = str(
            _gland_clear_cfg("SMTP_FROM_NAME", "GLAND Portfolio CMS")
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
                "<tr><td style=\"padding:10px 12px;color:#64748b;border-bottom:1px solid #e5e7eb;width:210px;vertical-align:top;font-weight:700;\">{}</td><td style=\"padding:10px 12px;color:#0f172a;border-bottom:1px solid #e5e7eb;white-space:pre-wrap;\">{}</td></tr>".format(
                    _gland_clear_html_escape(label),
                    _gland_clear_html_escape(value),
                )
                for label, value in rows
            ]
        )

        html_intro = ""

        if intro:
            html_intro = "<p style=\"margin:0 0 18px;color:#334155;font-size:14px;line-height:1.7;\">{}</p>".format(
                _gland_clear_html_escape(intro)
            )

        html_body = """<!doctype html>
<html>
  <body style="margin:0;background:#f8fafc;padding:24px;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:820px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:18px;overflow:hidden;">
      <div style="padding:22px 24px;background:#0f172a;color:#ffffff;">
        <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#a3e635;font-weight:800;">GLAND Portfolio CMS</div>
        <h1 style="margin:8px 0 0;font-size:22px;line-height:1.35;">{title}</h1>
      </div>
      <div style="padding:24px;">
        {intro}
        <table role="presentation" style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;">
          {rows}
        </table>
        <p style="margin:18px 0 0;color:#64748b;font-size:12px;line-height:1.6;">Catatan keamanan: password, token, session, dan kode OTP tidak pernah ditampilkan di email alert ini.</p>
      </div>
    </div>
  </body>
</html>""".format(
            title=_gland_clear_html_escape(title),
            intro=html_intro,
            rows=html_rows,
        )

        message = EmailMessage()
        message["Subject"] = str(subject)
        message["From"] = "{} <{}>".format(from_name, from_email) if from_name else from_email
        message["To"] = ", ".join(recipients)
        message["Reply-To"] = from_email
        message["X-GLAND-Alert"] = "security"
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


def send_gland_security_alert(event_name="admin_security_event", payload=None):
    payload = _gland_clear_enrich_payload(payload or {})
    event_name = str(event_name or _gland_clear_extract_event_name(payload) or "admin_security_event")
    safe = _gland_clear_safe_payload(payload)
    details = _gland_clear_event_details(event_name, payload)

    identifier = (
        safe.get("identifier")
        or safe.get("username")
        or safe.get("email")
        or safe.get("admin_email")
        or "-"
    )

    status_text = {
        "success": "BERHASIL",
        "failed": "GAGAL",
        "info": "INFO",
    }.get(details.get("status"), str(details.get("status") or "INFO").upper())

    subject = "GLAND Security Alert: {} | {}".format(
        details.get("subject_label") or details.get("label"),
        identifier,
    )

    intro = "Ringkasan: {}. Status: {}. {}".format(
        details.get("label"),
        status_text,
        details.get("meaning"),
    )

    rows = [
        ("Jenis alert", details.get("label", "-")),
        ("Status kejadian", status_text),
        ("Event teknis", event_name),
        ("Tahap proses", details.get("stage", "-")),
        ("Arti kejadian", details.get("meaning", "-")),
        ("Dampak keamanan", details.get("impact", "-")),
        ("Tingkat risiko", details.get("severity", "normal")),
        ("Akun atau identifier", identifier),
        ("Email admin", safe.get("email", safe.get("admin_email", "-"))),
        ("Username", safe.get("username", safe.get("admin_username", "-"))),
        ("Waktu", safe.get("time", safe.get("created_at", "-"))),
        ("IP address", safe.get("ip_address", safe.get("ip", safe.get("remote_addr", "-")))),
        ("Lokasi jaringan", safe.get("ip_location", "-")),
        ("Provider jaringan", safe.get("network_org", "-")),
        ("Timezone", safe.get("timezone", "-")),
        ("Koordinat", safe.get("coordinates", "-")),
        ("Jenis perangkat", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Sistem operasi", safe.get("operating_system", "-")),
        ("Request method", safe.get("request_method", safe.get("method", "-"))),
        ("Request path", safe.get("request_path", safe.get("path", "-"))),
        ("User agent", safe.get("user_agent", safe.get("userAgent", "-"))),
    ]

    known = {
        "event",
        "event_name",
        "event_type",
        "activity",
        "action",
        "type",
        "name",
        "title",
        "subject",
        "success",
        "status",
        "result",
        "identifier",
        "username",
        "admin_username",
        "email",
        "admin_email",
        "time",
        "created_at",
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
        "request_method",
        "method",
        "request_path",
        "path",
        "user_agent",
        "userAgent",
    }

    extra_count = 0

    for key in sorted(safe.keys()):
        if key in known:
            continue

        rows.append(("Detail aman: {}".format(key), safe.get(key, "-")))
        extra_count += 1

        if extra_count >= 18:
            break

    return _gland_clear_send_email(
        _gland_clear_security_recipients(),
        subject,
        "Security Alert: {}".format(details.get("label", "Aktivitas Keamanan Admin")),
        rows,
        intro,
    )


def send_gland_admin_change_alert(event_name="admin_change_event", payload=None):
    payload = _gland_clear_enrich_payload(payload or {})
    safe = _gland_clear_safe_payload(payload)
    event_name = str(event_name or _gland_clear_extract_event_name(payload) or "admin_change_event")

    admin_identity = (
        safe.get("identifier")
        or safe.get("username")
        or safe.get("email")
        or safe.get("admin_email")
        or "-"
    )

    rows = [
        ("Jenis alert", "Perubahan CMS Admin"),
        ("Status kejadian", safe.get("status", safe.get("success", "INFO"))),
        ("Event teknis", event_name),
        ("Admin", admin_identity),
        ("Email admin", safe.get("email", safe.get("admin_email", "-"))),
        ("Target", safe.get("target", safe.get("resource", safe.get("table", "-")))),
        ("Action", safe.get("action", event_name)),
        ("Waktu", safe.get("time", safe.get("created_at", "-"))),
        ("IP address", safe.get("ip_address", safe.get("ip", safe.get("remote_addr", "-")))),
        ("Lokasi jaringan", safe.get("ip_location", "-")),
        ("Jenis perangkat", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Sistem operasi", safe.get("operating_system", "-")),
        ("Request path", safe.get("request_path", safe.get("path", "-"))),
        ("User agent", safe.get("user_agent", safe.get("userAgent", "-"))),
    ]

    return _gland_clear_send_email(
        _gland_clear_change_recipients(),
        "GLAND Admin Change Alert: {} | {}".format(event_name, admin_identity),
        "Admin Change Alert",
        rows,
        "Sistem mencatat perubahan pada CMS admin.",
    )


def _gland_clear_wrap_alert_sender(fn):
    def _wrapped(*args, **kwargs):
        payload = _gland_clear_collect_payload(*args, **kwargs)
        event_name = _gland_clear_extract_event_name(payload)
        category = _gland_clear_category(event_name, payload)

        if category == "security":
            return send_gland_security_alert(event_name, payload)

        if category == "change":
            return send_gland_admin_change_alert(event_name, payload)

        return fn(*args, **kwargs)

    _wrapped._gland_clear_security_wrapped = True
    _wrapped.__name__ = getattr(fn, "__name__", "_wrapped")
    return _wrapped


_gland_clear_explicit_wrap_names = {
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
}

for _gland_clear_name, _gland_clear_candidate in list(globals().items()):
    if not callable(_gland_clear_candidate):
        continue

    if getattr(_gland_clear_candidate, "_gland_clear_security_wrapped", False):
        continue

    lower_name = str(_gland_clear_name).lower()

    if lower_name in {
        "send_admin_login_verification_email",
        "send_gland_security_alert",
        "send_gland_admin_change_alert",
        "send_gland_contact_alert",
        "send_gland_contact_message_alert",
    }:
        continue

    should_wrap = _gland_clear_name in _gland_clear_explicit_wrap_names

    if not should_wrap:
        should_wrap = (
            lower_name.startswith("send_")
            and (
                "admin" in lower_name
                or "login" in lower_name
                or "auth" in lower_name
                or "security" in lower_name
                or "activity" in lower_name
            )
            and (
                "alert" in lower_name
                or "notification" in lower_name
                or "activity" in lower_name
            )
        )

    if should_wrap:
        globals()[_gland_clear_name] = _gland_clear_wrap_alert_sender(_gland_clear_candidate)
# GLAND CLEAR SECURITY ALERT V2 END
