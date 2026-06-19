from backend.password_reset_service import request_admin_password_reset, reset_admin_password_with_token
from backend.notification_service import send_admin_login_alert
from backend.login_activity_service import create_login_event, update_login_event_alert_status
from backend.auth_service import authenticate_admin, create_admin_session, delete_admin_session, get_admin_by_session_token
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timezone
import json
import os

import config
from backend.db import test_connection
from backend.message_service import (
    create_message,
    delete_message,
    get_message_by_id,
    get_recent_messages,
    update_message,
)
from backend.project_service import (
    create_project,
    delete_project,
    get_project_by_id,
    list_projects,
    update_project,
)
from backend.highlight_service import (
    create_highlight,
    delete_highlight,
    get_highlight_by_id,
    list_highlights,
    update_highlight,
)
from backend.personal_info_service import (
    delete_personal_info,
    get_personal_info,
    update_personal_info,
)
from backend.hero_content_service import (
    delete_hero_content,
    get_hero_content,
    update_hero_content,
)
from backend.site_identity_service import (
    delete_site_identity,
    get_site_identity,
    update_site_identity,
)
from backend.media_service import (
    create_media_file,
    delete_media_file,
    get_media_file_by_id,
    list_media_files,
    update_media_file,
)
from backend.analytics_service import (
    get_analytics_summary,
    list_recent_events,
    record_event,
    record_visit,
)


PROJECT_ROOT = Path(__file__).resolve().parent


class GlandPortfolioHandler(SimpleHTTPRequestHandler):
    server_version = "GlandPortfolioPython/1.0"

    def _send_json(self, status_code, payload):
        response = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)

    def _read_request_data(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""
        content_type = self.headers.get("Content-Type", "").lower()

        if "application/json" in content_type:
            try:
                return json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}

        parsed = parse_qs(raw_body.decode("utf-8", errors="ignore"))

        return {
            key: values[0] if values else ""
            for key, values in parsed.items()
        }

    def _get_id_from_path(self, path, collection):
        parts = path.strip("/").split("/")

        if len(parts) != 3:
            return None

        if parts[0] != "api" or parts[1] != collection:
            return None

        try:
            return int(parts[2])
        except ValueError:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, POST, PATCH, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        # GLAND ADMIN AUTH GET ROUTES START
        if path == "/api/auth/me":
            self._handle_auth_me()
            return
        if self._auth_requires_guard(path, "GET"):
            if not self._auth_current_admin():
                self._auth_reject(path)
                return
        # GLAND ADMIN AUTH GET ROUTES END

        if path == "/api/health":
            db_status = test_connection()

            self._send_json(
                200 if db_status["success"] else 503,
                {
                    "success": db_status["success"],
                    "app": "GLAND Portfolio Admin CMS",
                    "backend": "python",
                    "database": db_status,
                    "message": "Python backend is running.",
                    "time": datetime.now(timezone.utc).isoformat(),
                },
            )
            return

        if path == "/api/analytics/summary":
            try:
                summary = get_analytics_summary()
                self._send_json(200, {"success": True, "data": summary})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load analytics summary.",
                        "error": str(error),
                    },
                )
            return

        if path == "/api/analytics/events":
            try:
                events = list_recent_events(limit=100)
                self._send_json(200, {"success": True, "data": events})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load analytics events.",
                        "error": str(error),
                    },
                )
            return
        if path == "/api/media-files":
            try:
                media_files = list_media_files(limit=100)
                self._send_json(200, {"success": True, "data": media_files})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load media files from MySQL.",
                        "error": str(error),
                    },
                )
            return

        media_file_id = self._get_id_from_path(path, "media-files")

        if media_file_id is not None:
            try:
                media_file = get_media_file_by_id(media_file_id)

                if not media_file:
                    self._send_json(404, {"success": False, "message": "Media file not found."})
                    return

                self._send_json(200, {"success": True, "data": media_file})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load media file from MySQL.",
                        "error": str(error),
                    },
                )
            return
        if path == "/api/site-identity":
            try:
                site_identity = get_site_identity()
                self._send_json(200, {"success": True, "data": site_identity})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load site identity from MySQL.",
                        "error": str(error),
                    },
                )
            return
        if path == "/api/site-identity":
            self._handle_update_site_identity()
            return
        if path == "/api/hero-content":
            try:
                hero_content = get_hero_content()
                self._send_json(200, {"success": True, "data": hero_content})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load hero content from MySQL.",
                        "error": str(error),
                    },
                )
            return
        if path == "/api/personal-info":
            try:
                personal_info = get_personal_info()
                self._send_json(200, {"success": True, "data": personal_info})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load personal info from MySQL.",
                        "error": str(error),
                    },
                )
            return

        if path == "/api/messages":
            try:
                messages = get_recent_messages(limit=50)
                self._send_json(200, {"success": True, "data": messages})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load messages from MySQL.",
                        "error": str(error),
                    },
                )
            return

        if path == "/api/hero-content":
            self._handle_update_hero_content()
            return
        media_file_id = self._get_id_from_path(path, "media-files")

        if media_file_id is not None:
            self._handle_update_media_file(media_file_id)
            return
        message_id = self._get_id_from_path(path, "messages")

        if message_id is not None:
            try:
                message = get_message_by_id(message_id)

                if not message:
                    self._send_json(404, {"success": False, "message": "Message not found."})
                    return

                self._send_json(200, {"success": True, "data": message})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load message from MySQL.",
                        "error": str(error),
                    },
                )
            return

        if path == "/api/hero-content":
            self._handle_update_hero_content()
            return
        if path == "/api/projects":
            try:
                projects = list_projects(limit=100)
                self._send_json(200, {"success": True, "data": projects})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load projects from MySQL.",
                        "error": str(error),
                    },
                )
            return

        project_id = self._get_id_from_path(path, "projects")

        if project_id is not None:
            try:
                project = get_project_by_id(project_id)

                if not project:
                    self._send_json(404, {"success": False, "message": "Project not found."})
                    return

                self._send_json(200, {"success": True, "data": project})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load project from MySQL.",
                        "error": str(error),
                    },
                )
            return

        if path == "/api/highlights":
            try:
                highlights = list_highlights(limit=100)
                self._send_json(200, {"success": True, "data": highlights})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load highlights from MySQL.",
                        "error": str(error),
                    },
                )
            return

        highlight_id = self._get_id_from_path(path, "highlights")

        if highlight_id is not None:
            try:
                highlight = get_highlight_by_id(highlight_id)

                if not highlight:
                    self._send_json(404, {"success": False, "message": "Highlight not found."})
                    return

                self._send_json(200, {"success": True, "data": highlight})
            except Exception as error:
                self._send_json(
                    500,
                    {
                        "success": False,
                        "message": "Failed to load highlight from MySQL.",
                        "error": str(error),
                    },
                )
            return

        return super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        # GLAND ADMIN AUTH POST ROUTES START
        if path == "/api/auth/login":
            self._handle_auth_login()
            return
        if path == "/api/auth/logout":
            self._handle_auth_logout()
            return
        if path == "/api/auth/forgot-password":
            self._handle_auth_forgot_password()
            return
        if path == "/api/auth/reset-password":
            self._handle_auth_reset_password()
            return
        if self._auth_requires_guard(path, "POST"):
            if not self._auth_current_admin():
                self._auth_reject(path)
                return
        # GLAND ADMIN AUTH POST ROUTES END

        if path == "/api/analytics/visit":
            self._handle_record_analytics_visit()
            return

        if path == "/api/analytics/event":
            self._handle_record_analytics_event()
            return
        if path == "/api/media-files":
            self._handle_create_media_file()
            return
        if path == "/api/contact":
            self._handle_create_contact()
            return

        if path == "/api/projects":
            self._handle_create_project()
            return

        if path == "/api/highlights":
            self._handle_create_highlight()
            return

        if path == "/api/personal-info":
            self._handle_update_personal_info()
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})

    def _get_client_ip(self):
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if self.client_address:
            return self.client_address[0]

        return ""

    def _handle_record_analytics_visit(self):
        data = self._read_request_data()

        try:
            visit = record_visit(data, ip_address=self._get_client_ip())

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Analytics visit recorded.",
                    "data": visit,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to record analytics visit.",
                    "error": str(error),
                },
            )

    def _handle_record_analytics_event(self):
        data = self._read_request_data()

        try:
            event = record_event(data, ip_address=self._get_client_ip())

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Analytics event recorded.",
                    "data": event,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to record analytics event.",
                    "error": str(error),
                },
            )
    def _handle_create_media_file(self):
        data = self._read_request_data()

        try:
            media_file = create_media_file(data)

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Media file uploaded.",
                    "data": media_file,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to upload media file.",
                    "error": str(error),
                },
            )
    def _handle_create_contact(self):
        data = self._read_request_data()

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip()
        subject = str(data.get("subject", "")).strip()
        message = str(data.get("message", "")).strip()

        errors = []

        if not name:
            errors.append("Name is required.")

        if not email or "@" not in email:
            errors.append("Valid email is required.")

        if not message:
            errors.append("Message is required.")

        if errors:
            self._send_json(
                400,
                {
                    "success": False,
                    "message": "Contact message validation failed.",
                    "errors": errors,
                },
            )
            return

        try:
            saved_message = create_message(name, email, subject, message)

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Message received and saved to MySQL database.",
                    "data": saved_message,
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Message received but failed to save to MySQL database.",
                    "error": str(error),
                },
            )

    def _handle_create_project(self):
        data = self._read_request_data()

        try:
            project = create_project(data)

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Project created.",
                    "data": project,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to create project.",
                    "error": str(error),
                },
            )

    def _handle_create_highlight(self):
        data = self._read_request_data()

        try:
            highlight = create_highlight(data)

            self._send_json(
                201,
                {
                    "success": True,
                    "message": "Highlight created.",
                    "data": highlight,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to create highlight.",
                    "error": str(error),
                },
            )

    def do_PATCH(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        # GLAND ADMIN AUTH PATCH GUARD START
        if self._auth_requires_guard(path, "PATCH"):
            if not self._auth_current_admin():
                self._auth_reject(path)
                return
        # GLAND ADMIN AUTH PATCH GUARD END
        # GLAND SINGLETON CMS PATCH ROUTES START
        if path == "/api/hero-content":
            self._handle_update_hero_content()
            return
        if path == "/api/site-identity":
            self._handle_update_site_identity()
            return
        if path == "/api/personal-info":
            self._handle_update_personal_info()
            return
        # GLAND SINGLETON CMS PATCH ROUTES END

        if path == "/api/personal-info":
            self._handle_update_personal_info()
            return

        message_id = self._get_id_from_path(path, "messages")

        if message_id is not None:
            self._handle_update_message(message_id)
            return

        project_id = self._get_id_from_path(path, "projects")

        if project_id is not None:
            self._handle_update_project(project_id)
            return

        highlight_id = self._get_id_from_path(path, "highlights")

        if highlight_id is not None:
            self._handle_update_highlight(highlight_id)
            return

        self._send_json(404, {"success": False, "message": "Update endpoint not found."})

    def _handle_update_media_file(self, media_file_id):
        data = self._read_request_data()

        try:
            media_file = update_media_file(media_file_id, data)

            if not media_file:
                self._send_json(404, {"success": False, "message": "Media file not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Media file updated.",
                    "data": media_file,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update media file.",
                    "error": str(error),
                },
            )
    def _handle_update_site_identity(self):
        data = self._read_request_data()

        try:
            site_identity = update_site_identity(data)

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Site identity updated.",
                    "data": site_identity,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update site identity.",
                    "error": str(error),
                },
            )
    def _handle_update_hero_content(self):
        data = self._read_request_data()

        try:
            hero_content = update_hero_content(data)

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Hero content updated.",
                    "data": hero_content,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update hero content.",
                    "error": str(error),
                },
            )
    def _handle_update_personal_info(self):
        data = self._read_request_data()

        try:
            personal_info = update_personal_info(data)

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Personal info updated.",
                    "data": personal_info,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update personal info.",
                    "error": str(error),
                },
            )

    def _handle_update_message(self, message_id):
        data = self._read_request_data()

        status = data.get("status")
        admin_note = data.get("admin_note")

        if status is not None:
            status = str(status).strip()

        if admin_note is not None:
            admin_note = str(admin_note).strip()

        if status is None and admin_note is None:
            self._send_json(
                400,
                {
                    "success": False,
                    "message": "Nothing to update. Send status or admin_note.",
                },
            )
            return

        try:
            updated_message = update_message(
                message_id=message_id,
                status=status,
                admin_note=admin_note,
            )

            if not updated_message:
                self._send_json(404, {"success": False, "message": "Message not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Message updated.",
                    "data": updated_message,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update message.",
                    "error": str(error),
                },
            )

    def _handle_update_project(self, project_id):
        data = self._read_request_data()

        try:
            project = update_project(project_id, data)

            if not project:
                self._send_json(404, {"success": False, "message": "Project not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Project updated.",
                    "data": project,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update project.",
                    "error": str(error),
                },
            )

    def _handle_update_highlight(self, highlight_id):
        data = self._read_request_data()

        try:
            highlight = update_highlight(highlight_id, data)

            if not highlight:
                self._send_json(404, {"success": False, "message": "Highlight not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Highlight updated.",
                    "data": highlight,
                },
            )
        except ValueError as error:
            self._send_json(400, {"success": False, "message": str(error)})
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to update highlight.",
                    "error": str(error),
                },
            )

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        # GLAND ADMIN AUTH DELETE GUARD START
        if self._auth_requires_guard(path, "DELETE"):
            if not self._auth_current_admin():
                self._auth_reject(path)
                return
        # GLAND ADMIN AUTH DELETE GUARD END

        if path == "/api/personal-info":
            self._handle_delete_personal_info()
            return

        if path == "/api/site-identity":
            self._handle_update_site_identity()
            return
        if path == "/api/hero-content":
            self._handle_delete_hero_content()
            return
        if path == "/api/site-identity":
            self._handle_delete_site_identity()
            return
        media_file_id = self._get_id_from_path(path, "media-files")

        if media_file_id is not None:
            self._handle_delete_media_file(media_file_id)
            return
        message_id = self._get_id_from_path(path, "messages")

        if message_id is not None:
            self._handle_delete_message(message_id)
            return

        project_id = self._get_id_from_path(path, "projects")

        if project_id is not None:
            self._handle_delete_project(project_id)
            return

        highlight_id = self._get_id_from_path(path, "highlights")

        if highlight_id is not None:
            self._handle_delete_highlight(highlight_id)
            return

        self._send_json(404, {"success": False, "message": "Delete endpoint not found."})

    def _handle_delete_media_file(self, media_file_id):
        try:
            was_deleted = delete_media_file(media_file_id)

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Media file not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Media file deleted.",
                    "data": {"id": media_file_id},
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete media file.",
                    "error": str(error),
                },
            )
    def _handle_delete_site_identity(self):
        try:
            was_deleted = delete_site_identity()

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Site identity not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Site identity deleted.",
                    "data": None,
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete site identity.",
                    "error": str(error),
                },
            )
    def _handle_delete_hero_content(self):
        try:
            was_deleted = delete_hero_content()

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Hero content not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Hero content deleted.",
                    "data": None,
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete hero content.",
                    "error": str(error),
                },
            )
    def _handle_delete_personal_info(self):
        try:
            was_deleted = delete_personal_info()

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Personal info not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Personal info deleted.",
                    "data": None,
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete personal info.",
                    "error": str(error),
                },
            )

    def _handle_delete_message(self, message_id):
        try:
            was_deleted = delete_message(message_id)

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Message not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Message deleted.",
                    "data": {"id": message_id},
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete message.",
                    "error": str(error),
                },
            )

    def _handle_delete_project(self, project_id):
        try:
            was_deleted = delete_project(project_id)

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Project not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Project deleted.",
                    "data": {"id": project_id},
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete project.",
                    "error": str(error),
                },
            )

    def _handle_delete_highlight(self, highlight_id):
        try:
            was_deleted = delete_highlight(highlight_id)

            if not was_deleted:
                self._send_json(404, {"success": False, "message": "Highlight not found."})
                return

            self._send_json(
                200,
                {
                    "success": True,
                    "message": "Highlight deleted.",
                    "data": {"id": highlight_id},
                },
            )
        except Exception as error:
            self._send_json(
                500,
                {
                    "success": False,
                    "message": "Failed to delete highlight.",
                    "error": str(error),
                },
            )

    # GLAND ADMIN AUTH METHODS START
    def _auth_read_json(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            content_length = 0

        if content_length <= 0:
            return {}

        raw_body = self.rfile.read(content_length).decode("utf-8")

        if not raw_body.strip():
            return {}

        return json.loads(raw_body)

    def _auth_json_response(self, status_code, payload, cookie_header=None):
        body = json.dumps(payload, default=str, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))

        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)

        self.end_headers()
        self.wfile.write(body)

    def _auth_cookie_header(self, token, max_age_seconds):
        return (
            f"gland_admin_session={token}; "
            "Path=/; "
            "HttpOnly; "
            "SameSite=Lax; "
            f"Max-Age={int(max_age_seconds)}"
        )

    def _auth_expired_cookie_header(self):
        return "gland_admin_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"

    def _auth_cookie_token(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            morsel = cookie.get("gland_admin_session")
            return morsel.value if morsel else ""
        except Exception:
            return ""

    def _auth_client_ip(self):
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

        try:
            return self.client_address[0]
        except Exception:
            return ""

    def _auth_current_admin(self):
        token = self._auth_cookie_token()

        if not token:
            return None

        try:
            return get_admin_by_session_token(token)
        except Exception:
            return None

    def _auth_requires_guard(self, path, method):
        method = (method or "").upper()

        if path in {"/admin/login.html", "/admin/forgot-password.html", "/admin/reset-password.html"} or path.startswith("/admin/assets/"):
            return False

        if path.startswith("/admin/") and method == "GET":
            if path == "/admin/" or path.endswith(".html"):
                return True

        if not path.startswith("/api/"):
            return False

        if path.startswith("/api/auth/"):
            return False

        if path == "/api/health":
            return False

        if method == "GET":
            public_get_exact = {
                "/api/site-identity",
                "/api/hero-content",
                "/api/personal-info",
            }

            if path in public_get_exact:
                return False

            public_get_prefixes = (
                "/api/projects",
                "/api/highlights",
                "/api/media-files",
            )

            for prefix in public_get_prefixes:
                if path == prefix or path.startswith(prefix + "/"):
                    return False

            return True

        if method == "POST":
            public_post_exact = {
                "/api/contact",
                "/api/analytics/visit",
                "/api/analytics/event",
            }

            if path in public_post_exact:
                return False

            return True

        if method in {"PATCH", "DELETE"}:
            return True

        return False

    def _auth_reject(self, path):
        if path.startswith("/api/"):
            self._auth_json_response(
                401,
                {
                    "success": False,
                    "authenticated": False,
                    "message": "Authentication required.",
                },
            )
            return

        self.send_response(302)
        self.send_header("Location", "/admin/login.html")
        self.end_headers()

    def _handle_auth_me(self):
        admin = self._auth_current_admin()

        if not admin:
            self._auth_json_response(
                200,
                {
                    "success": True,
                    "authenticated": False,
                    "data": None,
                },
            )
            return

        self._auth_json_response(
            200,
            {
                "success": True,
                "authenticated": True,
                "data": {
                    "admin": admin,
                },
            },
        )

    def _handle_auth_login(self):
        try:
            data = self._auth_read_json()
        except Exception:
            self._auth_json_response(
                400,
                {
                    "success": False,
                    "authenticated": False,
                    "message": "Invalid JSON body.",
                },
            )
            return

        identifier = str(data.get("username") or data.get("email") or "").strip()
        password = str(data.get("password") or "")

        if not identifier or not password:
            self._auth_record_event_and_alert(
                "login_failed",
                identifier=identifier,
                success=False,
                message="Missing username/email or password.",
            )
            self._auth_json_response(
                400,
                {
                    "success": False,
                    "authenticated": False,
                    "message": "Username/email and password are required.",
                },
            )
            return

        try:
            admin = authenticate_admin(identifier, password)
        except Exception:
            admin = None

        if not admin:
            self._auth_record_event_and_alert(
                "login_failed",
                identifier=identifier,
                success=False,
                message="Invalid username/email or password.",
            )
            self._auth_json_response(
                401,
                {
                    "success": False,
                    "authenticated": False,
                    "message": "Invalid username/email or password.",
                },
            )
            return

        session = create_admin_session(
            admin["id"],
            ip_address=self._auth_client_ip(),
            user_agent=self.headers.get("User-Agent", ""),
        )

        self._auth_record_event_and_alert(
            "login_success",
            identifier=identifier,
            admin=admin,
            success=True,
            message="Login successful.",
        )

        self._auth_json_response(
            200,
            {
                "success": True,
                "authenticated": True,
                "message": "Login successful.",
                "data": {
                    "admin": admin,
                    "expires_at": session.get("expires_at"),
                },
            },
            cookie_header=self._auth_cookie_header(
                session["token"],
                session.get("max_age_seconds", 43200),
            ),
        )

    def _handle_auth_logout(self):
        token = self._auth_cookie_token()
        admin = self._auth_current_admin()
        identifier = ""

        if isinstance(admin, dict):
            identifier = str(admin.get("username") or admin.get("email") or "")

        try:
            if token:
                delete_admin_session(token)
        except Exception:
            pass

        self._auth_record_event_and_alert(
            "logout",
            identifier=identifier,
            admin=admin,
            success=True,
            message="Logout successful.",
        )

        self._auth_json_response(
            200,
            {
                "success": True,
                "authenticated": False,
                "message": "Logout successful.",
            },
            cookie_header=self._auth_expired_cookie_header(),
        )

    # GLAND ADMIN LOGIN ALERT METHODS START
    def _auth_record_event_and_alert(self, event_type, identifier="", admin=None, success=False, message=""):
        admin_id = None

        if isinstance(admin, dict):
            admin_id = admin.get("id")

        try:
            event = create_login_event(
                event_type=event_type,
                identifier=identifier,
                admin_id=admin_id,
                success=success,
                ip_address=self._auth_client_ip(),
                user_agent=self.headers.get("User-Agent", ""),
                message=message,
            )
        except Exception:
            return None

        try:
            alert_result = send_admin_login_alert(event)

            if alert_result and not alert_result.get("skipped"):
                update_login_event_alert_status(
                    int(event.get("id") or 0),
                    sent=bool(alert_result.get("sent")),
                    error=str(alert_result.get("error") or ""),
                )
        except Exception:
            pass

        return event
    # GLAND ADMIN LOGIN ALERT METHODS END


    # GLAND ADMIN PASSWORD RESET METHODS START
    def _auth_request_base_url(self):
        host = self.headers.get("Host", "127.0.0.1:8000")
        scheme = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
        return f"{scheme}://{host}"

    def _handle_auth_forgot_password(self):
        try:
            data = self._auth_read_json()
        except Exception:
            self._auth_json_response(
                400,
                {
                    "success": False,
                    "message": "Invalid JSON body.",
                },
            )
            return

        identifier = str(data.get("identifier") or data.get("email") or data.get("username") or "").strip()

        if not identifier:
            self._auth_json_response(
                400,
                {
                    "success": False,
                    "message": "Username or email is required.",
                },
            )
            return

        result = request_admin_password_reset(
            identifier,
            base_url=self._auth_request_base_url(),
            ip_address=self._auth_client_ip(),
            user_agent=self.headers.get("User-Agent", ""),
        )

        status_code = int(result.get("status_code") or (200 if result.get("success") else 400))

        self._auth_json_response(
            status_code,
            {
                "success": bool(result.get("success")),
                "message": result.get("message") or "",
                "data": {
                    "email_sent": bool(result.get("email_sent")),
                    "email_skipped": bool(result.get("email_skipped")),
                    "debug_reset_url": result.get("debug_reset_url"),
                    "retry_after_seconds": int(result.get("retry_after_seconds") or 0),
                    "cooldown_seconds": int(result.get("cooldown_seconds") or 0),
                },
            },
        )

    def _handle_auth_reset_password(self):
        try:
            data = self._auth_read_json()
        except Exception:
            self._auth_json_response(
                400,
                {
                    "success": False,
                    "message": "Invalid JSON body.",
                },
            )
            return

        token = str(data.get("token") or "").strip()
        new_password = str(data.get("new_password") or data.get("password") or "")

        result = reset_admin_password_with_token(token, new_password)
        status_code = int(result.get("status_code") or (200 if result.get("success") else 400))

        self._auth_json_response(
            status_code,
            {
                "success": bool(result.get("success")),
                "message": result.get("message") or "",
                "data": {
                    "admin": result.get("admin"),
                } if result.get("success") else None,
            },
        )
    # GLAND ADMIN PASSWORD RESET METHODS END

    # GLAND ADMIN AUTH METHODS END


def run():
    os.chdir(PROJECT_ROOT)

    server_address = (config.APP_HOST, config.APP_PORT)
    httpd = ThreadingHTTPServer(server_address, GlandPortfolioHandler)

    print(f"GLAND Portfolio Python backend running at http://{config.APP_HOST}:{config.APP_PORT}")
    print("Press Ctrl+C to stop the server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()