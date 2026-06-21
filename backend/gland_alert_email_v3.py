from __future__ import annotations

import datetime as _dt
import html as _html
import re as _re
import smtplib as _smtplib
import ssl as _ssl
from email.message import EmailMessage as _EmailMessage
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote as _url_quote

PERSONAL_EMAIL = "glandjermanoblessedsiahaan@gmail.com"
OFFICIAL_EMAIL = "official.arcdev@gmail.com"


def _cfg(name: str, default: Any = None) -> Any:
    try:
        import config
        return getattr(config, name, default)
    except Exception:
        return default


def _normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = _re.split(r"[;,]", str(value))

    result = []
    seen = set()

    for item in items:
        email = _normalize_email(item)

        if not email or email in seen:
            continue

        seen.add(email)
        result.append(email)

    return result


def _unique(values: Iterable[str]) -> List[str]:
    result = []
    seen = set()

    for value in values:
        email = _normalize_email(value)

        if not email or email in seen:
            continue

        seen.add(email)
        result.append(email)

    return result


def _security_default() -> List[str]:
    configured = _as_list(_cfg("SECURITY_ALERT_EMAILS", []))
    return configured or [OFFICIAL_EMAIL]


def _login_security_default() -> List[str]:
    configured = _as_list(_cfg("LOGIN_SECURITY_ALERT_EMAILS", []))
    return configured or [PERSONAL_EMAIL, OFFICIAL_EMAIL]


def _admin_change_default() -> List[str]:
    configured = _as_list(_cfg("ADMIN_CHANGE_ALERT_EMAILS", []))
    return configured or [OFFICIAL_EMAIL]


def _contact_default() -> List[str]:
    configured = _as_list(_cfg("CONTACT_ALERT_EMAILS", []))
    return configured or [PERSONAL_EMAIL, OFFICIAL_EMAIL]


def _html_escape(value: Any) -> str:
    return _html.escape(str(value if value is not None else "-"), quote=True)


def _trim(value: Any, limit: int = 900) -> str:
    text = str(value if value is not None else "-")

    if len(text) > limit:
        return text[:limit] + "... [dipotong]"

    return text


def _pretty_text(value: Any) -> str:
    text = str(value if value is not None else "").strip()

    if not text:
        return "-"

    text = text.replace("_", " ").replace("-", " ").replace("/", " / ")
    text = _re.sub(r"\s+", " ", text).strip()

    known = {
        "otp": "OTP",
        "ip": "IP",
        "url": "URL",
        "cms": "CMS",
        "api": "API",
        "id": "ID",
    }

    words = []

    for word in text.split(" "):
        lower = word.lower()
        words.append(known.get(lower, word.capitalize()))

    return " ".join(words)


def _safe_key(key: Any) -> bool:
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


def _safe_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    safe = {}

    for key, value in dict(payload or {}).items():
        key_text = str(key)

        if not _safe_key(key_text):
            safe[key_text] = "[dirahasiakan]"
        else:
            safe[key_text] = _trim(value)

    return safe


def collect_payload(*args: Any, **kwargs: Any) -> Dict[str, Any]:
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


def collect_contact_payload(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    payload = collect_payload(*args, **kwargs)

    if len(args) >= 4 and not isinstance(args[0], dict):
        payload.setdefault("name", args[0])
        payload.setdefault("email", args[1])
        payload.setdefault("subject", args[2])
        payload.setdefault("message", args[3])

    return payload


def extract_event_name(payload: Dict[str, Any]) -> str:
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
        value = str((payload or {}).get(key) or "").strip()

        if value:
            return value

    return "admin_activity"


def _bool_status(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"1", "true", "yes", "y", "success", "successful", "ok", "berhasil"}:
        return "success"

    if text in {"0", "false", "no", "n", "failed", "fail", "error", "denied", "invalid", "gagal"}:
        return "failed"

    return ""


def _now_text() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _request_metadata() -> Dict[str, Any]:
    metadata = {}

    try:
        from flask import has_request_context, request

        if has_request_context():
            forwarded_for = request.headers.get("X-Forwarded-For", "")
            ip_address = (forwarded_for.split(",")[0].strip() if forwarded_for else "") or request.remote_addr or ""

            metadata.update({
                "ip_address": ip_address,
                "user_agent": request.headers.get("User-Agent", ""),
                "request_path": request.path,
                "request_method": request.method,
            })
    except Exception:
        pass

    return metadata


def _parse_user_agent(user_agent: Any) -> Dict[str, str]:
    text = str(user_agent or "")
    lower = text.lower()

    device_type = "Desktop"
    browser = "Browser tidak terdeteksi"
    os_name = "Sistem operasi tidak terdeteksi"

    if "android" in lower:
        os_name = "Android"
    elif "iphone" in lower:
        os_name = "iOS iPhone"
    elif "ipad" in lower:
        os_name = "iPadOS"
    elif "windows nt 10" in lower:
        os_name = "Windows 10 atau Windows 11"
    elif "windows" in lower:
        os_name = "Windows"
    elif "mac os x" in lower or "macintosh" in lower:
        os_name = "macOS"
    elif "linux" in lower:
        os_name = "Linux"

    if "edg/" in lower or "edga/" in lower:
        browser = "Microsoft Edge"
    elif "opr/" in lower or "opera" in lower:
        browser = "Opera"
    elif "chrome/" in lower or "crios/" in lower:
        browser = "Google Chrome"
    elif "firefox/" in lower or "fxios/" in lower:
        browser = "Mozilla Firefox"
    elif "safari/" in lower:
        browser = "Safari"

    if "ipad" in lower or "tablet" in lower:
        device_type = "Tablet"
    elif "mobile" in lower or "android" in lower or "iphone" in lower:
        device_type = "Mobile"

    return {
        "device_type": device_type,
        "browser": browser,
        "operating_system": os_name,
    }


def _ip_location(ip_address: Any) -> Dict[str, str]:
    ip_text = str(ip_address or "").strip()

    is_private = (
        not ip_text
        or ip_text in {"127.0.0.1", "::1", "localhost"}
        or ip_text.startswith("192.168.")
        or ip_text.startswith("10.")
        or any(ip_text.startswith("172.{}.".format(number)) for number in range(16, 32))
    )

    if is_private:
        return {
            "ip_location": "Localhost atau private network. Lokasi publik tidak tersedia.",
            "network_org": "Private network",
            "timezone": "-",
            "coordinates": "-",
        }

    if not bool(_cfg("IP_GEOLOCATION_ENABLED", False)):
        return {
            "ip_location": "Lookup lokasi IP publik belum diaktifkan.",
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }

    try:
        import json as _json
        import urllib.request as _urlrequest

        token = str(_cfg("IPINFO_TOKEN", "") or "").strip()
        url = "https://ipinfo.io/{}/json".format(_url_quote(ip_text))

        if token:
            url += "?token={}".format(_url_quote(token))

        with _urlrequest.urlopen(url, timeout=5) as response:
            data = _json.loads(response.read().decode("utf-8"))

        city = data.get("city") or "-"
        region = data.get("region") or "-"
        country = data.get("country") or "-"
        location = ", ".join([item for item in [city, region, country] if item and item != "-"])

        return {
            "ip_location": location or "-",
            "network_org": data.get("org") or "-",
            "timezone": data.get("timezone") or "-",
            "coordinates": data.get("loc") or "-",
        }
    except Exception as error:
        return {
            "ip_location": "Lookup lokasi IP gagal: {}".format(error),
            "network_org": "-",
            "timezone": "-",
            "coordinates": "-",
        }


def _enrich_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(payload or {})

    for key, value in _request_metadata().items():
        enriched.setdefault(key, value)

    enriched.setdefault("time", _now_text())

    user_agent = enriched.get("user_agent") or enriched.get("userAgent") or ""
    ip_address = enriched.get("ip_address") or enriched.get("ip") or enriched.get("remote_addr") or ""

    for key, value in _parse_user_agent(user_agent).items():
        enriched.setdefault(key, value)

    for key, value in _ip_location(ip_address).items():
        enriched.setdefault(key, value)

    if ip_address:
        enriched.setdefault("ip_address", ip_address)

    if user_agent:
        enriched.setdefault("user_agent", user_agent)

    return enriched


def _event_text(event_name: Any, payload: Dict[str, Any]) -> str:
    return (str(event_name or "") + " " + repr(payload or {})).lower()


def _is_login_security_event(event_name: Any, payload: Dict[str, Any]) -> bool:
    text = _event_text(event_name, payload)

    if "password_reset" in text or "reset_password" in text or "change_password" in text:
        return False

    keywords = [
        "login",
        "log in",
        "signin",
        "sign in",
        "logout",
        "log out",
        "signout",
        "sign out",
        "otp",
        "verification",
        "auth_failed",
        "invalid_password",
        "invalid credential",
        "session_created",
        "session_revoked",
        "session_expired",
    ]

    return any(keyword in text for keyword in keywords)


def _login_account_email(payload: Dict[str, Any]) -> str:
    payload = dict(payload or {})
    admin = payload.get("admin")

    if isinstance(admin, dict):
        for key in ["email", "admin_email", "identifier"]:
            email = _normalize_email(admin.get(key))

            if "@" in email:
                return email

    for key in ["email", "admin_email", "identifier", "username_or_email", "login_email", "target_email"]:
        email = _normalize_email(payload.get(key))

        if "@" in email:
            return email

    username = _normalize_email(
        payload.get("username")
        or payload.get("admin_username")
        or payload.get("identifier")
        or payload.get("user")
    )

    username_map = {
        "admin": PERSONAL_EMAIL,
        "gland": PERSONAL_EMAIL,
        "glandjermano": PERSONAL_EMAIL,
        "arcdev": OFFICIAL_EMAIL,
    }

    return username_map.get(username, "")


def _security_recipients_for_event(event_name: Any, payload: Dict[str, Any]) -> List[str]:
    if not _is_login_security_event(event_name, payload):
        return _unique(_security_default())

    login_email = _login_account_email(payload)

    if login_email == PERSONAL_EMAIL:
        return _unique(_login_security_default())

    return _unique([OFFICIAL_EMAIL])


def _admin_change_recipients() -> List[str]:
    return _unique(_admin_change_default())


def _contact_recipients() -> List[str]:
    return _unique(_contact_default())


def classify_alert_category(event_name: Any, payload: Dict[str, Any]) -> str:
    text = _event_text(event_name, payload)

    if _is_login_security_event(event_name, payload):
        return "security"

    if any(keyword in text for keyword in ["security", "session", "password", "reset", "auth", "failed"]):
        return "security"

    if any(keyword in text for keyword in [
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
    ]):
        return "change"

    return "other"


def _event_details(event_name: Any, payload: Dict[str, Any]) -> Dict[str, str]:
    text = _event_text(event_name, payload)
    explicit_status = (
        _bool_status((payload or {}).get("success"))
        or _bool_status((payload or {}).get("status"))
        or _bool_status((payload or {}).get("result"))
    )

    details = {
        "label": "Aktivitas Keamanan Admin",
        "subject_label": "Aktivitas Keamanan Admin",
        "status_code": explicit_status or "info",
        "status_text": "Info",
        "stage": "Sistem mencatat aktivitas keamanan pada area admin.",
        "meaning": "Periksa detail perangkat, IP, dan akun yang tercatat.",
        "impact": "Tidak ada tindakan otomatis selain pencatatan dan pengiriman alert.",
        "severity": "Normal",
        "theme": "info",
    }

    if "login_verification_sent" in text or "verification_sent" in text or "otp_sent" in text or "code_sent" in text:
        details.update({
            "label": "Kode OTP Login Dikirim",
            "subject_label": "OTP Dikirim, Login Belum Selesai",
            "status_code": "info",
            "status_text": "Info",
            "stage": "Email dan password sudah benar. Sistem mengirim kode OTP.",
            "meaning": "Login belum selesai. Dashboard baru bisa dibuka setelah OTP yang valid dimasukkan.",
            "impact": "Session admin final belum dibuat pada tahap ini.",
            "severity": "Normal",
            "theme": "info",
        })
    elif "login_verification_success" in text or "verification_success" in text or "otp_success" in text:
        details.update({
            "label": "OTP Login Benar",
            "subject_label": "OTP Benar",
            "status_code": "success",
            "status_text": "Berhasil",
            "stage": "Kode OTP yang dimasukkan valid.",
            "meaning": "Sistem menerima OTP dan dapat melanjutkan proses login.",
            "impact": "Session admin dapat dibuat setelah verifikasi ini.",
            "severity": "Normal",
            "theme": "success",
        })
    elif "login_verification_failed" in text or "verification_failed" in text or "otp_failed" in text or "invalid_otp" in text or "wrong_otp" in text:
        details.update({
            "label": "OTP Login Gagal",
            "subject_label": "OTP Salah atau Gagal",
            "status_code": "failed",
            "status_text": "Gagal",
            "stage": "Kode OTP yang dimasukkan tidak valid.",
            "meaning": "OTP salah, kedaluwarsa, sudah dipakai, atau melewati batas percobaan.",
            "impact": "Login ditolak. Session admin tidak dibuat dari percobaan ini.",
            "severity": "Tinggi",
            "theme": "danger",
        })
    elif "login_success" in text or "signin_success" in text or "sign_in_success" in text:
        details.update({
            "label": "Login Berhasil",
            "subject_label": "Login Berhasil, Session Dibuat",
            "status_code": "success",
            "status_text": "Berhasil",
            "stage": "Login final berhasil.",
            "meaning": "Akun admin berhasil masuk setelah proses autentikasi selesai.",
            "impact": "Session admin aktif dibuat untuk perangkat ini.",
            "severity": "Normal",
            "theme": "success",
        })
    elif "login_failed" in text or "signin_failed" in text or "sign_in_failed" in text or "invalid_password" in text or "auth_failed" in text:
        details.update({
            "label": "Login Gagal",
            "subject_label": "Login Gagal",
            "status_code": "failed",
            "status_text": "Gagal",
            "stage": "Pemeriksaan email, username, atau password gagal.",
            "meaning": "Ada percobaan masuk yang tidak memenuhi syarat login.",
            "impact": "Login ditolak. Session admin tidak dibuat.",
            "severity": "Tinggi",
            "theme": "danger",
        })
    elif "logout" in text or "signout" in text or "sign_out" in text:
        details.update({
            "label": "Logout Admin",
            "subject_label": "Logout Admin",
            "status_code": explicit_status or "success",
            "status_text": "Berhasil",
            "stage": "Admin keluar dari dashboard.",
            "meaning": "Session admin pada perangkat tersebut diakhiri.",
            "impact": "Akses dashboard pada session itu berhenti.",
            "severity": "Normal",
            "theme": "neutral",
        })
    elif "session_expired" in text or "session_invalid" in text or "session_revoked" in text:
        details.update({
            "label": "Session Admin Ditolak",
            "subject_label": "Session Admin Ditolak",
            "status_code": "failed",
            "status_text": "Gagal",
            "stage": "Validasi session gagal.",
            "meaning": "Session hilang, kedaluwarsa, atau dicabut.",
            "impact": "Akses dashboard ditolak sampai admin login ulang.",
            "severity": "Tinggi",
            "theme": "danger",
        })

    if details["status_code"] == "failed":
        details["status_text"] = "Gagal"
        details["theme"] = "danger"
    elif details["status_code"] == "success":
        details["status_text"] = "Berhasil"

    return details


def _theme(theme: str) -> Dict[str, str]:
    themes = {
        "success": {"bar": "#16a34a", "label_bg": "#ecfdf5", "label_fg": "#166534", "accent": "#16a34a"},
        "danger": {"bar": "#dc2626", "label_bg": "#fef2f2", "label_fg": "#991b1b", "accent": "#dc2626"},
        "info": {"bar": "#2563eb", "label_bg": "#eff6ff", "label_fg": "#1e40af", "accent": "#2563eb"},
        "contact": {"bar": "#84cc16", "label_bg": "#f7fee7", "label_fg": "#3f6212", "accent": "#65a30d"},
        "neutral": {"bar": "#64748b", "label_bg": "#f8fafc", "label_fg": "#334155", "accent": "#334155"},
    }

    return themes.get(theme, themes["info"])


def _build_rows_html(rows: List[Tuple[str, Any]]) -> str:
    return "\n".join([
        '<tr>'
        '<td style="width:220px;padding:13px 14px;border-bottom:1px solid #d8dee8;background:#f8fafc;color:#334155;font-size:13px;font-weight:800;vertical-align:top;">{}</td>'
        '<td style="padding:13px 14px;border-bottom:1px solid #d8dee8;color:#0f172a;font-size:14px;line-height:1.65;white-space:pre-wrap;vertical-align:top;">{}</td>'
        '</tr>'.format(_html_escape(label), _html_escape(value))
        for label, value in rows
    ])


def _build_email_html(
    title: str,
    intro: str,
    rows: List[Tuple[str, Any]],
    theme: str = "info",
    cta_label: str = "",
    cta_url: str = "",
    footer_note: str = "",
) -> str:
    palette = _theme(theme)
    cta_html = ""

    if cta_label and cta_url:
        cta_html = '''
        <div style="margin:22px 0 2px;">
          <a href="{url}" style="display:inline-block;background:{bg};color:#ffffff;text-decoration:none;padding:13px 18px;border-radius:0;font-size:14px;font-weight:900;letter-spacing:.01em;">
            {label}
          </a>
        </div>
        '''.format(
            url=_html_escape(cta_url),
            bg=_html_escape(palette["accent"]),
            label=_html_escape(cta_label),
        )

    if not footer_note:
        footer_note = "Email ini dibuat otomatis oleh GLAND Portfolio CMS. Password, token, session, dan kode OTP tidak ditampilkan di alert ini."

    return """<!doctype html>
<html>
  <body style="margin:0;background:#e5e7eb;padding:24px;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:820px;margin:0 auto;background:#ffffff;border:1px solid #cbd5e1;border-radius:0;overflow:hidden;">
      <div style="height:6px;background:{bar};line-height:6px;">&nbsp;</div>
      <div style="padding:24px 24px 20px;background:#0f172a;color:#ffffff;border-radius:0;">
        <div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#a3e635;font-weight:900;">GLAND Portfolio CMS</div>
        <h1 style="margin:10px 0 0;font-size:24px;line-height:1.35;font-weight:900;">{title}</h1>
      </div>
      <div style="padding:24px;">
        <div style="display:inline-block;background:{label_bg};color:{label_fg};padding:7px 10px;border-radius:0;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px;">
          Security Notice
        </div>
        <p style="margin:0 0 18px;color:#334155;font-size:15px;line-height:1.75;">{intro}</p>
        <table role="presentation" style="width:100%;border-collapse:collapse;border:1px solid #d8dee8;border-radius:0;">
          {rows}
        </table>
        {cta}
        <p style="margin:20px 0 0;color:#64748b;font-size:12px;line-height:1.6;">{footer}</p>
      </div>
    </div>
  </body>
</html>""".format(
        bar=_html_escape(palette["bar"]),
        title=_html_escape(title),
        label_bg=_html_escape(palette["label_bg"]),
        label_fg=_html_escape(palette["label_fg"]),
        intro=_html_escape(intro),
        rows=_build_rows_html(rows),
        cta=cta_html,
        footer=_html_escape(footer_note),
    )


def _send_email(
    recipients: List[str],
    subject: str,
    title: str,
    intro: str,
    rows: List[Tuple[str, Any]],
    theme: str = "info",
    cta_label: str = "",
    cta_url: str = "",
    footer_note: str = "",
    extra_headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    recipients = _unique(recipients)

    if not recipients:
        return {"sent": False, "skipped": True, "error": "No recipients configured.", "recipients": []}

    smtp_host = str(_cfg("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
    smtp_port = int(_cfg("SMTP_PORT", 587) or 587)
    smtp_username = str(_cfg("SMTP_USERNAME", "") or "").strip()
    smtp_password = str(_cfg("SMTP_APP_PASSWORD", "") or _cfg("SMTP_PASSWORD", "") or "").strip()
    from_email = str(_cfg("SMTP_FROM_EMAIL", "") or smtp_username or "").strip()
    from_name = str(_cfg("SMTP_FROM_NAME", "GLAND Portfolio CMS") or "GLAND Portfolio CMS").strip()

    if not smtp_username or not smtp_password:
        return {"sent": False, "skipped": False, "error": "SMTP username or password is missing.", "recipients": recipients}

    if not from_email:
        from_email = smtp_username

    plain_lines = [title, "", intro, ""]

    for label, value in rows:
        plain_lines.append("{} : {}".format(label, value))

    message = _EmailMessage()
    message["Subject"] = subject
    message["From"] = "{} <{}>".format(from_name, from_email) if from_name else from_email
    message["To"] = ", ".join(recipients)
    message["Reply-To"] = from_email

    for key, value in (extra_headers or {}).items():
        message[key] = value

    message.set_content("\n".join(plain_lines))
    message.add_alternative(
        _build_email_html(
            title=title,
            intro=intro,
            rows=rows,
            theme=theme,
            cta_label=cta_label,
            cta_url=cta_url,
            footer_note=footer_note,
        ),
        subtype="html",
    )

    try:
        if smtp_port == 465:
            context = _ssl.create_default_context()

            with _smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=context) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with _smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=_ssl.create_default_context())
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(message)

        return {"sent": True, "skipped": False, "error": "", "recipients": recipients, "subject": subject}
    except Exception as error:
        return {"sent": False, "skipped": False, "error": str(error), "recipients": recipients, "subject": subject}


def _secure_account_url() -> str:
    return str(
        _cfg("ADMIN_SECURITY_URL", "")
        or _cfg("ADMIN_LOGIN_URL", "")
        or "http://127.0.0.1:8000/admin/login.html"
    ).strip()


def send_security_alert(event_name: str = "admin_security_event", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = _enrich_payload(payload or {})
    event_name = str(event_name or extract_event_name(payload) or "admin_security_event")
    safe = _safe_payload(payload)
    details = _event_details(event_name, payload)

    identifier = safe.get("identifier") or safe.get("username") or safe.get("email") or safe.get("admin_email") or "-"

    subject = "GLAND Security Alert: {} | {}".format(details.get("subject_label") or details.get("label"), identifier)
    intro = "{}. Status: {}. {}".format(details.get("label"), details.get("status_text"), details.get("meaning"))

    rows = [
        ("Jenis alert", details.get("label", "-")),
        ("Status kejadian", details.get("status_text", "-")),
        ("Event teknis", _pretty_text(event_name)),
        ("Tahap proses", details.get("stage", "-")),
        ("Arti kejadian", details.get("meaning", "-")),
        ("Dampak keamanan", details.get("impact", "-")),
        ("Tingkat risiko", details.get("severity", "Normal")),
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
        "event", "event_name", "event_type", "activity", "action", "type", "name", "title", "subject",
        "success", "status", "result", "identifier", "username", "admin_username", "email", "admin_email",
        "time", "created_at", "ip", "ip_address", "remote_addr", "ip_location", "network_org", "timezone",
        "coordinates", "device_type", "browser", "operating_system", "request_method", "method",
        "request_path", "path", "user_agent", "userAgent",
    }

    extra_count = 0

    for key in sorted(safe.keys()):
        if key in known:
            continue

        rows.append(("Detail tambahan: {}".format(_pretty_text(key)), safe.get(key, "-")))
        extra_count += 1

        if extra_count >= 14:
            break

    cta_label = ""
    cta_url = ""

    if details.get("status_code") == "failed" or details.get("severity") == "Tinggi":
        cta_label = "Amankan Akun Sekarang"
        cta_url = _secure_account_url()

    return _send_email(
        _security_recipients_for_event(event_name, payload),
        subject,
        "Security Alert: {}".format(details.get("label", "Aktivitas Keamanan Admin")),
        intro,
        rows,
        theme=details.get("theme", "info"),
        cta_label=cta_label,
        cta_url=cta_url,
        footer_note="Segera cek akun bila aktivitas ini tidak kamu kenal. Password, token, session, dan kode OTP tidak ditampilkan di email alert ini.",
        extra_headers={"X-GLAND-Alert-Type": "security"},
    )


def send_admin_change_alert(event_name: str = "admin_change_event", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = _enrich_payload(payload or {})
    event_name = str(event_name or extract_event_name(payload) or "admin_change_event")
    safe = _safe_payload(payload)

    admin_identity = safe.get("identifier") or safe.get("username") or safe.get("email") or safe.get("admin_email") or "-"

    rows = [
        ("Jenis alert", "Perubahan CMS Admin"),
        ("Status kejadian", _pretty_text(safe.get("status", safe.get("success", "Info")))),
        ("Event teknis", _pretty_text(event_name)),
        ("Admin", admin_identity),
        ("Email admin", safe.get("email", safe.get("admin_email", "-"))),
        ("Target", _pretty_text(safe.get("target", safe.get("resource", safe.get("table", "-"))))),
        ("Action", _pretty_text(safe.get("action", event_name))),
        ("Waktu", safe.get("time", safe.get("created_at", "-"))),
        ("IP address", safe.get("ip_address", safe.get("ip", safe.get("remote_addr", "-")))),
        ("Lokasi jaringan", safe.get("ip_location", "-")),
        ("Provider jaringan", safe.get("network_org", "-")),
        ("Jenis perangkat", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Sistem operasi", safe.get("operating_system", "-")),
        ("Request path", safe.get("request_path", safe.get("path", "-"))),
        ("User agent", safe.get("user_agent", safe.get("userAgent", "-"))),
    ]

    return _send_email(
        _admin_change_recipients(),
        "GLAND Admin Change Alert: {} | {}".format(_pretty_text(event_name), admin_identity),
        "Admin Change Alert",
        "Sistem mencatat perubahan pada CMS admin. Alert jenis ini hanya dikirim ke akun monitoring utama.",
        rows,
        theme="info",
        extra_headers={"X-GLAND-Alert-Type": "admin-change"},
    )


def send_contact_alert(payload: Optional[Dict[str, Any]] = None, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        data = dict(payload)
        data.update(kwargs or {})
    else:
        values = []

        if payload is not None:
            values.append(payload)

        values.extend(args)
        data = collect_contact_payload(*values, **kwargs)

    data = _enrich_payload(data)
    safe = _safe_payload(data)
    subject_text = safe.get("subject", safe.get("name", "Pesan contact baru"))

    rows = [
        ("Waktu", safe.get("time", "-")),
        ("Nama", safe.get("name", "-")),
        ("Email pengirim", safe.get("email", "-")),
        ("Nomor telepon", safe.get("phone", safe.get("telephone", "-"))),
        ("Subjek", safe.get("subject", "-")),
        ("Pesan", safe.get("message", safe.get("content", "-"))),
        ("IP address", safe.get("ip_address", "-")),
        ("Lokasi jaringan", safe.get("ip_location", "-")),
        ("Provider jaringan", safe.get("network_org", "-")),
        ("Jenis perangkat", safe.get("device_type", "-")),
        ("Browser", safe.get("browser", "-")),
        ("Sistem operasi", safe.get("operating_system", "-")),
        ("User agent", safe.get("user_agent", "-")),
    ]

    return _send_email(
        _contact_recipients(),
        "GLAND Contact Message: {}".format(subject_text),
        "Pesan Contact Baru",
        "Ada pesan baru dari form contact frontend.",
        rows,
        theme="contact",
        extra_headers={"X-GLAND-Alert-Type": "contact"},
    )


def _build_otp_html(code: str, admin: Dict[str, Any], expires_at: str, ip_address: str, user_agent: str) -> str:
    copy_href = "data:text/plain;charset=utf-8,{}".format(_url_quote(code))
    login_url = str(_cfg("ADMIN_LOGIN_URL", "http://127.0.0.1:8000/admin/login.html") or "http://127.0.0.1:8000/admin/login.html").strip()

    rows = [
        ("Akun login", admin.get("email") or "-"),
        ("Username", admin.get("username") or "-"),
        ("Berlaku sampai", expires_at),
        ("IP address", ip_address),
        ("User agent", user_agent),
    ]

    return """<!doctype html>
<html>
  <body style="margin:0;background:#e5e7eb;padding:24px;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #cbd5e1;border-radius:0;overflow:hidden;">
      <div style="height:6px;background:#2563eb;line-height:6px;">&nbsp;</div>
      <div style="background:#0f172a;color:#ffffff;padding:24px;border-radius:0;">
        <div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#a3e635;font-weight:900;">GLAND Portfolio CMS</div>
        <h1 style="margin:10px 0 0;font-size:24px;line-height:1.35;font-weight:900;">Kode OTP Login Admin</h1>
      </div>
      <div style="padding:24px;">
        <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.75;">
          Email dan password sudah benar. Masukkan kode berikut untuk menyelesaikan login admin.
        </p>
        <div style="border:2px solid #0f172a;background:#f8fafc;padding:22px;text-align:center;margin:18px 0 12px;border-radius:0;">
          <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#64748b;font-weight:900;margin-bottom:10px;">Kode OTP</div>
          <div style="font-size:40px;letter-spacing:10px;color:#0f172a;font-weight:900;line-height:1.2;user-select:all;">{code}</div>
        </div>
        <div style="margin:16px 0 24px;">
          <a href="{copy_href}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:999px;font-size:14px;font-weight:900;margin-right:8px;">
            Salin kode
          </a>
          <a href="{login_url}" style="display:inline-block;background:#0f172a;color:#ffffff;text-decoration:none;padding:12px 18px;border-radius:0;font-size:14px;font-weight:900;">
            Buka halaman login
          </a>
        </div>
        <table role="presentation" style="width:100%;border-collapse:collapse;border:1px solid #d8dee8;border-radius:0;">
          {rows}
        </table>
        <p style="margin:18px 0 0;color:#64748b;font-size:12px;line-height:1.6;">
          Jangan bagikan kode ini kepada siapa pun. Jika kamu tidak mencoba login, segera amankan akun admin.
        </p>
      </div>
    </div>
  </body>
</html>""".format(
        code=_html_escape(code),
        copy_href=_html_escape(copy_href),
        login_url=_html_escape(login_url),
        rows=_build_rows_html(rows),
    )


def send_login_otp_email(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = payload or {}
    admin = payload.get("admin") or {}

    code = str(payload.get("code") or "").strip()
    expires_at = str(payload.get("expires_at") or "-")
    ip_address = str(payload.get("ip_address") or "-")
    user_agent = str(payload.get("user_agent") or "-")
    to_email = _normalize_email(admin.get("email"))

    if not to_email:
        return {"sent": False, "skipped": True, "error": "Admin account does not have an email address.", "recipient": ""}

    if not code:
        return {"sent": False, "skipped": True, "error": "Missing verification code.", "recipient": to_email}

    if not bool(_cfg("SMTP_ENABLED", True)):
        return {"sent": False, "skipped": True, "error": "SMTP is disabled.", "recipient": to_email}

    smtp_host = str(_cfg("SMTP_HOST", "smtp.gmail.com") or "smtp.gmail.com").strip()
    smtp_port = int(_cfg("SMTP_PORT", 587) or 587)
    smtp_username = str(_cfg("SMTP_USERNAME", "") or "").strip()
    smtp_password = str(_cfg("SMTP_APP_PASSWORD", "") or _cfg("SMTP_PASSWORD", "") or "").strip()
    from_email = str(_cfg("SMTP_FROM_EMAIL", "") or smtp_username or "").strip()
    from_name = str(_cfg("SMTP_FROM_NAME", "GLAND Portfolio CMS") or "GLAND Portfolio CMS").strip()

    if not smtp_username or not smtp_password:
        return {"sent": False, "skipped": False, "error": "SMTP username or password is missing.", "recipient": to_email}

    if not from_email:
        from_email = smtp_username

    subject = "GLAND OTP Login Admin: {} | {}".format(code, to_email)

    plain = "\n".join([
        "Kode OTP Login GLAND",
        "",
        "Kode OTP: {}".format(code),
        "",
        "Akun login      : {}".format(admin.get("email") or "-"),
        "Username        : {}".format(admin.get("username") or "-"),
        "Berlaku sampai  : {}".format(expires_at),
        "IP address      : {}".format(ip_address),
        "",
        "Masukkan kode ini pada halaman login admin.",
        "Jangan bagikan kode ini kepada siapa pun.",
        "",
        "User agent:",
        user_agent,
    ])

    message = _EmailMessage()
    message["Subject"] = subject
    message["From"] = "{} <{}>".format(from_name, from_email) if from_name else from_email
    message["To"] = to_email
    message["Reply-To"] = from_email
    message["X-GLAND-OTP-Recipient"] = to_email
    message.set_content(plain)
    message.add_alternative(_build_otp_html(code, admin, expires_at, ip_address, user_agent), subtype="html")

    try:
        if smtp_port == 465:
            context = _ssl.create_default_context()

            with _smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=context) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with _smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.ehlo()
                server.starttls(context=_ssl.create_default_context())
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(message)

        return {
            "sent": True,
            "skipped": False,
            "error": "",
            "message": "OTP email sent only to login account email: {}".format(to_email),
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


def send_admin_login_verification_email(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return send_login_otp_email(payload)