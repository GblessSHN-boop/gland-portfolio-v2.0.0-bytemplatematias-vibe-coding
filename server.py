from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timezone
import json
import os

import config
from backend.db import test_connection
from backend.message_service import create_message, get_recent_messages


PROJECT_ROOT = Path(__file__).resolve().parent


class GlandPortfolioHandler(SimpleHTTPRequestHandler):
    server_version = "GlandPortfolioPython/0.2"

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

    def do_GET(self):
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/api/health":
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

        if parsed_url.path == "/api/messages":
            try:
                messages = get_recent_messages(limit=50)

                self._send_json(
                    200,
                    {
                        "success": True,
                        "data": messages,
                    },
                )
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

        return super().do_GET()

    def do_POST(self):
        parsed_url = urlparse(self.path)

        if parsed_url.path != "/api/contact":
            self._send_json(
                404,
                {
                    "success": False,
                    "message": "API endpoint not found.",
                },
            )
            return

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