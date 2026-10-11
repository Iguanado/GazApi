import os
from datetime import datetime

import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, FiniteFloat

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


def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )



@app.post("/devices/{device_id}/pokazaniya", status_code=201)
def create_pokazaniya(device_id: str, payload: PokazaniyaCreate):
    with get_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO pokazaniya (device_id, x, y, z) VALUES (%s, %s, %s, %s) RETURNING id, device_id, vremya_zapisi, x, y, z",
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


@app.get("/devices/{device_id}/statistics")
def read_statistics(params: ReadStatistic = Depends()):  # noqa: B008
    device_id = params.device_id
    start = params.start
    end = params.end

    if start is not None and start.utcoffset() is None:
        raise HTTPException(
            status_code=422,
            detail="start должен содержать часовой пояс",
        )

    if end is not None and end.utcoffset() is None:
        raise HTTPException(
            status_code=422,
            detail="end должен содержать часовой пояс",
        )

    if start is not None and end is not None and start >= end:
        raise HTTPException(
            status_code=422,
            detail="start должен быть раньше end",
        )

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






# @app.get("/health")
# def health():
#     return {"status": "ok"}

# @app.get("/health/db")
# def health_db():
#     with get_connection() as connection, connection.cursor() as cursor:
#         cursor.execute("SELECT 1")
#         result = cursor.fetchone()

#     return {"database": "ok", "result":result[0]}
