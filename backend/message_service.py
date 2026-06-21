from backend.db import get_connection
from backend.activity_service import create_admin_activity


VALID_MESSAGE_STATUSES = {"new", "read", "approved", "rejected", "archived"}


def normalize_message(row):
    if not row:
        return None

    for key in ("created_at", "updated_at"):
        if row.get(key):
            row[key] = row[key].isoformat(sep=" ")

    return row


def create_message(name, email, subject, message):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            INSERT INTO messages (name, email, subject, message, status)
            VALUES (%s, %s, %s, %s, 'new')
        """

        cursor.execute(query, (name, email, subject, message))
        connection.commit()

        message_id = cursor.lastrowid

        # GLAND MESSAGE ACTIVITY CREATE START
        try:
            create_admin_activity(
                action="message_created",
                entity_type="message",
                entity_id=message_id,
                description="New contact message received.",
                metadata={"name": name, "email": email, "subject": subject},
            )
        except Exception:
            pass
        # GLAND MESSAGE ACTIVITY CREATE END

        return {
            "id": message_id,
            "name": name,
            "email": email,
            "subject": subject,
            "status": "new",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def get_recent_messages(limit=50):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, name, email, subject, message, status, admin_note, created_at, updated_at
            FROM messages
            ORDER BY created_at DESC
            LIMIT %s
        """

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        return [normalize_message(row) for row in rows]
    finally:
        cursor.close()
        connection.close()


def get_message_by_id(message_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, name, email, subject, message, status, admin_note, created_at, updated_at
            FROM messages
            WHERE id = %s
            LIMIT 1
        """

        cursor.execute(query, (message_id,))
        row = cursor.fetchone()

        return normalize_message(row)
    finally:
        cursor.close()
        connection.close()


def update_message(message_id, status=None, admin_note=None):
    if status is not None and status not in VALID_MESSAGE_STATUSES:
        raise ValueError(
            "Invalid message status. Allowed statuses: "
            + ", ".join(sorted(VALID_MESSAGE_STATUSES))
        )

    fields = []
    params = []

    if status is not None:
        fields.append("status = %s")
        params.append(status)

    if admin_note is not None:
        fields.append("admin_note = %s")
        params.append(admin_note)

    if not fields:
        return get_message_by_id(message_id)

    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(message_id)

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = f"""
            UPDATE messages
            SET {", ".join(fields)}
            WHERE id = %s
        """

        cursor.execute(query, tuple(params))
        connection.commit()

        if cursor.rowcount == 0:
            return None

        updated_message = get_message_by_id(message_id)

        # GLAND MESSAGE ACTIVITY UPDATE START
        try:
            create_admin_activity(
                action="message_updated",
                entity_type="message",
                entity_id=message_id,
                description="Message status or note updated.",
                metadata={"status": status, "admin_note_changed": admin_note is not None},
            )
        except Exception:
            pass
        # GLAND MESSAGE ACTIVITY UPDATE END

        return updated_message
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def delete_message(message_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        connection.commit()

        deleted = cursor.rowcount > 0

        # GLAND MESSAGE ACTIVITY DELETE START
        if deleted:
            try:
                create_admin_activity(
                    action="message_deleted",
                    entity_type="message",
                    entity_id=message_id,
                    description="Message deleted from admin inbox.",
                )
            except Exception:
                pass
        # GLAND MESSAGE ACTIVITY DELETE END

        return deleted
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()