from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import hashlib
import uuid
from database import get_db

router = APIRouter()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/signup")
async def signup(payload: SignupRequest):
    db = await get_db()
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed = _hash_password(payload.password)
    doc = {
        "user_id": user_id,
        "name": payload.name,
        "email": payload.email.lower(),
        "password_hash": hashed,
    }
    await db.users.insert_one(doc)
    return {"user_id": user_id, "email": payload.email.lower(), "name": payload.name}


@router.post("/login")
async def login(payload: LoginRequest):
    db = await get_db()
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user["password_hash"] != _hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user.get("name", ""),
    }


@router.get("/health")
def auth_health():
    return {"status": "ok"}
