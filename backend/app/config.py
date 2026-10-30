"""Sozlamalar muhit oʻzgaruvchilaridan (environment variables) oʻqiladi.

Mahalliy ishga tushirishda .env.example faylini .env ga nusxalab, qiymatlarni oʻzgartiring.
"""
import os
from dataclasses import dataclass, field


def _load_dotenv(path: str = ".env") -> None:
    """Oddiy .env oʻquvchi: KEY=VALUE qatorlari (qoʻshimcha kutubxonasiz)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "World Cinema API"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./world_cinema.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-only-change-me")
    token_minutes: int = int(os.getenv("TOKEN_MINUTES", "10080"))  # 7 kun
    cors_origins: list[str] = field(
        default_factory=lambda: _list(
            "CORS_ORIGINS",
            "https://butayorovkaramatullo-cloud.github.io,http://localhost:8000,http://127.0.0.1:8000,http://127.0.0.1:5500",
        )
    )
    admin_email: str | None = os.getenv("ADMIN_EMAIL") or None
    admin_password: str | None = os.getenv("ADMIN_PASSWORD") or None
    seed_demo_data: bool = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"
    # Toʻlov provayderi: "mock" (sinov uchun), keyinchalik "click" yoki "payme"
    payment_provider: str = os.getenv("PAYMENT_PROVIDER", "mock").lower()
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


settings = Settings()

if settings.secret_key == "dev-only-change-me" and os.getenv("ENV", "dev") == "production":
    raise RuntimeError("Production muhitida SECRET_KEY ni albatta oʻrnating.")
