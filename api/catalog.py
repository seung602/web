from fastapi import APIRouter, HTTPException
from api.database import get_catalog_db

router = APIRouter(prefix="/api/catalog", tags=["Catalog"])


@router.get("/schema")
def catalog_schema():
    """beauty_catalog.db의 실제 테이블/컬럼 구조를 그대로 반환"""
    conn = get_catalog_db()
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]

        result = {}
        for t in tables:
            cols = [dict(r) for r in conn.execute(f'PRAGMA table_info("{t}")')]
            count = conn.execute(f'SELECT COUNT(*) AS c FROM "{t}"').fetchone()["c"]
            result[t] = {
                "columns": [c["name"] for c in cols],
                "row_count": count,
            }

        return {"tables": result}
    finally:
        conn.close()


@router.get("/preview/{table_name}")
def preview_table(table_name: str, limit: int = 5):
    """테이블 상위 몇 줄을 그대로 반환 (데이터 맛보기)"""
    conn = get_catalog_db()
    try:
        tables = [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        ]
        if table_name not in tables:
            raise HTTPException(404, f"Table not found: {table_name}")

        rows = conn.execute(
            f'SELECT * FROM "{table_name}" LIMIT ?', (limit,)
        ).fetchall()

        return {"table": table_name, "rows": [dict(r) for r in rows]}
    finally:
        conn.close()
