"""
TallySync Manager — FastAPI Application Entry Point
Version : 1.0.0
Build   : 20260217.001
"""

from __future__ import annotations

import logging
import secrets
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import APP_NAME, APP_VERSION, APP_BUILD, DB_PATH, API_KEY_FILE, settings
from database import engine, init_db, SessionLocal
from models.schemas import ConnectionTestResult
from routes import companies, inventory, ledgers, orders, reports, vouchers, events
from sync import start_scheduler, scheduler
from tally_client import TallyClient

logger = logging.getLogger("tallysync.main")

# Loopback addresses — only these get the API key from /api/info
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


# ─── API Key ─────────────────────────────────────────────────────────────────

def _load_or_create_api_key() -> str:
    """Return the persistent API key, generating one on first run."""
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text().strip()
        if key:
            return key
    key = secrets.token_hex(16)   # 32 hex chars
    API_KEY_FILE.write_text(key)
    API_KEY_FILE.chmod(0o600)
    logger.info("Generated new API key — copy it from Settings after first launch")
    return key

_API_KEY: str = _load_or_create_api_key()


def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """FastAPI dependency — validates X-API-Key header on protected routes."""
    if x_api_key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set it in Settings → Backend Server URL.",
        )


# ─── Lifespan (startup / shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialising database...")
    init_db()

    logger.info("Starting sync scheduler...")
    db = SessionLocal()
    try:
        start_scheduler(db)
    finally:
        db.close()

    yield

    # Shutdown
    logger.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown(wait=False)
    logger.info("TallySync Manager stopped.")


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Order and inventory management with Tally Prime sync",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS — allow localhost origins + file:// ("null") + Vercel-hosted frontend
_cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()] \
    if settings.cors_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "Content-Disposition"],
)


# ─── Routes (all protected by API key) ───────────────────────────────────────

_auth = [Depends(verify_api_key)]

app.include_router(companies.router, dependencies=_auth)
app.include_router(inventory.router, dependencies=_auth)
app.include_router(ledgers.router,   dependencies=_auth)
app.include_router(orders.router,    dependencies=_auth)
app.include_router(reports.router,   dependencies=_auth)
app.include_router(vouchers.router,  dependencies=_auth)
# Events (SSE) is intentionally public — EventSource cannot send custom headers
app.include_router(events.router)


# ─── Info Endpoint ────────────────────────────────────────────────────────────

@app.get("/api/info", tags=["meta"])
def app_info(request: Request):
    """Public endpoint — returns app info. API key only included for loopback connections."""
    result = {
        "name":    APP_NAME,
        "version": APP_VERSION,
        "build":   APP_BUILD,
        "db_path": str(DB_PATH),
    }
    # Only expose the key to localhost — prevents LAN attackers from trivially
    # discovering the key by calling a public endpoint.
    client_host = (request.client.host if request.client else "") or ""
    if client_host in _LOOPBACK:
        result["api_key"] = _API_KEY
    return result


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "scheduler_running": scheduler.running}


# ─── DB Backup ───────────────────────────────────────────────────────────────

@app.get("/api/backup", dependencies=[Depends(verify_api_key)], tags=["meta"])
def download_backup(background_tasks: BackgroundTasks):
    """Download a point-in-time copy of the SQLite database."""
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database not found")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"tallysync_backup_{timestamp}.db"

    # Flush WAL into the main DB file so the backup is complete and consistent.
    from sqlalchemy import text as _text
    with engine.connect() as _conn:
        _conn.execute(_text("PRAGMA wal_checkpoint(TRUNCATE)"))

    tmp_dir  = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / filename
    shutil.copy2(DB_PATH, tmp_path)

    # Schedule temp dir cleanup after the response is fully sent.
    background_tasks.add_task(shutil.rmtree, str(tmp_dir), True)

    return FileResponse(
        path=str(tmp_path),
        filename=filename,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ProbeRequest(BaseModel):
    host: str = "localhost"
    port: int = 9000


@app.post("/api/probe", response_model=ConnectionTestResult, tags=["meta"],
          dependencies=[Depends(verify_api_key)])
async def probe_connection(req: ProbeRequest):
    """Test a Tally connection using raw host/port — no saved company needed."""
    client = TallyClient(req.host, req.port)
    success, message, open_companies = await client.test_connection()
    return ConnectionTestResult(success=success, message=message, open_companies=open_companies)


# ─── Serve static frontend ───────────────────────────────────────────────────
# Works both in development (python main.py) and as a PyInstaller .exe bundle.
# When frozen, __file__ lives inside the temp extraction dir (_MEIPASS), but
# sys.executable points at the actual .exe — two levels up from there is the
# distribution root that contains pages/ and assets/.
import sys as _sys
if getattr(_sys, "frozen", False):
    _FRONTEND_DIR = Path(_sys.executable).resolve().parent.parent  # .exe → server-bin → dist root
else:
    _FRONTEND_DIR = Path(__file__).resolve().parent.parent  # server/main.py → server → project root

if (_FRONTEND_DIR / "pages").is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    try:
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )
    except OSError as exc:
        if "address already in use" in str(exc).lower() or exc.errno in (98, 10048):
            print(
                f"\n  ERROR: Port {settings.port} is already in use by another application.\n"
                f"  Close the other program, or change the port by creating a file called\n"
                f"  'server/.env' (or next to the .exe) and adding:  PORT=8002\n"
                f"  Then restart TallySync Manager.\n",
                flush=True,
            )
        else:
            raise
