from datetime import datetime

from pydantic import BaseModel, Field, FiniteFloat


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
