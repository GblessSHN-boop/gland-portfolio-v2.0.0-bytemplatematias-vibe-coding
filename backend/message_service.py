from backend.db import get_connection


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

        for row in rows:
            if row.get("created_at"):
                row["created_at"] = row["created_at"].isoformat(sep=" ")
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat(sep=" ")

        return rows
    finally:
        cursor.close()
        connection.close()