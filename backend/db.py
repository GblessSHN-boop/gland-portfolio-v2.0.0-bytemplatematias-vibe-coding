import mysql.connector
from mysql.connector import Error

try:
    import config
except ImportError as exc:
    raise RuntimeError(
        "config.py tidak ditemukan. Copy config.example.py menjadi config.py lalu sesuaikan koneksi database."
    ) from exc


def get_connection(use_database=True):
    connection_config = {
        "host": config.DB_HOST,
        "port": config.DB_PORT,
        "user": config.DB_USER,
        "password": config.DB_PASSWORD,
        "autocommit": False,
    }

    if use_database:
        connection_config["database"] = config.DB_NAME

    return mysql.connector.connect(**connection_config)


def test_connection():
    connection = None

    try:
        connection = get_connection(use_database=True)
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT DATABASE() AS database_name, NOW() AS server_time")
        row = cursor.fetchone()
        cursor.close()

        return {
            "success": True,
            "database": row["database_name"],
            "server_time": str(row["server_time"]),
        }
    except Error as error:
        return {
            "success": False,
            "error": str(error),
        }
    finally:
        if connection and connection.is_connected():
            connection.close()