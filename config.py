import os
from functools import lru_cache

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai

load_dotenv()


class Settings:
    MONGODB_URI: str
    MONGODB_DB: str
    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"

    def __init__(self) -> None:
        self.MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://owncoach:Test@123@owncoach.hisqa9s.mongodb.net/?appName=owncoach")
        self.MONGODB_DB = os.getenv("MONGODB_DB", "fitnesswon")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be set in .env")

        # New google-genai SDK client
        self.gemini_client = genai.Client(api_key=self.GEMINI_API_KEY)
        print(f"✅ Gemini client ready — model: {self.GEMINI_MODEL}")

    def get_mongo_client(self) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(self.MONGODB_URI)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
