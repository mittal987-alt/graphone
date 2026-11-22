from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GraphOne Intelligence"
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/graphone.db"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    deepseek_api_key: str | None = None
    github_token: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    google_application_credentials: str | None = None
    crawler_concurrency: int = 8
    crawler_timeout_seconds: float = 30
    crawler_max_retries: int = 4
    playwright_enabled: bool = False
    gemini_model: str = "gemini-2.0-flash"
    groq_model: str = "llama-3.3-70b-versatile"
    deepseek_model: str = "deepseek-chat"
    llm_request_timeout_seconds: float = 60
    llm_max_retries: int = 3
    llm_chunk_overlap_tokens: int = 100
    proxy_url: str | None = None
    domain_requests_per_second: float = 1.0
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 60.0
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
