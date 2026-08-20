import os
import sqlite3
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Public source repositories requested by the project.
CATALOG_URL = os.getenv(
    "CATALOG_DB_URL",
    "https://raw.githubusercontent.com/seung602/practice/main/beauty_catalog.db",
)
# If the trend repository uses a different filename/path, override TREND_DB_URL in Render.
TREND_URL = os.getenv(
    "TREND_DB_URL",
    "https://raw.githubusercontent.com/seung602/daiy-trend-bot/main/beauty_trends.db",
)

TREND_DB_PATH = Path(os.getenv("TREND_DB_PATH", DATA_DIR / "beauty_trends.db"))
CATALOG_DB_PATH = Path(os.getenv("CATALOG_DB_PATH", DATA_DIR / "beauty_catalog.db"))


def _download_if_needed(url: str, path: Path):
    """Download a source DB at application startup.

    The download is atomic so a running API never opens a partially-written SQLite file.
    Set DISABLE_DB_SYNC=1 if you want to use manually supplied local DBs.
    """
    if os.getenv("DISABLE_DB_SYNC") == "1":
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "kbeauty-intelligence-web/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as response, open(tmp, "wb") as f:
            shutil_copyfileobj(response, f)
        if tmp.stat().st_size < 1024:
            raise RuntimeError("Downloaded DB is unexpectedly small.")
        os.replace(tmp, path)
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        # If a previous DB exists, keep serving it rather than taking the whole site down.
        if path.exists() and path.stat().st_size > 1024:
            print(f"[DB sync warning] {url}: {exc}. Using existing {path}")
        else:
            raise RuntimeError(f"Could not download database: {url} -> {path}: {exc}") from exc


def sync_source_databases():
    _download_if_needed(CATALOG_URL, CATALOG_DB_PATH)
    _download_if_needed(TREND_URL, TREND_DB_PATH)


def shutil_copyfileobj(src, dst, length=1024 * 1024):
    while True:
        buf = src.read(length)
        if not buf:
            break
        dst.write(buf)


def _connect(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def get_trend_db():
    return _connect(TREND_DB_PATH)


def get_catalog_db():
    return _connect(CATALOG_DB_PATH)


def table_cols(conn, table):
    return {
        r["name"]
        for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    }
