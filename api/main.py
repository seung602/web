from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.ai import router as ai_router          # 🚨 먼저 등록 (app의 /api/app/ai 덮어씀)
from api.app import router as app_router
from api.catalog import router as catalog_router
from api.periods import router as periods_router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="K-Beauty Trend Intelligence",
    description="Unified K-Beauty trend + catalog API",
    version="3.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)        # 🚨 순서 중요!
app.include_router(app_router)
app.include_router(catalog_router)
app.include_router(periods_router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"status": "ok", "service": "K-Beauty Trend Intelligence"}


@app.get("/health")
def health():
    return {"status": "healthy"}
