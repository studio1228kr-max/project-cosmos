from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── 서비스 식별 ──────────────────────────────────────────
    SERVICE_NAME: str = "hephaestus"
    SERVICE_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"

    # ── 네트워킹 ─────────────────────────────────────────────
    PORT: int = 8000
    COSMOS_INTERNAL_URL: str = "http://project-cosmos.railway.internal:8000"

    # ── 엔진 기본값 ──────────────────────────────────────────
    AS_OF_FUTURE_TOLERANCE_SEC: int = 300
    ENFORCE_DOWNSIDE_FIRST: bool = True
    AUTO_DOWNGRADE_UNVERIFIED: bool = True

    # ── 런 로그 ──────────────────────────────────────────────
    RUN_LOG_MAX_IN_MEMORY: int = 1000


settings = Settings()
