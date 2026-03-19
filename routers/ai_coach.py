import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from database import get_db

router = APIRouter()


# ── Request models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    context_type: Optional[str] = "general"

class WorkoutPlanRequest(BaseModel):
    user_id: str

class DietPlanRequest(BaseModel):
    user_id: str

class BodyAnalysisRequest(BaseModel):
    user_id: str

class SupplementAdviceRequest(BaseModel):
    user_id: str
    goal_specific: bool = True


# ── Science-backed system prompt ────────────────────────────────────────────

COACH_SYSTEM = """You are FitnessWon, an elite evidence-based AI fitness coach.

Your answers are grounded ONLY in peer-reviewed research from:
- ISSN (International Society of Sports Nutrition) Position Stands
- NSCA (National Strength and Conditioning Association) guidelines
- ACSM (American College of Sports Medicine) exercise prescriptions
- PubMed / MEDLINE sports science studies
- UK Sport and Sport England athlete development research
- NHS (UK) nutritional guidelines
- Journal of Strength and Conditioning Research
- Sports Medicine journal

Rules you ALWAYS follow:
1. Every recommendation must be backed by evidence — never give bro-science
2. Cite specific study authors + year or ISSN/NSCA/ACSM position stand name
3. Always give SPECIFIC numbers — sets, reps, rest, calories, macro grams
4. Tailor every answer to the athlete's exact profile, goal and fitness level
5. Be direct, motivating and coach-like — not robotic or generic
6. If asked about something outside fitness/health, politely redirect"""


# ── AI engine — Groq primary, Gemini fallback ───────────────────────────────

async def _call_ai(prompt: str, system: str = None, max_tokens: int = 2048) -> str:
    """Try Groq first (free, fast), fall back to Gemini."""
    if settings.GROQ_API_KEY:
        try:
            return await _groq(prompt, system, max_tokens=max_tokens)
        except Exception as e:
            print(f"Groq failed: {e}, trying Gemini...")

    # Gemini fallback
    if settings.GEMINI_API_KEY:
        return await _gemini(prompt, system)

    raise HTTPException(status_code=500, detail="No AI API key configured. Add GROQ_API_KEY or GEMINI_API_KEY to .env")


async def _call_ai_chat(system: str, history: list, message: str) -> str:
    """Try Groq first for chat, fall back to Gemini."""
    if settings.GROQ_API_KEY:
        try:
            msgs = [{"role": "system", "content": system}]
            for h in history:
                msgs.append({
                    "role": "assistant" if h["role"] == "assistant" else "user",
                    "content": h["content"]
                })
            msgs.append({"role": "user", "content": message})
            return await _groq_chat(msgs)
        except Exception as e:
            print(f"Groq chat failed: {e}, trying Gemini...")

    # Gemini fallback
    if settings.GEMINI_API_KEY:
        return await _gemini_chat(system, history, message)

    raise HTTPException(status_code=500, detail="No AI API key configured.")


async def _groq(prompt: str, system: str = None, max_tokens: int = 2048) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await _groq_chat(msgs, max_tokens=max_tokens)


async def _groq_chat(messages: list, max_tokens: int = 2048) -> str:
    import httpx
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _gemini(prompt: str, system: str = None) -> str:
    loop = asyncio.get_event_loop()

    def _run():
        from google.genai import types
        full_prompt = (system + "\n\n" + prompt) if system else prompt
        config = types.GenerateContentConfig(temperature=0.7, max_output_tokens=2048)
        response = settings.gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=full_prompt,
            config=config,
        )
        return response.text

    try:
        return await loop.run_in_executor(None, _run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")


async def _gemini_chat(system: str, history: list, message: str) -> str:
    loop = asyncio.get_event_loop()

    def _run():
        from google.genai import types
        contents = []
        for h in history:
            role = "model" if h["role"] == "assistant" else "user"
            contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.7,
            max_output_tokens=2048,
        )
        response = settings.gemini_client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )
        return response.text

    try:
        return await loop.run_in_executor(None, _run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")


def _clean_json(text: str) -> str:
    text = text.strip()
    # Strip markdown fences
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    # Find the first { and last } to extract only the JSON object
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        text = text[start:end+1]
    return text


async def _load_user_profile(user_id: str) -> dict:
    db = await get_db()
    doc = await db.user_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found. Please complete onboarding first.")
    return doc


async def _load_chat_history(user_id: str, limit: int = 10) -> list:
    db = await get_db()
    cursor = db.chat_history.find(
        {"user_id": user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    data = await cursor.to_list(length=limit)
    return list(reversed(data))


def _profile_summary(p: dict) -> str:
    return (
        f"Name: {p.get('name')} | Age: {p.get('age')} | Gender: {p.get('gender')} | "
        f"Height: {p.get('height_cm')}cm | Weight: {p.get('weight_kg')}kg | "
        f"Goal: {p.get('goal')} | Level: {p.get('fitness_level')} | "
        f"Diet: {p.get('dietary_preference')} | "
        f"Target: {p.get('target_weight_kg')}kg in {p.get('timeline_weeks')} weeks | "
        f"Injuries: {p.get('injuries') or 'None'}"
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat_with_coach(payload: ChatRequest):
    profile = await _load_user_profile(payload.user_id)
    history = await _load_chat_history(payload.user_id, limit=10)

    system = COACH_SYSTEM + "\n\nAthlete Profile: " + _profile_summary(profile)
    history_dicts = [{"role": h["role"], "content": h["content"]} for h in history]

    reply = await _call_ai_chat(system, history_dicts, payload.message)

    db = await get_db()
    now = datetime.utcnow().isoformat()
    await db.chat_history.insert_one({
        "user_id": payload.user_id, "role": "user",
        "content": payload.message, "context_type": payload.context_type,
        "created_at": now,
    })
    await db.chat_history.insert_one({
        "user_id": payload.user_id, "role": "assistant",
        "content": reply, "context_type": payload.context_type,
        "created_at": now,
    })
    return {"reply": reply}


@router.get("/history/{user_id}")
async def get_chat_history(user_id: str):
    return await _load_chat_history(user_id, limit=20)


@router.post("/generate-workout-plan")
async def generate_workout_plan(payload: WorkoutPlanRequest):
    profile = await _load_user_profile(payload.user_id)

    prompt = (
        "Generate a complete science-based 7-day workout plan. "
        "Apply NSCA periodisation and ACSM exercise prescription guidelines.\n\n"
        "Athlete: " + _profile_summary(profile) + "\n\n"
        "CRITICAL: Return ONLY a raw JSON object. "
        "No markdown fences. No explanation text. No ```json. "
        "Your entire response must start with { and end with }\n\n"
        "Required JSON structure:\n"
        '{"days":[{"day":"Monday","focus":"Upper Body Hypertrophy","exercises":'
        '[{"name":"Bench Press","sets":4,"reps":"8-10","rest_seconds":90,'
        '"rpe":7,"muscle":"Chest","technique_tips":"Retract scapula, 3s eccentric"}]}]}'
    )

    text = _clean_json(await _call_ai(prompt, COACH_SYSTEM))

    try:
        parsed = json.loads(text)
    except Exception:
        raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {text[:300]}")

    db = await get_db()
    await db.workout_plans.insert_one({
        "user_id": payload.user_id,
        "plan_json": text,
        "created_at": datetime.utcnow().isoformat(),
    })
    return {"user_id": payload.user_id, "plan": text}


@router.post("/generate-diet-plan")
async def generate_diet_plan(payload: DietPlanRequest):
    profile = await _load_user_profile(payload.user_id)

    weight = float(profile.get("weight_kg") or 70)
    height = float(profile.get("height_cm") or 170)
    age = int(profile.get("age") or 25)
    gender = str(profile.get("gender") or "male").lower()
    activity_factor = float(profile.get("activity_factor") or 1.4)

    bmr = (10 * weight + 6.25 * height - 5 * age + 5) if gender == "male" \
          else (10 * weight + 6.25 * height - 5 * age - 161)
    tdee = round(bmr * activity_factor)

    prompt = (
        "Generate a science-based 7-day personalised meal plan. "
        "Apply ISSN nutritional guidelines. "
        "Protein target: 1.6-2.2g/kg bodyweight per ISSN 2017 position stand. "
        "Adjust total calories for goal.\n\n"
        "Athlete: " + _profile_summary(profile) + "\n"
        "Calculated TDEE: " + str(tdee) + " kcal/day\n\n"
        "CRITICAL: Return ONLY a raw JSON object. "
        "No markdown fences. No explanation text. No ```json. "
        "Your entire response must start with { and end with }\n\n"
        "Keep meal items concise — max 4 items per meal, max 4 meals per day. "
        "Required JSON structure:\n"
        '{"tdee":' + str(tdee) + ',"days":[{"day":"Monday","meals":'
        '[{"time":"08:00","name":"Breakfast",'
        '"items":[{"food":"Oats","grams":80},{"food":"Whey Protein","grams":30}],'
        '"macros":{"protein":35,"carbs":60,"fats":8,"calories":456}}],'
        '"total_macros":{"protein":175,"carbs":220,"fats":65,"calories":' + str(tdee) + '}}]}'
    )

    text = _clean_json(await _call_ai(prompt, COACH_SYSTEM, max_tokens=4096))

    try:
        json.loads(text)
    except Exception:
        # Retry with a simplified prompt requesting fewer details
        print("Diet plan JSON parse failed, retrying with simplified prompt...")
        simple_prompt = (
            "Generate a 7-day meal plan JSON for this athlete.\n"
            "Athlete: " + _profile_summary(profile) + "\n"
            "TDEE: " + str(tdee) + " kcal\n\n"
            "Rules: Return ONLY raw JSON. No markdown. Start with { end with }.\n"
            "Exactly 3 meals per day (Breakfast, Lunch, Dinner). Max 3 food items per meal.\n"
            "JSON format: {\"tdee\":" + str(tdee) + ",\"days\":[{\"day\":\"Monday\","
            "\"meals\":[{\"time\":\"08:00\",\"name\":\"Breakfast\","
            "\"items\":[{\"food\":\"Oats\",\"grams\":80}],"
            "\"macros\":{\"protein\":30,\"carbs\":55,\"fats\":8,\"calories\":410}}],"
            "\"total_macros\":{\"protein\":150,\"carbs\":200,\"fats\":60,\"calories\":" + str(tdee) + "}}]}"
        )
        text = _clean_json(await _call_ai(simple_prompt, max_tokens=4096))
        try:
            json.loads(text)
        except Exception:
            raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {text[:300]}")

    db = await get_db()
    await db.diet_plans.insert_one({
        "user_id": payload.user_id,
        "plan_json": text,
        "tdee": tdee,
        "created_at": datetime.utcnow().isoformat(),
    })
    return {"user_id": payload.user_id, "tdee": tdee, "plan": text}


@router.post("/body-analysis")
async def body_analysis(payload: BodyAnalysisRequest):
    profile = await _load_user_profile(payload.user_id)
    db = await get_db()

    measurements = await db.body_measurements.find(
        {"user_id": payload.user_id}, {"_id": 0}
    ).sort("date", -1).to_list(20)

    check_ins = await db.check_ins.find(
        {"user_id": payload.user_id}, {"_id": 0}
    ).sort("date", -1).to_list(20)

    weights = await db.weight_history.find(
        {"user_id": payload.user_id}, {"_id": 0}
    ).sort("date", -1).to_list(20)

    prompt = (
        "Analyse this athlete's body composition progress. "
        "Use evidence-based benchmarks:\n"
        "- Safe fat loss rate: 0.5-1% bodyweight per week (Helms et al. 2014)\n"
        "- Natural muscle gain: 0.5-2 lbs/month (NSCA guidelines)\n\n"
        "Athlete: " + _profile_summary(profile) + "\n"
        "Weight history (newest first): " + str(weights) + "\n"
        "Body measurements: " + str(measurements) + "\n"
        "Daily check-ins: " + str(check_ins) + "\n\n"
        "Structure your response with these exact sections:\n"
        "## Progress Analysis\n"
        "## On Track Assessment\n"
        "## Key Issues Found\n"
        "## Top 5 Action Steps\n\n"
        "Be specific with numbers and cite studies where relevant."
    )

    analysis = await _call_ai(prompt, COACH_SYSTEM)
    return {"user_id": payload.user_id, "analysis": analysis}


@router.post("/supplement-advice")
async def supplement_advice(payload: SupplementAdviceRequest):
    profile = await _load_user_profile(payload.user_id)
    goal = str(profile.get("goal") or "general fitness")

    prompt = (
        "Give evidence-based supplement recommendations. "
        "Only include supplements with Grade A or B evidence per ISSN classification. "
        "Cite specific ISSN Position Stand or PubMed study for each supplement.\n\n"
        "Athlete: " + _profile_summary(profile) + "\n"
        "Goal: " + goal + "\n\n"
        "CRITICAL: Return ONLY a raw JSON object. "
        "No markdown fences. No explanation text. No ```json. "
        "Your entire response must start with { and end with }\n"
        "Include 4-6 supplements maximum to keep the response short.\n\n"
        "Required JSON structure:\n"
        '{"goal":"' + goal + '","supplements":['
        '{"name":"Creatine Monohydrate","primary_goal":"Strength and power",'
        '"evidence_level":"A","dosage":"3-5g daily, no loading needed",'
        '"timing":"Any time of day, consistency matters most",'
        '"safety_notes":"Safe for healthy adults. Adequate hydration recommended.",'
        '"citations":["Buford et al. 2007 - ISSN Position Stand on Creatine",'
        '"Kreider et al. 2017 - Journal of International Society of Sports Nutrition"]}]}'
    )

    text = _clean_json(await _call_ai(prompt, COACH_SYSTEM, max_tokens=2048))

    # Validate JSON — retry with a simpler prompt if it fails
    import json as _json
    try:
        _json.loads(text)
    except Exception:
        print("Supplement advice JSON parse failed, retrying with simpler prompt...")
        simple_prompt = (
            "Return supplement advice JSON for this athlete.\n"
            "Athlete goal: " + goal + "\n"
            "Return ONLY raw JSON, no markdown. Start with { end with }.\n"
            "Max 4 supplements. Use this exact format:\n"
            '{"goal":"' + goal + '","supplements":['
            '{"name":"Creatine","primary_goal":"Strength","evidence_level":"A",'
            '"dosage":"3-5g daily","timing":"Any time","safety_notes":"Safe",'
            '"citations":["Kreider et al. 2017"]}]}'
        )
        text = _clean_json(await _call_ai(simple_prompt, max_tokens=2048))
        try:
            _json.loads(text)
        except Exception:
            raise HTTPException(status_code=500, detail="AI could not generate valid supplement advice. Please try again.")

    return {"user_id": payload.user_id, "recommendations": text}
