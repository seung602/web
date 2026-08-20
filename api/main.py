from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import get_catalog_db, table_cols, sync_source_databases
from .services import (
    get_trend_dashboard,
    get_daily_trends,
    get_weekly_trends,
    get_monthly_trends,
    get_theme_rollup,
    ranking_rows,
    load_products,
    get_ranking_change,
    get_search_suggestions,
)

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / "static"

app = FastAPI(
    title="K-Beauty Trend Intelligence",
    version="6.0.0",
)


@app.on_event("startup")
def startup_sync_databases():
    sync_source_databases()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ============================================================
# Root / Health
# ============================================================
@app.get("/")
def root():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "6.0.0",
    }


# ============================================================
# Trend APIs
# ============================================================

@app.get("/api/dashboard")
def dashboard():
    """
    구버전 호환용 대시보드 API
    """
    return get_trend_dashboard()


@app.get("/api/trends")
def trends(limit: int = Query(50, ge=1, le=500)):
    """
    구버전 호환용 트렌드 API
    """
    d = get_trend_dashboard()
    return {
        "latest_catalog": d.get("latest_catalog"),
        "items": d.get("trends", [])[:limit],
    }


@app.get("/api/trends/daily")
def trends_daily(limit: int = Query(50, ge=1, le=500)):
    """
    일간 트렌드 API
    프론트 app.js에서 호출하는 핵심 엔드포인트
    """
    return get_daily_trends(limit=limit)


@app.get("/api/trends/weekly")
def trends_weekly(limit: int = Query(25, ge=1, le=200)):
    """
    주간 트렌드 API
    """
    return get_weekly_trends(limit=limit)


@app.get("/api/trends/monthly")
def trends_monthly(limit: int = Query(30, ge=1, le=200)):
    """
    월간 트렌드 API
    """
    return get_monthly_trends(limit=limit)


@app.get("/api/trends/themes")
def trends_themes(days: int = Query(7, ge=1, le=90)):
    """
    테마별 트렌드 롤업 API
    """
    return get_theme_rollup(days=days)


@app.get("/api/google")
def google(limit: int = Query(50, ge=1, le=500)):
    """
    구버전 호환용 Google 신호 API
    현재 프론트에서는 숨김 처리 가능
    """
    d = get_trend_dashboard()
    return {
        "items": d.get("google", [])[:limit],
    }


# ============================================================
# Ranking APIs
# ============================================================

@app.get("/api/rankings")
def rankings(
    kind: str = Query("overall"),
    limit: int = Query(50, ge=1, le=500),
):
    """
    상품 랭킹 API

    kind:
    - overall
    - olive
    - daiso
    """
    items, date = ranking_rows(kind, limit)
    return {
        "kind": kind,
        "latest_date": date,
        "items": items,
    }


@app.get("/api/rankings/change")
def rankings_change(limit: int = Query(50, ge=1, le=200)):
    """
    어제 대비 랭킹 변동 API
    신규 / 상승 / 하락
    """
    return get_ranking_change(limit=limit)


# ============================================================
# Product APIs
# ============================================================

@app.get("/api/products")
def products(
    q: str | None = None,
    category: str | None = None,
    source: str | None = None,
    keyword: str | None = None,
    limit: int = Query(200, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """
    전체 상품 목록 API

    프론트 요구사항:
    - 첫 로드 80개
    - 더보기마다 50개
    - 전체 상품까지 계속 로드 가능
    """
    items, date = load_products(
        limit=limit,
        q=q,
        category=category,
        source=source,
        keyword=keyword,
        offset=offset,
    )

    return {
        "latest_date": date,
        "count": len(items),
        "has_more": len(items) == limit,
        "items": items,
    }


@app.get("/api/products/{product_id}")
def product_detail(product_id: str):
    """
    상품 상세 API
    현재 프론트에서 상품명을 쇼핑몰 링크로 보내더라도
    모달 상세용 호환성 때문에 유지
    """
    items, _ = load_products(
        limit=None,
        q=None,
        category=None,
        source=None,
        keyword=None,
        offset=0,
    )

    p = next((x for x in items if str(x.get("product_id")) == str(product_id)), None)

    if not p:
        return {
            "found": False,
            "product": None,
            "snapshots": [],
            "rankings": [],
        }

    c = get_catalog_db()

    tables = [
        r["name"]
        for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]

    snaps = []
    ranks = []

    if "product_snapshots" in tables:
        snap_cols = table_cols(c, "product_snapshots")

        wanted = []
        for col in ["captured_at", "price", "sale_price", "source", "status"]:
            if col in snap_cols:
                wanted.append(col)

        if wanted:
            rows = c.execute(
                f"""
                SELECT {", ".join(wanted)}
                FROM product_snapshots
                WHERE product_id=?
                ORDER BY ROWID DESC
                LIMIT 30
                """,
                (product_id,),
            ).fetchall()
            snaps = [dict(r) for r in rows]

    if "daily_rankings" in tables:
        cols = table_cols(c, "daily_rankings")

        dcol = next(
            (
                x
                for x in ("run_date", "ranking_date", "date", "captured_at")
                if x in cols
            ),
            None,
        )

        rcol = "rank_num" if "rank_num" in cols else "rank" if "rank" in cols else None

        if dcol and rcol:
            rows = c.execute(
                f"""
                SELECT
                    {dcol} AS ranking_date,
                    source,
                    category,
                    {rcol} AS rank_num
                FROM daily_rankings
                WHERE product_id=?
                ORDER BY {dcol} DESC
                LIMIT 60
                """,
                (product_id,),
            ).fetchall()
            ranks = [dict(r) for r in rows]

    c.close()

    return {
        "found": True,
        "product": p,
        "snapshots": snaps,
        "rankings": ranks,
    }


@app.get("/api/categories")
def categories():
    """
    상품 카테고리 API
    """
    c = get_catalog_db()

    rows = c.execute(
        """
        SELECT
            COALESCE(parent_category, category, 'Other') AS category,
            COUNT(*) AS count
        FROM products
        WHERE status='ACTIVE'
        GROUP BY 1
        ORDER BY count DESC
        """
    ).fetchall()

    c.close()

    return {
        "items": [dict(r) for r in rows],
    }


# ============================================================
# Search Suggestions
# ============================================================

@app.get("/api/suggestions")
def suggestions(limit: int = Query(40, ge=1, le=100)):
    """
    검색 자동완성 API
    """
    return {
        "items": get_search_suggestions(limit),
    }
