import os, sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
TREND_DB_PATH = Path(os.getenv("TREND_DB_PATH", DATA_DIR / "beauty_trends.db"))
CATALOG_DB_PATH = Path(os.getenv("CATALOG_DB_PATH", DATA_DIR / "beauty_catalog.db"))

def _connect(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def get_trend_db(): return _connect(TREND_DB_PATH)
def get_catalog_db(): return _connect(CATALOG_DB_PATH)
def table_cols(conn, table):
    return {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
