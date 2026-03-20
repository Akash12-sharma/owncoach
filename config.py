import os
import re
from functools import lru_cache
from urllib.parse import quote_plus

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
        self.MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://owncoach:TestPassword123@owncoach.r1ramvv.mongodb.net/?appName=owncoach")
        self.MONGODB_DB = os.getenv("MONGODB_DB", "fitnesswon")
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be set in .env")

        # New google-genai SDK client
        self.gemini_client = genai.Client(api_key=self.GEMINI_API_KEY)
        print(f"✅ Gemini client ready — model: {self.GEMINI_MODEL}")

    def get_mongo_client(self) -> AsyncIOMotorClient:
    # Hardcode encoded URI directly to avoid parsing issues
        from urllib.parse import quote_plus
    
        user = "owncoach"
        password = quote_plus("Test@123")  # encodes @ to %40
        host = "owncoach.hisqa9s.mongodb.net/?appName=owncoach"
    
        encoded_uri = f"mongodb+srv://{user}:{password}@{host}"
        return AsyncIOMotorClient(encoded_uri)



@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()