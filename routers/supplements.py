from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from database import get_db

router = APIRouter()


class SupplementLogCreate(BaseModel):
    user_id: str
    name: str
    dose: float
    unit: str
    timing: str
    notes: Optional[str] = None


@router.post("/log")
async def log_supplement(payload: SupplementLogCreate):
    from datetime import datetime
    db = await get_db()
    data = payload.dict()
    data["created_at"] = datetime.utcnow().isoformat()
    await db.supplement_logs.insert_one(data)
    data.pop("_id", None)
    return data


@router.get("/log/{user_id}")
async def get_supplement_log(user_id: str):
    db = await get_db()
    cursor = db.supplement_logs.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    return await cursor.to_list(length=100)


@router.get("/library")
def supplements_library():
    return [
        {
            "name": "Creatine Monohydrate",
            "category": "Performance",
            "evidence_level": "A",
            "benefits": ["Increases strength and power output", "Supports lean mass gains"],
            "dosage": "3-5 g/day",
            "timing": "Any time of day, ideally with a carb-containing meal",
            "side_effects": "May cause mild water retention; ensure adequate hydration",
            "studies": ["Buford et al., 2007, ISSN Position Stand on Creatine", "Kreider et al., 2017, J Int Soc Sports Nutr"],
        },
        {
            "name": "Whey Protein",
            "category": "Recovery",
            "evidence_level": "A",
            "benefits": ["Supports muscle protein synthesis", "Convenient high-quality protein source"],
            "dosage": "20-40 g per serving",
            "timing": "Around workouts and/or to fill protein gaps",
            "side_effects": "Generally well tolerated; monitor if lactose sensitive",
            "studies": ["Phillips, 2014, Sports Med"],
        },
        {
            "name": "Beta-Alanine",
            "category": "Performance",
            "evidence_level": "A",
            "benefits": ["Improves high-intensity exercise capacity", "Buffers muscular acidosis"],
            "dosage": "3.2-6.4 g/day divided into smaller doses",
            "timing": "Any time, consistency over weeks is key",
            "side_effects": "May cause harmless tingling (paresthesia)",
            "studies": ["Hobson et al., 2012, Amino Acids"],
        },
        {
            "name": "Caffeine",
            "category": "Performance",
            "evidence_level": "A",
            "benefits": ["Increases alertness and focus", "Improves endurance performance"],
            "dosage": "3-6 mg/kg body weight",
            "timing": "30-60 minutes before training",
            "side_effects": "Can disrupt sleep; may increase anxiety",
            "studies": ["Spriet, 2014, Sports Med"],
        },
        {
            "name": "Fish Oil (Omega-3)",
            "category": "Health",
            "evidence_level": "A",
            "benefits": ["Supports cardiovascular health", "May reduce inflammation"],
            "dosage": "1-3 g/day combined EPA+DHA",
            "timing": "With meals",
            "side_effects": "May cause mild GI upset",
            "studies": ["Calder, 2017, Nutrients"],
        },
        {
            "name": "Vitamin D3",
            "category": "Health",
            "evidence_level": "A",
            "benefits": ["Supports bone health and immune function", "May influence muscle function"],
            "dosage": "1000-4000 IU/day",
            "timing": "With a fat-containing meal",
            "side_effects": "High doses long term can cause toxicity",
            "studies": ["Holick, 2007, N Engl J Med"],
        },
        {
            "name": "Ashwagandha",
            "category": "Adaptogen",
            "evidence_level": "B",
            "benefits": ["May reduce stress and anxiety", "Some evidence for strength support"],
            "dosage": "300-600 mg/day of standardized extract",
            "timing": "Once or twice daily, with meals",
            "side_effects": "Generally well tolerated",
            "studies": ["Wankhede et al., 2015, J Int Soc Sports Nutr"],
        },
    ]
