from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from routers import gmail, drive, calendar, todoist, users
from auth.middleware import SessionMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Happy House Manager backend starting up")
    yield
    logger.info("Happy House Manager backend shutting down")


app = FastAPI(
    title="Happy House Manager API",
    description="Home management API for Erick and Jewel Darrington",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (JWT extraction)
app.add_middleware(SessionMiddleware)

# Routers
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(gmail.router, prefix="/gmail", tags=["gmail"])
app.include_router(drive.router, prefix="/drive", tags=["drive"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
app.include_router(todoist.router, prefix="/todoist", tags=["todoist"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "happy-house-manager"}
