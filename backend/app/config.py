from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file via python-dotenv if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    APP_NAME: str = "Revora"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    DATABASE_URL: str = "sqlite:///./revora.db"

    # Razorpay Test Mode Credentials
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # LLM Explanation Agent Configuration
    LLM_PROVIDER: str = "deterministic"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-1.5-flash"

    @property
    def razorpay_key_id(self) -> str:
        """Expose lowercase razorpay_key_id without hardcoding."""
        return self.RAZORPAY_KEY_ID

    @property
    def razorpay_key_secret(self) -> str:
        """Expose lowercase razorpay_key_secret without hardcoding."""
        return self.RAZORPAY_KEY_SECRET

    model_config = SettingsConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
