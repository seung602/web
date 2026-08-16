import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TREND_DB_PATH = os.path.join(BASE_DIR, "beauty_trends.db")
CATALOG_DB_PATH = os.path.join(BASE_DIR, "beauty_catalog.db")


def _connect(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Database not found: {path}")

    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_connection():
    """beauty_trends.db 연결 (기존 라우터들이 쓰는 이름 그대로 유지)"""
    return _connect(TREND_DB_PATH)


def get_trend_db():
    """beauty_trends.db 연결 (별칭)"""
    return _connect(TREND_DB_PATH)


def get_catalog_db():
    """beauty_catalog.db 연결 (상품/랭킹 API용)"""
    return _connect(CATALOG_DB_PATH)
