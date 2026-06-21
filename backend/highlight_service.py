from backend.db import get_connection


HIGHLIGHT_FIELDS = {
    "title",
    "subtitle",
    "year_label",
    "highlight_url",
    "display_order",
    "is_active",
}


def normalize_highlight(row):
    if not row:
        return None

    for key in ("created_at", "updated_at"):
        if row.get(key):
            row[key] = row[key].isoformat(sep=" ")

    row["is_active"] = bool(row.get("is_active"))

    return row


def to_int(value, default=0):
    if value is None or value == "":
        return default

    return int(value)


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


def clean_highlight_payload(data, partial=False):
    payload = {}

    for field in HIGHLIGHT_FIELDS:
        if field in data:
            payload[field] = data.get(field)

    if not partial:
        payload.setdefault("title", "")
        payload.setdefault("subtitle", "")
        payload.setdefault("year_label", "")
        payload.setdefault("highlight_url", "")
        payload.setdefault("display_order", 0)
        payload.setdefault("is_active", True)

    for field in ("title", "subtitle", "year_label", "highlight_url"):
        if field in payload:
            payload[field] = str(payload.get(field) or "").strip()

    if "display_order" in payload:
        payload["display_order"] = to_int(payload.get("display_order"), default=0)

    if "is_active" in payload:
        payload["is_active"] = to_bool_int(payload.get("is_active"), default=True)

    if not partial and not payload["title"]:
        raise ValueError("Highlight title is required.")

    if partial and "title" in payload and not payload["title"]:
        raise ValueError("Highlight title cannot be empty.")

    return payload


def list_highlights(limit=100):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, title, subtitle, year_label, highlight_url,
                   display_order, is_active, created_at, updated_at
            FROM selected_highlights
            ORDER BY display_order ASC, id DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        return [normalize_highlight(row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def get_highlight_by_id(highlight_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, title, subtitle, year_label, highlight_url,
                   display_order, is_active, created_at, updated_at
            FROM selected_highlights
            WHERE id = %s
            LIMIT 1
        """

        cursor.execute(query, (highlight_id,))
        row = cursor.fetchone()

        return normalize_highlight(row)
    finally:
        cursor.close()
        connection.close()


def create_highlight(data):
    payload = clean_highlight_payload(data, partial=False)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO selected_highlights (
                title, subtitle, year_label, highlight_url,
                display_order, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                payload["title"],
                payload["subtitle"],
                payload["year_label"],
                payload["highlight_url"],
                payload["display_order"],
                payload["is_active"],
            ),
        )

        connection.commit()

        return get_highlight_by_id(cursor.lastrowid)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def update_highlight(highlight_id, data):
    payload = clean_highlight_payload(data, partial=True)

    if not payload:
        return get_highlight_by_id(highlight_id)

    fields = []
    params = []

    for field, value in payload.items():
        fields.append(f"{field} = %s")
        params.append(value)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(highlight_id)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = f"""
            UPDATE selected_highlights
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        if cursor.rowcount == 0:
            return None

        return get_highlight_by_id(highlight_id)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_highlight(highlight_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM selected_highlights WHERE id = %s", (highlight_id,))
        connection.commit()

        return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()