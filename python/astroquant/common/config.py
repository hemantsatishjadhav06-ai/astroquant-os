"""Typed configuration (pydantic-settings). No secrets in code — load from env/.env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="AQ_", extra="ignore")

    # --- Postgres / TimescaleDB ---
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_db: str = "astroquant"
    pg_user: str = "astroquant"
    pg_password: str = "astroquant"

    # --- MongoDB ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "astroquant"

    # --- Redis (message bus) ---
    redis_host: str = "localhost"
    redis_port: int = 6379

    # --- Ephemeris ---
    # Optional path to Swiss Ephemeris .se1 data files. If empty, the built-in
    # Moshier model is used (no files, ~0.1" precision for planets) — fine for research.
    ephe_path: str = ""
    ayanamsa: str = "lahiri"  # sidereal mode for Vedic work

    # --- Market data ---
    broker: str = "yfinance"  # yfinance (free fallback) | kite | upstox | smartapi
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
