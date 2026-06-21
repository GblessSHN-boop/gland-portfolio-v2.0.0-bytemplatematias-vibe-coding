# GLAND Portfolio Admin CMS - Example Configuration
# Copy this file to config.py and adjust values for your local environment.

APP_NAME = "GLAND Portfolio Admin"
APP_HOST = "127.0.0.1"
APP_PORT = 8000
APP_DEBUG = True

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "gland_portfolio_db"

ADMIN_DEFAULT_USERNAME = "admin"
ADMIN_DEFAULT_EMAIL = "glandjermanoblessedsiahaan@gmail.com"

UPLOAD_IMAGE_DIR = "uploads/images"
UPLOAD_VIDEO_DIR = "uploads/videos"

# GLAND SMTP EMAIL ALERT CONFIG START
# Use Gmail App Password, not your normal Gmail password.
SMTP_ENABLED = False
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_APP_PASSWORD = ""
SMTP_FROM_EMAIL = "your-email@gmail.com"
SMTP_TIMEOUT_SECONDS = 10

ADMIN_ALERT_EMAIL = "your-email@gmail.com"
ADMIN_ALERT_LOGIN_SUCCESS = True
ADMIN_ALERT_LOGIN_FAILED = True
ADMIN_ALERT_LOGOUT = True
# GLAND SMTP EMAIL ALERT CONFIG END

# GLAND PASSWORD RESET CONFIG START
PASSWORD_RESET_TOKEN_MINUTES = 30
PASSWORD_RESET_BASE_URL = "http://127.0.0.1:8000"
PASSWORD_RESET_DEBUG_RETURN_TOKEN = False
# GLAND PASSWORD RESET CONFIG END
# GLAND PASSWORD RESET THROTTLE CONFIG START
PASSWORD_RESET_REQUEST_COOLDOWN_SECONDS = 90
# GLAND PASSWORD RESET THROTTLE CONFIG END
# Contact form alert email
CONTACT_ALERTS_ENABLED = True
# Admin login 6-digit verification
LOGIN_VERIFICATION_CODE_MINUTES = 10
LOGIN_VERIFICATION_MAX_ATTEMPTS = 5
LOGIN_VERIFICATION_DEBUG_RETURN_CODE = False

# GLAND ACTIVITY LOG CONFIG START
ACTIVITY_LOG_RETENTION_DAYS = 180
ACTIVITY_LOG_AUTO_REFRESH_SECONDS = 5
# GLAND ACTIVITY LOG CONFIG END

# GLAND ALERT RECIPIENT ROUTING V3 START
# Personal inbox only receives frontend contact messages and login alerts for the personal admin account.
LOGIN_SECURITY_ALERT_EMAILS = [
    "personal@example.com",
    "monitoring@example.com",
]

# Non-login security alerts only go to the monitoring inbox.
SECURITY_ALERT_EMAILS = [
    "monitoring@example.com",
]

# CMS change alerts only go to the monitoring inbox.
ADMIN_CHANGE_ALERT_EMAILS = [
    "monitoring@example.com",
]

# Frontend contact messages go to both inboxes.
CONTACT_ALERT_EMAILS = [
    "personal@example.com",
    "monitoring@example.com",
]

SMTP_FROM_NAME = "GLAND Portfolio CMS"
ADMIN_LOGIN_URL = "https://example.com/admin/login.html"
ADMIN_SECURITY_URL = "https://example.com/admin/login.html"
# GLAND ALERT RECIPIENT ROUTING V3 END
