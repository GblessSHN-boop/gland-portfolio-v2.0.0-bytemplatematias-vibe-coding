from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import uuid


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
DEV_CONTACT_LOG = LOG_DIR / "contact_messages_dev.jsonl"

APP_HOST = "127.0.0.1"
APP_PORT = 8000


class GlandPortfolioHandler(SimpleHTTPRequestHandler):
    server_version = "GlandPortfolioPython/0.1"

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
            self._send_json(
                200,
                {
                    "success": True,
                    "app": "GLAND Portfolio Admin CMS",
                    "backend": "python",
                    "status": "healthy",
                    "message": "Python backend is running.",
                    "time": datetime.now(timezone.utc).isoformat(),
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

        LOG_DIR.mkdir(exist_ok=True)

        record = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
            "status": "new",
            "storage": "dev_log",
            "database": "pending_mysql_integration",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with DEV_CONTACT_LOG.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        self._send_json(
            201,
            {
                "success": True,
                "message": "Message received by Python backend. MySQL storage will be connected in the next phase.",
                "data": {
                    "id": record["id"],
                    "status": record["status"],
                    "storage": record["storage"],
                },
            },
        )


def run():
    os.chdir(PROJECT_ROOT)

    server_address = (APP_HOST, APP_PORT)
    httpd = ThreadingHTTPServer(server_address, GlandPortfolioHandler)

    print(f"GLAND Portfolio Python backend running at http://{APP_HOST}:{APP_PORT}")
    print("Press Ctrl+C to stop the server.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
