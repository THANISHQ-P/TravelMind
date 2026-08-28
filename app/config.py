import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    PLACES_API_KEY: str = os.getenv("PLACES_API_KEY", "")
    ROUTES_API_KEY: str = os.getenv("ROUTES_API_KEY", "")
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
    
    # Run in demo mode if keys are absent
    DEMO_MODE: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
