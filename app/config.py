"""Notification microservice configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    qstash_token: str = ""
    qstash_current_signing_key: str = ""
    qstash_next_signing_key: str = ""
    api_key: str = ""
    # Full URL of this service (used as QStash callback URL)
    service_url: str = "http://localhost:8001"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
