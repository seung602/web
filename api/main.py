from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.app import router as app_router
from api.catalog import router as catalog_router
from api.periods import router as periods_router  # 🚨 추가

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="K-Beauty Trend Intelligence",
    description="Unified K-Beauty trend + catalog API",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(app_router)
app.include_router(catalog_router)
app.include_router(periods_router)  # 🚨 추가

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
