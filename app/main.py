from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.models.database import init_db
from app.api import interview, ingestion, knowledge, playbook, audio, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="営業暗黙知 AI ツール",
    description="営業担当者の暗黙知を収集・形式知化・活用するAIプラットフォーム",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(playbook.router, prefix="/api")
app.include_router(audio.router, prefix="/api")
app.include_router(users.router, prefix="/api")

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "営業暗黙知 AI ツール API", "docs": "/docs"}
