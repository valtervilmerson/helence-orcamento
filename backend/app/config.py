from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    database_path: str = "./data/helence.db"
    uploads_dir: str = "./data/uploads"
    max_upload_size_mb: int = 50
    secret_key: str = "change-me-in-production"
    session_cookie_secure: bool = False
    log_level: str = "INFO"
    cors_allowed_origins: str = "http://localhost:5173"
    backup_dir: str = "./backups"
    admin_seed_key: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
