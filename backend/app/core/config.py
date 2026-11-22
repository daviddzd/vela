"""Application settings, read from environment variables (see .env.example)."""
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings

# The whole operational app runs on wall-clock time in Mexico City (CLAUDE.md rule 2).
MEXICO_CITY = ZoneInfo("America/Mexico_City")


class Settings(BaseSettings):
    # Connection as role vela_api: NOT the table owner, so row-level security applies.
    database_url: str
    jwt_secret: str
    jwt_hours: int = 8
    public_base_url: str = "http://localhost:8080"
    # Failed login attempts allowed per IP per minute (docs/spec/02_arquitectura.md).
    login_attempts_per_minute: int = 5

    @property
    def cookie_secure(self) -> bool:
        """Send the cookie only over HTTPS when the public URL is HTTPS (Cloudflare tunnel)."""
        return self.public_base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
