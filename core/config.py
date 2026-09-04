from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./event_ticketing.db"
    RESET_TOKEN_EXPIRES_MINUTES: int = 15
    JWT_SECRET: str = "change-this-development-secret-before-production"
    ACCESS_TOKEN_EXPIRES_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
