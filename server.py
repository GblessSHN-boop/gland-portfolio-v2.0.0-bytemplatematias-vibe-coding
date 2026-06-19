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


PROJECT_ROOT = Path(__file__).resolve().parent


class GlandPortfolioHandler(SimpleHTTPRequestHandler):
    server_version = "GlandPortfolioPython/0.4"

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

        return super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/contact":
            self._handle_create_contact()
            return

        if path == "/api/projects":
            self._handle_create_project()
            return

        self._send_json(404, {"success": False, "message": "API endpoint not found."})

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

    def do_PATCH(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        message_id = self._get_id_from_path(path, "messages")

        if message_id is not None:
            self._handle_update_message(message_id)
            return

        project_id = self._get_id_from_path(path, "projects")

        if project_id is not None:
            self._handle_update_project(project_id)
            return

        self._send_json(404, {"success": False, "message": "Update endpoint not found."})

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

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        message_id = self._get_id_from_path(path, "messages")

        if message_id is not None:
            self._handle_delete_message(message_id)
            return

        project_id = self._get_id_from_path(path, "projects")

        if project_id is not None:
            self._handle_delete_project(project_id)
            return

        self._send_json(404, {"success": False, "message": "Delete endpoint not found."})

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