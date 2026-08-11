import secrets
import warnings
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRETS = {
    "",
    "your-secret-key-change-in-production",
    "woenv-secret-key-2024-change-in-production",
    "changeme",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "WOEnv Dashboard"
    VERSION: str = "1.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://woenv_user:woenv_pass@localhost:5433/woenv_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT. The default is generated per process: without a configured
    # SECRET_KEY every restart invalidates existing tokens, which is noisy but
    # far safer than shipping a known signing key.
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    # Thirty minutes forced a re-login mid-session with no refresh flow.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # File upload
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if self.SECRET_KEY.strip() in INSECURE_SECRETS:
            warnings.warn(
                "SECRET_KEY is unset or uses a known placeholder. A random key "
                "has been generated for this process, so tokens will not "
                "survive a restart. Set SECRET_KEY in .env for any deployment.",
                RuntimeWarning,
                stacklevel=2,
            )
            object.__setattr__(self, "SECRET_KEY", secrets.token_urlsafe(48))


settings = Settings()
