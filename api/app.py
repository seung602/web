"""앱 전용 통합 API — 트렌드 + 카탈로그를 한 번에"""
from fastapi import APIRouter, Query
from api.database import get_trend_db, get_catalog_db

router = APIRouter(prefix="/api/app", tags=["App"])

# 트렌드 키워드 → 한국어 상품명 매칭 사전
KEYWORD_MAP = {
    "retinol": ["레티놀"], "retinal": ["레티날", "레티놀"],
    "pdrn": ["pdrn", "피디알엔"], "ceramide": ["세라마이드"],
    "collagen": ["콜라겐"], "niacinamide": ["나이아신"],
    "hyaluronic": ["히알루론"], "centella": ["센텔라", "시카", "병풀"],
    "cica": ["시카", "센텔라"], "propolis": ["프로폴리스"],
    "peptide": ["펩타이드"], "snail": ["달팽이", "스네일"],
    "azelaic": ["아젤라익"], "spicule": ["스피큘"], "ectoin": ["엑토인"],
    "vitamin c": ["비타민"], "sunscreen": ["선크림", "선스크린", "선케어"],
    "toner": ["토너"], "serum": ["세럼", "앰플"], "essence": ["에센스"],
    "moisturizer": ["크림", "로션", "모이스처"], "cleanser": ["클렌징", "클렌저"],
    "mask": ["마스크팩", "팩"], "brightening": ["화이트닝", "광채"],
    "dark spot": ["잡티", "미백", "다크스팟"], "dark spots": ["잡티", "미백"],
    "hydration": ["수분", "히알루론"], "acne": ["트러블", "피지", "여드름"],
    "glass skin": ["광채", "글로우"], "glow": ["광채", "글로우"],
    "anti-aging": ["주름", "탄력", "에이징"],
}


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _cols(conn, table):
    return [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _pick(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


# ---------- 트렌드 DB ----------

def _top_trends(conn, limit):
    cols = _cols(conn, "trend_scores")
    kw = _pick(cols, ["keyword", "query", "term", "topic", "name"])
    if not kw:
        return [], None
    latest = conn.execute("SELECT MAX(signal_date) AS d FROM trend_scores").fetchone()["d"]
    if not latest:
        return [], None

    score = _pick(cols, ["score", "total_score", "trend_score", "heat"]) or "velocity_score"
    extra = [c for c in ["velocity_score", "persistence_score", "platforms"] if c in cols]
    sel = f"{kw} AS keyword, {score} AS score" + (", " + ", ".join(extra) if extra else "")

    items = _rows(
        conn,
        f"""SELECT {sel} FROM trend_scores
            WHERE signal_date = ? ORDER BY {score} DESC LIMIT ?""",
        (latest, limit),
    )
    return items, latest


def _google_signals(conn, limit):
    return _rows(
        conn,
        """SELECT signal_date, region, seed_keyword, keyword, query_type,
                  intent, interest_score, rising_score, source
           FROM google_signals
           ORDER BY id DESC LIMIT ?""",
        (limit,),
    )


# ---------- 카탈로그 DB ----------

def _top_rankings(conn, limit):
    latest = conn.execute("SELECT MAX(ranking_date) AS d FROM daily_rankings").fetchone()["d"]
    if not latest:
        return [], None
    items = _rows(
        conn,
        """SELECT r.rank_num, r.source, r.category, r.product_id,
                  p.brand, p.product_name, p.product_url,
                  (SELECT s.sale_price FROM product_snapshots s
                    WHERE s.product_id = r.product_id
                    ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS sale_price,
                  (SELECT s.price FROM product_snapshots s
                    WHERE s.product_id = r.product_id
                    ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS price
           FROM daily_rankings r
           LEFT JOIN products p ON p.product_id = r.product_id
           WHERE r.ranking_date = ?
           ORDER BY r.rank_num LIMIT ?""",
        (latest, limit),
    )
    return items, latest


def _rising_products(conn, limit):
    latest = conn.execute("SELECT MAX(ranking_date) AS d FROM daily_rankings").fetchone()["d"]
    if not latest:
        return [], None
    previous = conn.execute(
        "SELECT MAX(ranking_date) AS d FROM daily_rankings WHERE ranking_date < ?",
        (latest,),
    ).fetchone()["d"]

    items = _rows(
        conn,
        """SELECT cur.rank_num AS current_rank, prev.rank_num AS previous_rank,
                  cur.product_id, p.brand, p.product_name, p.product_url
           FROM daily_rankings cur
           LEFT JOIN daily_rankings prev
             ON prev.product_id = cur.product_id
            AND prev.source = cur.source
            AND prev.ranking_type = cur.ranking_type
            AND prev.category = cur.category
            AND prev.ranking_date = ?
           LEFT JOIN products p ON p.product_id = cur.product_id
           WHERE cur.ranking_date = ?""",
        (previous, latest),
    )
    out = []
    for it in items:
        it = dict(it)
        if it["previous_rank"] is not None:
            it["rank_change"] = it["previous_rank"] - it["current_rank"]
            it["direction"] = "up" if it["rank_change"] > 0 else ("down" if it["rank_change"] < 0 else "same")
        else:
            it["rank_change"] = None
            it["direction"] = "new"
        out.append(it)
    out.sort(key=lambda x: x["rank_change"] if x["rank_change"] is not None else -9999, reverse=True)
    return out[:limit], latest


def _trend_product_matches(trends, conn, per=3):
    """ 킬러 기능: 트렌드 키워드 → 실제 인기 상품 매칭"""
    matches = []
    for t in trends:
        kw = (t.get("keyword") or "").strip()
        if not kw:
            continue
        terms = [kw] + KEYWORD_MAP.get(kw.lower(), [])
        products, seen = [], set()
        for term in terms:
            for p in _rows(
                conn,
                """SELECT product_id, brand, product_name, product_url, category
                   FROM products
                   WHERE LOWER(product_name) LIKE LOWER(?) LIMIT ?""",
                (f"%{term}%", per),
            ):
                if p["product_id"] not in seen:
                    seen.add(p["product_id"])
                    products.append(p)
            if len(products) >= per:
                break
        if products:
            matches.append({
                "keyword": kw,
                "score": t.get("score"),
                "products": products[:per],
            })
    return matches


# ---------- 통합 엔드포인트 ----------

@router.get("/home")
def app_home(
    trends_limit: int = Query(10, ge=1, le=30),
    rankings_limit: int = Query(10, ge=1, le=50),
    rising_limit: int = Query(10, ge=1, le=50),
    google_limit: int = Query(10, ge=1, le=50),
):
    """앱 메인 화면용 — 모든 데이터를 한 번에"""
    trend_conn = get_trend_db()
    try:
        try:
            top_trends, trend_date = _top_trends(trend_conn, trends_limit)
        except Exception:
            top_trends, trend_date = [], None
        try:
            google_signals = _google_signals(trend_conn, google_limit)
        except Exception:
            google_signals = []
    finally:
        trend_conn.close()

    cat_conn = get_catalog_db()
    try:
        try:
            top_rankings, rank_date = _top_rankings(cat_conn, rankings_limit)
        except Exception:
            top_rankings, rank_date = [], None
        try:
            rising, _ = _rising_products(cat_conn, rising_limit)
        except Exception:
            rising = []
        try:
            matches = _trend_product_matches(top_trends, cat_conn)
        except Exception:
            matches = []
    finally:
        cat_conn.close()

    return {
        "updated_at": {"trends": trend_date, "catalog": rank_date},
        "top_trends": top_trends,
        "trend_product_matches": matches,
        "top_rankings": top_rankings,
        "rising_products": rising,
        "google_signals": google_signals,
    }
