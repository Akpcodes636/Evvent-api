from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    RESET_TOKEN_EXPIRES_MINUTES: int = 15
    JWT_SECRET: str = "change-this-development-secret-before-production"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 60

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = "no-reply@evvent.com"
    SMTP_FROM_NAME: str = "Evvent"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
