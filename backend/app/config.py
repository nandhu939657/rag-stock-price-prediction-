from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Single .env file lives at the repo root (shared with the frontend - see
# vite.config.ts), not in backend/ - resolve it as an absolute path from this
# file's location so it's found regardless of the working directory uvicorn
# is launched from.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    database_url: str | None = None

    # Groq
    groq_api_key: str
    groq_model: str = "openai/gpt-oss-120b"

    # Market data (Infoway - see app/ingestion/market_data_client.py)
    market_data_api_key: str = ""

    # Firecrawl
    firecrawl_api_key: str = ""

    # Apify
    apify_api_token: str = ""
    # apify/google-search-scraper: official actor, pay-per-usage (not rental-gated),
    # confirmed working - returns Google SERP organic results per query.
    apify_news_actor_id: str = "apify~google-search-scraper"

    # App
    scheduler_interval_minutes: int = 5
    news_rescrape_interval_hours: int = 1
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def has_market_data_key(self) -> bool:
        return bool(self.market_data_api_key and self.market_data_api_key != "REPLACE_ME")

    @property
    def has_firecrawl_key(self) -> bool:
        return bool(self.firecrawl_api_key and self.firecrawl_api_key != "REPLACE_ME")

    @property
    def has_apify_key(self) -> bool:
        return bool(self.apify_api_token and self.apify_api_token != "REPLACE_ME")


@lru_cache
def get_settings() -> Settings:
    return Settings()
