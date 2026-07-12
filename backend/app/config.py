from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    environment: str = "development"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"
    internal_secret: str = "dev_internal_secret_change_in_production"
    journal_encryption_key: str = ""  # base64-encoded 32 bytes
    anthropic_api_key: str = ""
    privacy_enabled: bool = False
    privacy_epsilon: float = 1.0  # ε-DP budget; lower = more privacy, more noise

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
