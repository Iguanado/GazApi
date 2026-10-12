import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def insert_pokazaniya(device_id, x, y, z):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT device_id FROM devices WHERE device_id = %s", (device_id,))

        if cursor.fetchone() is None:
            return None

        cursor.execute(
            """
            INSERT INTO pokazaniya (device_id, x, y, z)
            VALUES (%s, %s, %s, %s)
            RETURNING id, device_id, vremya_zapisi, x, y, z
            """,
            (device_id, x, y, z),
        )

        row = cursor.fetchone()

    return row


def insert_user(name):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO polzovateli (name)
            VALUES (%s)
            RETURNING id, name
            """,
            (name.strip(),),
        )

        row = cursor.fetchone()

    return row


def insert_device(user_id, device_id):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM polzovateli WHERE id = %s", (user_id,))

        if cursor.fetchone() is None:
            return None

        cursor.execute(
            """
            INSERT INTO devices (device_id, user_id)
            VALUES (%s, %s)
            RETURNING device_id, user_id
            """,
            (device_id, user_id),
        )

        row = cursor.fetchone()

    return row


def select_device_statistics(device_id, start, end):
    conditions = ["device_id = %s"]
    sql_params = [device_id]

    if start is not None:
        conditions.append("vremya_zapisi >= %s")
        sql_params.append(start)

    if end is not None:
        conditions.append("vremya_zapisi < %s")
        sql_params.append(end)

    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COUNT(*),
                MIN(x),
                MAX(x),
                COALESCE(SUM(x), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY x),

                MIN(y),
                MAX(y),
                COALESCE(SUM(y), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY y),

                MIN(z),
                MAX(z),
                COALESCE(SUM(z), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY z)
            FROM pokazaniya
            WHERE {" AND ".join(conditions)}
            """,
            sql_params,
        )

        row = cursor.fetchone()

    return row


def select_user_statistics(user_id, start, end):
    conditions = ["d.user_id = %s"]
    sql_params = [user_id]

    if start is not None:
        conditions.append("p.vremya_zapisi >= %s")
        sql_params.append(start)

    if end is not None:
        conditions.append("p.vremya_zapisi < %s")
        sql_params.append(end)

    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM polzovateli WHERE id = %s", (user_id,))

        if cursor.fetchone() is None:
            return None

        cursor.execute(
            f"""
            SELECT
                COUNT(*),
                MIN(p.x),
                MAX(p.x),
                COALESCE(SUM(p.x), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.x),

                MIN(p.y),
                MAX(p.y),
                COALESCE(SUM(p.y), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.y),

                MIN(p.z),
                MAX(p.z),
                COALESCE(SUM(p.z), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.z)
            FROM pokazaniya AS p
            JOIN devices AS d ON p.device_id = d.device_id
            WHERE {" AND ".join(conditions)}
            """,
            sql_params,
        )

        row = cursor.fetchone()

    return row


def select_user_devices_statistics(user_id, start, end):
    join_conditions = ["p.device_id = d.device_id"]
    sql_params = []

    if start is not None:
        join_conditions.append("p.vremya_zapisi >= %s")
        sql_params.append(start)

    if end is not None:
        join_conditions.append("p.vremya_zapisi < %s")
        sql_params.append(end)

    sql_params.append(user_id)

    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id FROM polzovateli WHERE id = %s", (user_id,))

        if cursor.fetchone() is None:
            return None

        cursor.execute(
            f"""
            SELECT
                d.device_id,
                COUNT(p.id),

                MIN(p.x),
                MAX(p.x),
                COALESCE(SUM(p.x), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.x),

                MIN(p.y),
                MAX(p.y),
                COALESCE(SUM(p.y), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.y),

                MIN(p.z),
                MAX(p.z),
                COALESCE(SUM(p.z), 0),
                percentile_cont(0.5) WITHIN GROUP (ORDER BY p.z)
            FROM devices AS d
            LEFT JOIN pokazaniya AS p
                ON {" AND ".join(join_conditions)}
            WHERE d.user_id = %s
            GROUP BY d.device_id
            ORDER BY d.device_id
            """,
            sql_params,
        )

        rows = cursor.fetchall()

    return rows
