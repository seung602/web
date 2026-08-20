import os
import shutil
import sqlite3
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

CATALOG_URL = os.getenv(
    "CATALOG_DB_URL",
    "https://raw.githubusercontent.com/seung602/Info/main/beauty_catalog.db",
)
TREND_URL = os.getenv(
    "TREND_DB_URL",
    "https://raw.githubusercontent.com/seung602/daiy-trend-bot/main/beauty_trends.db",
)
TREND_DB_PATH = Path(os.getenv("TREND_DB_PATH", DATA_DIR / "beauty_trends.db"))
CATALOG_DB_PATH = Path(os.getenv("CATALOG_DB_PATH", DATA_DIR / "beauty_catalog.db"))

# 재다운로드 간격 (1시간) - 매번 받지 않고 주기적으로만 업데이트
REFRESH_INTERVAL_HOURS = int(os.getenv("DB_REFRESH_HOURS", "1"))


def _is_valid_sqlite(path: Path) -> bool:
    """파일이 진짜 유효한 SQLite DB인지 빠르게 확인"""
    if not path.exists() or path.stat().st_size < 4096:
        return False
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3) as conn:
            conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        return True
    except Exception:
        return False


def _needs_refresh(path: Path) -> bool:
    """마지막 다운로드 이후 일정 시간이 지났는지 확인"""
    if not path.exists():
        return True
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    age = datetime.now() - mtime
    return age > timedelta(hours=REFRESH_INTERVAL_HOURS)


def _download_if_needed(url: str, path: Path):
    """스마트 다운로드: 이미 있으면 스킵, 오래됐거나 깨졌으면 업데이트"""
    if os.getenv("DISABLE_DB_SYNC") == "1":
        print(f"[DB sync] DISABLE_DB_SYNC=1, skipping {path.name}")
        return

    # ✅ 케이스 1: 파일이 이미 유효하고 최신이면 스킵
    if _is_valid_sqlite(path) and not _needs_refresh(path):
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"[DB sync] ✓ {path.name} is valid and fresh (updated {mtime}), skipping download")
        return

    # ✅ 케이스 2: 다운로드 필요
    print(f"[DB sync] ⬇ Downloading {path.name} from {url[:60]}...")
    tmp = path.with_suffix(path.suffix + ".tmp")
    
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "kbeauty-intelligence-web/1.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as response, open(tmp, "wb") as f:
            while True:
                buf = response.read(1024 * 1024)
                if not buf:
                    break
                f.write(buf)
        
        # 다운로드된 파일 검증
        if tmp.stat().st_size < 4096:
            raise RuntimeError(f"Downloaded DB is too small: {tmp.stat().st_size} bytes")
        
        # SQLite 무결성 체크
        try:
            with sqlite3.connect(f"file:{tmp}?mode=ro", uri=True, timeout=5) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if not tables:
                    raise RuntimeError("Downloaded DB has no tables")
        except sqlite3.Error as e:
            raise RuntimeError(f"Downloaded DB is corrupt: {e}")
        
        # 원자적 교체
        os.replace(tmp, path)
        print(f"[DB sync] ✓ {path.name} downloaded and validated ({path.stat().st_size / 1024 / 1024:.1f} MB)")
        
    except Exception as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        
        # 기존 파일이 있으면 그것으로 fallback
        if path.exists() and _is_valid_sqlite(path):
            print(f"[DB sync warning] {path.name} download failed: {exc}. Using existing file.")
        else:
            raise RuntimeError(f"Could not download or find database: {url} -> {path}: {exc}") from exc


def sync_source_databases():
    """앱 시작 시 한 번만 호출되는 메인 동기화 함수"""
    print("[DB sync] Starting source database sync...")
    _download_if_needed(CATALOG_URL, CATALOG_DB_PATH)
    _download_if_needed(TREND_URL, TREND_DB_PATH)
    print("[DB sync] ✓ All databases ready")


def get_trend_db():
    if not TREND_DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {TREND_DB_PATH}")
    conn = sqlite3.connect(f"file:{TREND_DB_PATH}?mode=ro", uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def get_catalog_db():
    if not CATALOG_DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {CATALOG_DB_PATH}")
    conn = sqlite3.connect(f"file:{CATALOG_DB_PATH}?mode=ro", uri=True, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def table_cols(conn, table):
    return {r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}
