"""AgentShield configuration loaded from environment."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "agentshield"
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str
    REDIS_URL: str | None = None

    API_KEY_PREFIX: str = "ash_live_"
    ADMIN_BOOTSTRAP_SECRET: str = "change-me"

    IDEMPOTENCY_TTL: int = 86400
    APPROVAL_WAIT_TIMEOUT: int = 15

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"


settings = Settings()
