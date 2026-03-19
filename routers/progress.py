from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timedelta
from database import get_db

router = APIRouter()


class MeasurementCreate(BaseModel):
    user_id: str
    neck_cm: Optional[float] = None
    shoulders_cm: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hips_cm: Optional[float] = None
    thigh_cm: Optional[float] = None
    arm_cm: Optional[float] = None
    body_fat_pct: Optional[float] = None
    notes: Optional[str] = None


class WeightEntry(BaseModel):
    user_id: str
    weight_kg: float


@router.post("/measurements")
async def create_measurements(payload: MeasurementCreate):
    db = await get_db()
    data = payload.dict()
    data["date"] = date.today().isoformat()
    await db.body_measurements.insert_one(data)
    data.pop("_id", None)
    return data


@router.get("/measurements/{user_id}")
async def get_measurements_history(user_id: str):
    db = await get_db()
    cursor = db.body_measurements.find({"user_id": user_id}, {"_id": 0}).sort("date", -1)
    return await cursor.to_list(length=100)


@router.post("/weight")
async def log_weight(payload: WeightEntry):
    db = await get_db()
    data = payload.dict()
    data["date"] = date.today().isoformat()
    await db.weight_history.insert_one(data)
    data.pop("_id", None)
    return data


@router.get("/stats/{user_id}")
async def get_progress_stats(user_id: str):
    db = await get_db()

    # Weight trend
    cursor = db.weight_history.find({"user_id": user_id}, {"_id": 0}).sort("date", 1)
    weight_trend = await cursor.to_list(length=200)

    # Measurement changes
    cursor2 = db.body_measurements.find({"user_id": user_id}, {"_id": 0}).sort("date", 1)
    measurements = await cursor2.to_list(length=200)

    measurement_changes = {}
    keys = ["neck_cm", "shoulders_cm", "chest_cm", "waist_cm", "hips_cm", "thigh_cm", "arm_cm", "body_fat_pct"]
    if len(measurements) >= 2:
        first = measurements[0]
        last = measurements[-1]
        for k in keys:
            if first.get(k) is not None and last.get(k) is not None:
                measurement_changes[f"{k}_change"] = float(last[k]) - float(first[k])
            else:
                measurement_changes[f"{k}_change"] = None
    else:
        for k in keys:
            measurement_changes[f"{k}_change"] = None

    # Streak
    cursor3 = db.check_ins.find({"user_id": user_id}, {"_id": 0, "date": 1}).sort("date", -1)
    checkin_docs = await cursor3.to_list(length=200)
    dates = {row["date"] for row in checkin_docs}
    streak_days = 0
    current = date.today()
    while current.isoformat() in dates:
        streak_days += 1
        current = current - timedelta(days=1)

    progress_score = min(100, streak_days * 5 + len(measurements) * 2)

    return {
        "weight_trend": weight_trend,
        "measurement_changes": measurement_changes,
        "streak_days": streak_days,
        "progress_score": progress_score,
        "milestone_achieved": [],
    }
