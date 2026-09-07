import os
import secrets
import warnings
from pydantic_settings import BaseSettings


def _resolve_jwt_secret() -> str:
    """
    Reads JWT_SECRET strictly from the environment. There is NO hardcoded
    secret compiled into the source anymore - a static secret checked into
    a public/shared repository means anyone who has ever seen the source
    (or its git history) can forge valid tokens for any user, including
    ADMIN, forever (until the secret is rotated).

    If the environment variable is absent:
      - When ENVIRONMENT=production, refuse to start outright. A silent
        random fallback in production would issue tokens that all become
        invalid on the next restart/redeploy with no visible error until
        users start getting logged out - fail loudly at boot instead.
      - Otherwise (local dev), generate a cryptographically random secret
        for THIS PROCESS ONLY, so `uvicorn` dev runs still work out of the
        box. The secret is different every restart, so no one can rely on
        it being stable, and a loud warning is emitted so this is never
        mistaken for a real deployment configuration.
    """
    env_secret = os.getenv("JWT_SECRET")
    if env_secret:
        return env_secret

    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment == "production":
        raise RuntimeError(
            "JWT_SECRET environment variable is required in production and was not set. "
            "Set a strong, random secret (e.g. `openssl rand -hex 32`) before starting the server."
        )

    warnings.warn(
        "JWT_SECRET is not set in the environment. Generating a random "
        "in-memory secret for this process only - all issued tokens will "
        "become invalid on restart, and this is NOT safe for production. "
        "Set the JWT_SECRET environment variable before deploying.",
        RuntimeWarning,
    )
    return secrets.token_hex(32)


class Settings(BaseSettings):
    PROJECT_NAME: str = "HawkerCredit Quantum"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # Optional break-glass bootstrap secret for the first internal staff account.
    # Never commit a real value.
    STAFF_BOOTSTRAP_SECRET: str = os.getenv("STAFF_BOOTSTRAP_SECRET", "")

    # Security: JWT secret MUST come from the environment in real
    # deployments (see _resolve_jwt_secret docstring above).
    JWT_SECRET: str = _resolve_jwt_secret()
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database (Aiven PostgreSQL or local fallback SQLite)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./hawkercredit.db"
    )

    # CORS
    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000"
        ).split(",")
        if origin.strip()
    ]

    class Config:
        case_sensitive = True


settings = Settings()
