"""
TallySync Manager — Application Configuration
Version : 1.0.0
Build   : 20260217.001
"""

from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
from pathlib import Path

from pydantic_settings import BaseSettings


# ─── Version Info ────────────────────────────────────────────────────────────

APP_NAME    = "TallySync Manager"
APP_VERSION = "1.0.0"
APP_BUILD   = "20260217.001"
APP_AUTHOR  = "TallySync"


# ─── Paths ───────────────────────────────────────────────────────────────────

# When running as a PyInstaller binary (sys.frozen), store data next to the
# executable so it persists across runs.  When running from source, use the
# traditional server/ directory.
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "tallysync.db"
LOG_DIR     = DATA_DIR / "logs"
API_KEY_FILE = DATA_DIR / "api_key.txt"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)


# ─── Settings (reads from .env) ──────────────────────────────────────────────

class Settings(BaseSettings):
    host: str           = "0.0.0.0"
    port: int           = 8001                  # aligned with frontend default
    debug: bool         = False
    log_level: str      = "INFO"
    cors_origins: str   = "null"                # "null" = file:// + localhost regex covers the rest
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
        RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=5 * 1024 * 1024,   # 5 MB per file
            backupCount=3,               # keep app.log + app.log.1/2/3
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger("tallysync")
logger.info("TallySync Manager v%s (build %s) starting up", APP_VERSION, APP_BUILD)
