"""
TallySync Manager — Application Configuration
Version : 1.0.0
Build   : 20260217.001
"""

from __future__ import annotations
import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings


# ─── Version Info ────────────────────────────────────────────────────────────

APP_NAME    = "TallySync Manager"
APP_VERSION = "1.0.0"
APP_BUILD   = "20260217.001"
APP_AUTHOR  = "TallySync"


# ─── Paths ───────────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).resolve().parent          # server/
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "tallysync.db"
LOG_DIR     = DATA_DIR / "logs"
API_KEY_FILE = DATA_DIR / "api_key.txt"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ─── Settings (reads from .env) ──────────────────────────────────────────────

class Settings(BaseSettings):
    host: str           = "0.0.0.0"
    port: int           = 8000
    debug: bool         = False
    log_level: str      = "INFO"
    cors_origins: str   = "*"               # comma-separated for production
    default_sync_interval_minutes: int = 5

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_FORMAT = "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format=LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("tallysync")
logger.info("TallySync Manager v%s (build %s) starting up", APP_VERSION, APP_BUILD)
