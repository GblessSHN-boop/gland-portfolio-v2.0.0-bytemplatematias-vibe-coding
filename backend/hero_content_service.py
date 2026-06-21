from backend.db import get_connection


HERO_CONTENT_FIELDS = {
    "eyebrow",
    "title_line_1",
    "title_line_2",
    "description",
    "availability_text",
    "availability_location",
    "phone_label",
    "phone_url",
    "intro_video_label",
    "intro_video_url",
    "hero_media_type",
    "hero_media_path",
    "background_image_path",
    "is_active",
}


VALID_MEDIA_TYPES = {"image", "video"}


def normalize_hero_content(row):
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


def clean_hero_content_payload(data, partial=False):
    payload = {}

    for field in HERO_CONTENT_FIELDS:
        if field in data:
            payload[field] = data.get(field)

    if not partial:
        payload.setdefault("eyebrow", "")
        payload.setdefault("title_line_1", "")
        payload.setdefault("title_line_2", "")
        payload.setdefault("description", "")
        payload.setdefault("availability_text", "")
        payload.setdefault("availability_location", "")
        payload.setdefault("phone_label", "")
        payload.setdefault("phone_url", "")
        payload.setdefault("intro_video_label", "")
        payload.setdefault("intro_video_url", "")
        payload.setdefault("hero_media_type", "video")
        payload.setdefault("hero_media_path", "")
        payload.setdefault("background_image_path", "")
        payload.setdefault("is_active", True)

    for field in (
        "eyebrow",
        "title_line_1",
        "title_line_2",
        "description",
        "availability_text",
        "availability_location",
        "phone_label",
        "phone_url",
        "intro_video_label",
        "intro_video_url",
        "hero_media_type",
        "hero_media_path",
        "background_image_path",
    ):
        if field in payload:
            payload[field] = str(payload.get(field) or "").strip()

    if "hero_media_type" in payload:
        payload["hero_media_type"] = payload["hero_media_type"].lower()

        if payload["hero_media_type"] not in VALID_MEDIA_TYPES:
            raise ValueError("Hero media type must be image or video.")

    if "is_active" in payload:
        payload["is_active"] = to_bool_int(payload.get("is_active"), default=True)

    if not partial and not payload["title_line_1"]:
        raise ValueError("Hero title line 1 is required.")

    if partial and "title_line_1" in payload and not payload["title_line_1"]:
        raise ValueError("Hero title line 1 cannot be empty.")

    return payload


def get_hero_content():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, eyebrow, title_line_1, title_line_2, description,
                   availability_text, availability_location, phone_label, phone_url,
                   intro_video_label, intro_video_url, hero_media_type, hero_media_path,
                   background_image_path, is_active, created_at, updated_at
            FROM hero_content
            ORDER BY id ASC
            LIMIT 1
        """

        cursor.execute(query)
        row = cursor.fetchone()

        return normalize_hero_content(row)
    finally:
        cursor.close()
        connection.close()


def create_hero_content(data):
    payload = clean_hero_content_payload(data, partial=False)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO hero_content (
                eyebrow, title_line_1, title_line_2, description,
                availability_text, availability_location, phone_label, phone_url,
                intro_video_label, intro_video_url, hero_media_type, hero_media_path,
                background_image_path, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["eyebrow"],
                payload["title_line_1"],
                payload["title_line_2"],
                payload["description"],
                payload["availability_text"],
                payload["availability_location"],
                payload["phone_label"],
                payload["phone_url"],
                payload["intro_video_label"],
                payload["intro_video_url"],
                payload["hero_media_type"],
                payload["hero_media_path"],
                payload["background_image_path"],
                payload["is_active"],
            ),
        )

        connection.commit()

        return get_hero_content()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_hero_content(data):
    existing = get_hero_content()

    if not existing:
        return create_hero_content(data)

    payload = clean_hero_content_payload(data, partial=True)

    if not payload:
        return existing

    fields = []
    params = []

    for field, value in payload.items():
        fields.append(f"{field} = %s")
        params.append(value)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(existing["id"])

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = f"""
            UPDATE hero_content
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        return get_hero_content()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_hero_content():
    existing = get_hero_content()

    if not existing:
        return False

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM hero_content WHERE id = %s", (existing["id"],))
        connection.commit()

        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()