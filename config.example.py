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
