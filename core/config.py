from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    RESET_TOKEN_EXPIRES_MINUTES: int = 1440 
    JWT_SECRET: str = "change-this-development-secret-before-production"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRES_DAYS: int = 30
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    SMTP_FROM_NAME: str = "Evvent"

    MAILJET_APIKEY: str | None = None
    MAILJET_SECRET_KEY: str | None = None
    MAILJET_FROM_EMAIL: str = "no-reply@evvent.com"
    MAILJET_FROM_NAME: str = "Evvent"

    PAYSTACK_SECRET_KEY: str | None = None
    PAYSTACK_BASE_URL: str = "https://evvnt-ticketer.netlify.app/payments"
    FRONTEND_BASE_URL: str = "https://evvnt-ticketer.netlify.app"

    REDIS_URL: str = "redis://localhost:6379/0"

    # Fee (in kobo) charged to an organizer to feature their event.
    # Default: ₦5,000 = 500,000 kobo
    FEATURE_FEE: int = 500000

    # Admin commission rate on every paid ticket sale (0.05 = 5%)
    ADMIN_COMMISSION_RATE: float = 0.05

    model_config = SettingsConfigDict(
    env_file=Path(__file__).resolve().parent.parent / ".env",
    env_file_encoding="utf-8",
    extra="ignore",
)

settings = Settings()

