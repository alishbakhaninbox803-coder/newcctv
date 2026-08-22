"""
FILE PATH: backend/app/main.py
ACTION: REPLACE ENTIRE FILE
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.database import Base, engine
from app.config import settings
from app.routers import (
    faces, camera, events, statistics, whatsapp_route,
    auth as auth_router, zones, stream, health, unknown_persons,
)
from app.auth import seed_admin_user

# Enable pgvector extension, then create tables on startup
# (simple approach; use Alembic migrations for production)
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

Base.metadata.create_all(bind=engine)
seed_admin_user()

# Requirement 4/13: keep snapshots separated by category on disk (known /
# unknown / restricted / forensic) instead of one flat folder.
for _subdir in ("known", "unknown", "restricted", "forensic", "misc"):
    os.makedirs(f"{settings.SNAPSHOT_DIR}/{_subdir}", exist_ok=True)

app = FastAPI(title="AI-Based Smart CCTV Surveillance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(faces.router)
app.include_router(camera.router)
app.include_router(zones.router)
app.include_router(stream.router)
app.include_router(health.router)
app.include_router(events.router)
app.include_router(statistics.router)
app.include_router(whatsapp_route.router)
app.include_router(unknown_persons.router)

# Serve snapshot images statically so the dashboard can display them
app.mount("/snapshots", StaticFiles(directory="data/snapshots"), name="snapshots")


@app.get("/")
def root():
    return {"status": "running", "message": "Smart CCTV Surveillance API"}