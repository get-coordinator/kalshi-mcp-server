"""Configuration loading for the server."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass
class Settings:
    """Runtime configuration loaded from environment or files."""
    base_url: str
    timeout_seconds: float
    api_key_id: str | None = None
    api_key_path: str | None = None
    api_key_pem: str | None = None


def _load_dotenv_into_environment(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env if variables are not already set."""
    if not dotenv_path.is_file():
        return

    try:
        lines = dotenv_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
            cleaned = cleaned[1:-1]

        os.environ[key] = cleaned


def _optional_str_env(name: str) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    normalized = raw.strip()
    if not normalized:
        return None
    return normalized


def load_settings() -> Settings:
    """Load settings from environment or config files."""
    _load_dotenv_into_environment(Path.cwd() / ".env")

    default_base_url = "https://api.elections.kalshi.com/trade-api/v2"
    base_url = os.getenv("KALSHI_API_BASE_URL", default_base_url).strip().rstrip("/")

    raw_timeout = os.getenv("KALSHI_TIMEOUT_SECONDS", "10")
    try:
        timeout_seconds = float(raw_timeout)
    except ValueError:
        timeout_seconds = 10.0

    if timeout_seconds <= 0:
        timeout_seconds = 10.0

    return Settings(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        api_key_id=_optional_str_env("KALSHI_API_KEY_ID"),
        api_key_path=_optional_str_env("KALSHI_API_KEY_PATH"),
    )
