from pathlib import Path
from datetime import datetime
from uuid import uuid4
import base64
import re

from backend.db import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_ROOT = PROJECT_ROOT / "uploads"

ALLOWED_MEDIA_TYPES = {"image", "video"}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}

MIME_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}

MEDIA_UPDATE_FIELDS = {
    "title",
    "alt_text",
    "is_active",
}


def normalize_media_file(row):
    if not row:
        return None

    for key in ("created_at", "updated_at"):
        if row.get(key):
            row[key] = row[key].isoformat(sep=" ")

    row["is_active"] = bool(row.get("is_active"))

    return row


def to_bool_int(value, default=True):
    if value is None:
        return 1 if default else 0

    if isinstance(value, bool):
        return 1 if value else 0

    normalized = str(value).strip().lower()

    if normalized in {"1", "true", "yes", "on", "active"}:
        return 1

    if normalized in {"0", "false", "no", "off", "inactive"}:
        return 0

    return 1 if default else 0


def sanitize_filename(filename):
    name = Path(str(filename or "upload")).name
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-").lower()

    if not safe_stem:
        safe_stem = "upload"

    return safe_stem, suffix


def get_media_type_from_extension(extension):
    extension = extension.lower()

    if extension in IMAGE_EXTENSIONS:
        return "image"

    if extension in VIDEO_EXTENSIONS:
        return "video"

    return None


def split_base64_payload(file_base64):
    value = str(file_base64 or "").strip()

    if not value:
        raise ValueError("File content is required.")

    if value.startswith("data:") and "," in value:
        header, payload = value.split(",", 1)
        mime_match = re.match(r"data:([^;]+);base64", header)
        mime_type = mime_match.group(1) if mime_match else ""
        return mime_type, payload

    return "", value


def save_uploaded_file(data):
    original_name = str(data.get("file_name") or "upload").strip()
    requested_media_type = str(data.get("media_type") or "").strip().lower()
    mime_type_from_payload, base64_payload = split_base64_payload(data.get("file_base64"))
    mime_type = str(data.get("mime_type") or mime_type_from_payload or "").strip().lower()

    safe_stem, extension = sanitize_filename(original_name)

    if not extension and mime_type in MIME_EXTENSION_MAP:
        extension = MIME_EXTENSION_MAP[mime_type]

    detected_media_type = get_media_type_from_extension(extension)

    if not detected_media_type:
        raise ValueError("Unsupported media file type.")

    media_type = requested_media_type or detected_media_type

    if media_type not in ALLOWED_MEDIA_TYPES:
        raise ValueError("Media type must be image or video.")

    if media_type != detected_media_type:
        raise ValueError("Media type does not match file extension.")

    try:
        file_bytes = base64.b64decode(base64_payload, validate=True)
    except Exception as error:
        raise ValueError("Invalid base64 file content.") from error

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    folder_name = "images" if media_type == "image" else "videos"
    target_dir = UPLOAD_ROOT / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_name = f"{timestamp}-{uuid4().hex[:10]}-{safe_stem}{extension}"
    target_path = target_dir / unique_name

    target_path.write_bytes(file_bytes)

    relative_path = target_path.relative_to(PROJECT_ROOT).as_posix()

    return {
        "media_type": media_type,
        "file_name": unique_name,
        "file_path": relative_path,
        "mime_type": mime_type,
        "file_size": len(file_bytes),
    }


def clean_media_metadata(data, partial=False):
    payload = {}

    for field in MEDIA_UPDATE_FIELDS:
        if field in data:
            payload[field] = data.get(field)

    if not partial:
        payload.setdefault("title", "")
        payload.setdefault("alt_text", "")
        payload.setdefault("is_active", True)

    for field in ("title", "alt_text"):
        if field in payload:
            payload[field] = str(payload.get(field) or "").strip()

    if "is_active" in payload:
        payload["is_active"] = to_bool_int(payload.get("is_active"), default=True)

    return payload


def list_media_files(limit=100):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, title, alt_text, media_type, file_name, file_path,
                   mime_type, file_size, is_active, created_at, updated_at
            FROM media_files
            ORDER BY id DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        return [normalize_media_file(row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def get_media_file_by_id(media_file_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, title, alt_text, media_type, file_name, file_path,
                   mime_type, file_size, is_active, created_at, updated_at
            FROM media_files
            WHERE id = %s
            LIMIT 1
        """

        cursor.execute(query, (media_file_id,))
        row = cursor.fetchone()

        return normalize_media_file(row)
    finally:
        cursor.close()
        connection.close()


def create_media_file(data):
    saved_file = save_uploaded_file(data)
    metadata = clean_media_metadata(data, partial=False)

    title = metadata["title"] or Path(str(data.get("file_name") or saved_file["file_name"])).stem

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO media_files (
                title, alt_text, media_type, file_name, file_path,
                mime_type, file_size, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                title,
                metadata["alt_text"],
                saved_file["media_type"],
                saved_file["file_name"],
                saved_file["file_path"],
                saved_file["mime_type"],
                saved_file["file_size"],
                metadata["is_active"],
            ),
        )

        connection.commit()

        return get_media_file_by_id(cursor.lastrowid)
    except Exception:
        connection.rollback()

        try:
            uploaded_path = (PROJECT_ROOT / saved_file["file_path"]).resolve()
            if uploaded_path.exists() and str(uploaded_path).startswith(str(PROJECT_ROOT.resolve())):
                uploaded_path.unlink()
        except Exception:
            pass

        raise
    finally:
        cursor.close()
        connection.close()


def update_media_file(media_file_id, data):
    payload = clean_media_metadata(data, partial=True)

    if not payload:
        return get_media_file_by_id(media_file_id)

    fields = []
    params = []

    for field, value in payload.items():
        fields.append(f"{field} = %s")
        params.append(value)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(media_file_id)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = f"""
            UPDATE media_files
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        if cursor.rowcount == 0:
            return None

        return get_media_file_by_id(media_file_id)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_media_file(media_file_id):
    existing = get_media_file_by_id(media_file_id)

    if not existing:
        return False

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM media_files WHERE id = %s", (media_file_id,))
        connection.commit()

        if cursor.rowcount == 0:
            return False

        file_path = existing.get("file_path") or ""

        if file_path:
            absolute_path = (PROJECT_ROOT / file_path).resolve()

            if str(absolute_path).startswith(str(PROJECT_ROOT.resolve())) and absolute_path.exists():
                absolute_path.unlink()

        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()