from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class CompleteDayPayload(BaseModel):
    day: str
    plan_id: Optional[str] = None


@router.get("/workout/{user_id}")
async def get_latest_workout_plan(user_id: str):
    db = await get_db()
    doc = await db.workout_plans.find_one({"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)])
    return doc or {}


@router.get("/diet/{user_id}")
async def get_latest_diet_plan(user_id: str):
    db = await get_db()
    doc = await db.diet_plans.find_one({"user_id": user_id}, {"_id": 0}, sort=[("created_at", -1)])
    return doc or {}


@router.put("/workout/{user_id}/complete-day")
async def complete_workout_day(user_id: str, payload: CompleteDayPayload):
    from datetime import datetime
    db = await get_db()
    data = {
        "user_id": user_id,
        "day": payload.day,
        "completed_at": datetime.utcnow().isoformat(),
    }
    await db.workout_plan_completions.insert_one(data)
    data.pop("_id", None)
    return data
