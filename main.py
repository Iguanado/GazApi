import psycopg
from fastapi import Depends, FastAPI, HTTPException

from database import (
    insert_device,
    insert_pokazaniya,
    insert_user,
    select_device_statistics,
    select_user_devices_statistics,
    select_user_statistics,
)
from schemas import (
    DeviceCreate,
    PokazaniyaCreate,
    ReadStatistic,
    UserCreate,
    UserStatistic,
)

app = FastAPI()


@app.post("/devices/{device_id}/pokazaniya", status_code=201, tags=["Показания"])
def create_pokazaniya(device_id: str, payload: PokazaniyaCreate):
    row = insert_pokazaniya(device_id, payload.x, payload.y, payload.z)

    if row is None:
        raise HTTPException(status_code=404, detail="Устройство не зарегистрировано")

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

    row = select_device_statistics(device_id, start, end)

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
    row = insert_user(payload.name)

    return {
        "id": row[0],
        "name": row[1],
    }


@app.post("/users/{user_id}/devices", status_code=201, tags=["Устройства"])
def create_device(user_id: int, payload: DeviceCreate):
    device_id = payload.device_id.strip()

    try:
        row = insert_device(user_id, device_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

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

    row = select_user_statistics(user_id, start, end)

    if row is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

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

    rows = select_user_devices_statistics(user_id, start, end)

    if rows is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

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
