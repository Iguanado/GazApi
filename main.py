import os
from datetime import datetime

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, FiniteFloat

load_dotenv()
app = FastAPI()


class PokazaniyaCreate(BaseModel):
    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat


class ReadStatistic(BaseModel):
    device_id: str
    start: datetime | None = None
    end: datetime | None = None


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"\S", examples=["Максим"])


class DeviceCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=100, pattern=r"\S", examples=["sensor-1"])


class UserStatistic(BaseModel):
    user_id: int
    start: datetime | None = None
    end: datetime | None = None


def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


@app.post("/devices/{device_id}/pokazaniya", status_code=201, tags=["Показания"])
def create_pokazaniya(device_id: str, payload: PokazaniyaCreate):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute("SELECT device_id FROM devices WHERE device_id = %s", (device_id,))

        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Устройство не зарегистрировано")

        cursor.execute(
            """
            INSERT INTO pokazaniya (device_id, x, y, z)
            VALUES (%s, %s, %s, %s)
            RETURNING id, device_id, vremya_zapisi, x, y, z
            """,
            (device_id, payload.x, payload.y, payload.z),
        )

        row = cursor.fetchone()

    return {
        "id": row[0],
        "device_id": row[1],
        "vremya_zapisi": row[2],
        "x": row[3],
        "y": row[4],
        "z": row[5],
    }


@app.get("/devices/{device_id}/statistics", tags=["Статистика"])
def read_statistics(params: ReadStatistic = Depends()):  # noqa: B008
    device_id = params.device_id
    start = params.start
    end = params.end

    if start is not None and start.utcoffset() is None:
        raise HTTPException(status_code=422, detail="start должен содержать часовой пояс")

    if end is not None and end.utcoffset() is None:
        raise HTTPException(status_code=422, detail="end должен содержать часовой пояс")

    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="start должен быть раньше end")

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

    return {
        "device_id": device_id,
        "x": {
            "count": row[0],
            "min": row[1],
            "max": row[2],
            "sum": row[3],
            "median": row[4],
        },
        "y": {
            "count": row[0],
            "min": row[5],
            "max": row[6],
            "sum": row[7],
            "median": row[8],
        },
        "z": {
            "count": row[0],
            "min": row[9],
            "max": row[10],
            "sum": row[11],
            "median": row[12],
        },
    }


@app.post("/users", status_code=201, tags=["Пользователи"])
def create_user(payload: UserCreate):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO polzovateli (name)
            VALUES (%s)
            RETURNING id, name
            """,
            (payload.name.strip(),),
        )

        row = cursor.fetchone()

    return {
        "id": row[0],
        "name": row[1],
    }


@app.post("/users/{user_id}/devices", status_code=201, tags=["Устройства"])
def create_device(user_id: int, payload: DeviceCreate):
    device_id = payload.device_id.strip()

    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id FROM polzovateli WHERE id = %s", (user_id,))

            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Пользователь не найден")

            cursor.execute(
                """
                INSERT INTO devices (device_id, user_id)
                VALUES (%s, %s)
                RETURNING device_id, user_id
                """,
                (device_id, user_id),
            )

            row = cursor.fetchone()

    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Устройство с таким идентификатором уже существует") from None

    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(status_code=404, detail="Пользователь не найден") from None

    return {
        "device_id": row[0],
        "user_id": row[1],
    }


@app.get("/users/{user_id}/statistics", tags=["Статистика"])
def read_user_statistics(params: UserStatistic = Depends()):  # noqa: B008
    user_id = params.user_id
    start = params.start
    end = params.end

    if start is not None and start.utcoffset() is None:
        raise HTTPException(status_code=422, detail="start должен содержать часовой пояс")

    if end is not None and end.utcoffset() is None:
        raise HTTPException(status_code=422, detail="end должен содержать часовой пояс")

    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="start должен быть раньше end")

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
            raise HTTPException(status_code=404, detail="Пользователь не найден")

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

    return {
        "user_id": user_id,
        "x": {
            "count": row[0],
            "min": row[1],
            "max": row[2],
            "sum": row[3],
            "median": row[4],
        },
        "y": {
            "count": row[0],
            "min": row[5],
            "max": row[6],
            "sum": row[7],
            "median": row[8],
        },
        "z": {
            "count": row[0],
            "min": row[9],
            "max": row[10],
            "sum": row[11],
            "median": row[12],
        },
    }


@app.get("/users/{user_id}/devices/statistics", tags=["Статистика"])
def read_user_devices_statistics(params: UserStatistic = Depends()):  # noqa: B008
    user_id = params.user_id
    start = params.start
    end = params.end

    if start is not None and start.utcoffset() is None:
        raise HTTPException(status_code=422, detail="start должен содержать часовой пояс")

    if end is not None and end.utcoffset() is None:
        raise HTTPException(status_code=422, detail="end должен содержать часовой пояс")

    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="start должен быть раньше end")

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
            raise HTTPException(status_code=404, detail="Пользователь не найден")

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

    devices_statistics = []

    for row in rows:
        devices_statistics.append(
            {
                "device_id": row[0],
                "x": {
                    "count": row[1],
                    "min": row[2],
                    "max": row[3],
                    "sum": row[4],
                    "median": row[5],
                },
                "y": {
                    "count": row[1],
                    "min": row[6],
                    "max": row[7],
                    "sum": row[8],
                    "median": row[9],
                },
                "z": {
                    "count": row[1],
                    "min": row[10],
                    "max": row[11],
                    "sum": row[12],
                    "median": row[13],
                },
            }
        )

    return {
        "user_id": user_id,
        "devices": devices_statistics,
    }
