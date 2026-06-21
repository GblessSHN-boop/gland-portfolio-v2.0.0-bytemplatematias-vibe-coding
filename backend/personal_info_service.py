from backend.db import get_connection


PERSONAL_INFO_FIELDS = {
    "full_name",
    "role_title",
    "description",
    "email",
    "phone",
    "address",
    "photo_path",
    "resume_url",
    "is_active",
}


def normalize_personal_info(row):
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


def clean_personal_info_payload(data, partial=False):
    payload = {}

    for field in PERSONAL_INFO_FIELDS:
        if field in data:
            payload[field] = data.get(field)

    if not partial:
        payload.setdefault("full_name", "")
        payload.setdefault("role_title", "")
        payload.setdefault("description", "")
        payload.setdefault("email", "")
        payload.setdefault("phone", "")
        payload.setdefault("address", "")
        payload.setdefault("photo_path", "")
        payload.setdefault("resume_url", "")
        payload.setdefault("is_active", True)

    for field in (
        "full_name",
        "role_title",
        "description",
        "email",
        "phone",
        "address",
        "photo_path",
        "resume_url",
    ):
        if field in payload:
            payload[field] = str(payload.get(field) or "").strip()

    if "is_active" in payload:
        payload["is_active"] = to_bool_int(payload.get("is_active"), default=True)

    if not partial and not payload["full_name"]:
        raise ValueError("Full name is required.")

    if partial and "full_name" in payload and not payload["full_name"]:
        raise ValueError("Full name cannot be empty.")

    return payload


def get_personal_info():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, full_name, role_title, description, email, phone, address,
                   photo_path, resume_url, is_active, created_at, updated_at
            FROM personal_info
            ORDER BY id ASC
            LIMIT 1
        """

        cursor.execute(query)
        row = cursor.fetchone()

        return normalize_personal_info(row)
    finally:
        cursor.close()
        connection.close()


def create_personal_info(data):
    payload = clean_personal_info_payload(data, partial=False)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO personal_info (
                full_name, role_title, description, email, phone, address,
                photo_path, resume_url, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["full_name"],
                payload["role_title"],
                payload["description"],
                payload["email"],
                payload["phone"],
                payload["address"],
                payload["photo_path"],
                payload["resume_url"],
                payload["is_active"],
            ),
        )

        connection.commit()

        return get_personal_info()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_personal_info(data):
    existing = get_personal_info()

    if not existing:
        return create_personal_info(data)

    payload = clean_personal_info_payload(data, partial=True)

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
            UPDATE personal_info
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        return get_personal_info()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_personal_info():
    existing = get_personal_info()

    if not existing:
        return False

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM personal_info WHERE id = %s", (existing["id"],))
        connection.commit()

        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()