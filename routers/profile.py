from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class ProfileCreate(BaseModel):
    user_id: str
    name: str
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    goal: str
    fitness_level: str
    dietary_preference: str
    target_weight_kg: float
    timeline_weeks: int
    activity_factor: float = 1.4
    injuries: Optional[str] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    fitness_level: Optional[str] = None
    dietary_preference: Optional[str] = None
    target_weight_kg: Optional[float] = None
    timeline_weeks: Optional[int] = None
    activity_factor: Optional[float] = None
    injuries: Optional[str] = None


class CheckInCreate(BaseModel):
    mood: str
    energy: str
    sleep_hours: float
    stress_level: str
    soreness: str
    adherence: str
    notes: Optional[str] = None


@router.get("/{user_id}")
async def get_profile(user_id: str):
    db = await get_db()
    doc = await db.user_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc


@router.post("")
async def create_or_update_profile(profile: ProfileCreate):
    db = await get_db()
    data = profile.dict()
    # upsert: update if exists, insert if not
    await db.user_profiles.update_one(
        {"user_id": profile.user_id},
        {"$set": data},
        upsert=True,
    )
    doc = await db.user_profiles.find_one({"user_id": profile.user_id}, {"_id": 0})
    return doc


@router.put("/{user_id}")
async def update_profile(user_id: str, profile: ProfileUpdate):
    db = await get_db()
    update_data = {k: v for k, v in profile.dict(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.user_profiles.update_one({"user_id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    doc = await db.user_profiles.find_one({"user_id": user_id}, {"_id": 0})
    return doc


@router.post("/{user_id}/checkin")
async def create_checkin(user_id: str, payload: CheckInCreate):
    from datetime import date
    db = await get_db()
    data = payload.dict()
    data["user_id"] = user_id
    data["date"] = date.today().isoformat()
    await db.check_ins.insert_one(data)
    data.pop("_id", None)
    return data


@router.get("/{user_id}/checkins")
async def get_recent_checkins(user_id: str):
    db = await get_db()
    cursor = db.check_ins.find({"user_id": user_id}, {"_id": 0}).sort("date", -1).limit(30)
    return await cursor.to_list(length=30)
