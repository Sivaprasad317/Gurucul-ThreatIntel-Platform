from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / ".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{Path(__file__).resolve().parents[2] / 'gurucul_threatintel.db'}"
    jwt_secret: str = "replace-with-a-long-random-secret"
    jwt_expire_minutes: int = 480
    admin_email: str = "admin@example.com"
    admin_password: str = "ChangeMe123!"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    demo_mode: bool = False
    seed_demo_data: bool = False
    tor_proxy: str = "socks5://127.0.0.1:9150"
    ransomware_live_api_key: str | None = None
    ransomware_live_api_base_url: str = "https://api-pro.ransomware.live"
    ransomware_live_group_endpoint: str | None = None
    http_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
