from backend.db import get_connection


SITE_IDENTITY_FIELDS = {
    "site_title",
    "meta_description",
    "canonical_url",
    "logo_path",
    "header_icon_path",
    "favicon_path",
    "preloader_text",
    "youtube_url",
    "github_url",
    "instagram_url",
    "linkedin_url",
    "is_active",
}


def normalize_site_identity(row):
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


def clean_site_identity_payload(data, partial=False):
    payload = {}

    for field in SITE_IDENTITY_FIELDS:
        if field in data:
            payload[field] = data.get(field)

    if not partial:
        payload.setdefault("site_title", "")
        payload.setdefault("meta_description", "")
        payload.setdefault("canonical_url", "")
        payload.setdefault("logo_path", "")
        payload.setdefault("header_icon_path", "")
        payload.setdefault("favicon_path", "")
        payload.setdefault("preloader_text", "")
        payload.setdefault("youtube_url", "")
        payload.setdefault("github_url", "")
        payload.setdefault("instagram_url", "")
        payload.setdefault("linkedin_url", "")
        payload.setdefault("is_active", True)

    for field in (
        "site_title",
        "meta_description",
        "canonical_url",
        "logo_path",
        "header_icon_path",
        "favicon_path",
        "preloader_text",
        "youtube_url",
        "github_url",
        "instagram_url",
        "linkedin_url",
    ):
        if field in payload:
            payload[field] = str(payload.get(field) or "").strip()

    if "is_active" in payload:
        payload["is_active"] = to_bool_int(payload.get("is_active"), default=True)

    if not partial and not payload["site_title"]:
        raise ValueError("Site title is required.")

    if partial and "site_title" in payload and not payload["site_title"]:
        raise ValueError("Site title cannot be empty.")

    return payload


def get_site_identity():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, site_title, meta_description, canonical_url,
                   logo_path, header_icon_path, favicon_path, preloader_text,
                   youtube_url, github_url, instagram_url, linkedin_url,
                   is_active, created_at, updated_at
            FROM site_identity
            ORDER BY id ASC
            LIMIT 1
        """

        cursor.execute(query)
        row = cursor.fetchone()

        return normalize_site_identity(row)
    finally:
        cursor.close()
        connection.close()


def create_site_identity(data):
    payload = clean_site_identity_payload(data, partial=False)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO site_identity (
                site_title, meta_description, canonical_url,
                logo_path, header_icon_path, favicon_path, preloader_text,
                youtube_url, github_url, instagram_url, linkedin_url,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["site_title"],
                payload["meta_description"],
                payload["canonical_url"],
                payload["logo_path"],
                payload["header_icon_path"],
                payload["favicon_path"],
                payload["preloader_text"],
                payload["youtube_url"],
                payload["github_url"],
                payload["instagram_url"],
                payload["linkedin_url"],
                payload["is_active"],
            ),
        )

        connection.commit()

        return get_site_identity()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_site_identity(data):
    existing = get_site_identity()

    if not existing:
        return create_site_identity(data)

    payload = clean_site_identity_payload(data, partial=True)

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
            UPDATE site_identity
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        return get_site_identity()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_site_identity():
    existing = get_site_identity()

    if not existing:
        return False

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM site_identity WHERE id = %s", (existing["id"],))
        connection.commit()

        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()