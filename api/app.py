"""앱 전용 통합 API — 트렌드 + 카탈로그 + Gemini 한영 매핑"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Query
from api.database import get_trend_db, get_catalog_db

router = APIRouter(prefix="/api/app", tags=["App"])

# ============================================================
# Gemini 한-영 매핑 자동화
# ============================================================

MAPPING_CACHE_PATH = Path("/tmp/mapping_cache.db")
MAPPING_TTL_DAYS = 7

# ============================================================
# 성분 사전 (서구 성분 키워드 → 한국어 상품명 표현)
# 제품명에 실제로 등장하는 표현 위주, 정확도 100%
# ============================================================
INGREDIENT_MAP = {
    "ceramide": ["세라마이드"],
    "retinol": ["레티놀", "레티날"],
    "retinal": ["레티날"],
    "niacinamide": ["나이아신아마이드", "나이아신"],
    "hyaluronic": ["히알루론", "히아루론"],
    "hyaluronic acid": ["히알루론산", "히알루론"],
    "pdrn": ["피디알엔", "pdrn", "연어"],
    "azelaic": ["아젤라익"],
    "azelaic acid": ["아젤라익"],
    "panthenol": ["판테놀"],
    "centella": ["센텔라", "병풀", "시카"],
    "cica": ["시카", "센텔라", "병풀"],
    "propolis": ["프로폴리스"],
    "peptide": ["펩타이드"],
    "snail": ["달팽이", "스네일"],
    "snail mucin": ["달팽이점액", "달팽이", "스네일"],
    "collagen": ["콜라겐"],
    "vitamin c": ["비타민", "비타"],
    "ectoin": ["엑토인"],
    "spicule": ["스피큘"],
    "madecassoside": ["마데카소사이드"],
    "asiaticoside": ["아시아티코사이드"],
    "glutathione": ["글루타치온"],
    "tranexamic": ["트라넥삼"],
    "adenosine": ["아데노신"],
    "squalane": ["스쿠알란"],
    "bakuchiol": ["바쿠치올"],
    "salicylic": ["살리실", "bha"],
    "glycolic": ["글리콜", "aha"],
    "beta-glucan": ["베글루칸"],
    "heartleaf": ["어성초"],
    "mugwort": ["쑥"],
    "tea tree": ["티트리"],
    "aloe": ["알로에"],
    "ginseng": ["인삼", "홍삼"],
    "green tea": ["녹차"],
    "rice": ["쌀", "미", "라이스"],
    "bamboo": ["대나무"],
    "betaine": ["베인"],
    "allantoin": ["알란토인"],
    "zinc": ["징크", "아연"],
}

# Gemini 클라이언트 (lazy init)
_genai_client = None

def _get_genai():
    global _genai_client
    if _genai_client is not None:
        return _genai_client
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        _genai_client = genai.GenerativeModel("gemini-2.0-flash")
        return _genai_client
    except Exception as e:
        logging.warning(f"GenAI init failed: {e}")
        return None


def _init_cache_db():
    MAPPING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mapping_cache (
            keyword TEXT PRIMARY KEY,
            terms TEXT,
            cached_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def _get_cached(keyword: str):
    if not MAPPING_CACHE_PATH.exists():
        return None
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    try:
        row = conn.execute(
            "SELECT terms, cached_at FROM mapping_cache WHERE keyword = ?",
            (keyword.lower(),)
        ).fetchone()
        if not row:
            return None
        terms_json, cached_at_str = row
        cached_at = datetime.fromisoformat(cached_at_str)
        if datetime.now() - cached_at > timedelta(days=MAPPING_TTL_DAYS):
            return None
        return json.loads(terms_json)
    finally:
        conn.close()


def _set_cached(keyword: str, terms: list):
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO mapping_cache (keyword, terms, cached_at) VALUES (?, ?, ?)",
            (keyword.lower(), json.dumps(terms, ensure_ascii=False),
             datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def _ask_gemini(keyword: str):
    client = _get_genai()
    if client is None:
        return None

    prompt = f"""You are a K-beauty expert. For the Korean cosmetics trend keyword '{keyword}',
list 3-6 Korean expressions that would appear in Korean product names (상품명).

Examples:
- retinol → ["레티놀", "레티날", "비타A", "안티에이징"]
- ceramide → ["세라마이드"]
- glass skin → ["광채", "글로우", "유리광"]
- sunscreen → ["선크림", "선스크린", "선케어", "자외선차단"]
- sunstick → ["선스틱", "선크림", "선팩", "UV차단"]

Return ONLY a JSON array of Korean strings, nothing else. No markdown, no explanation.

Keyword: '{keyword}'
Output:"""

    try:
        resp = client.generate_content(
            prompt, generation_config={"temperature": 0.3}
        )
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        terms = json.loads(text)
        if isinstance(terms, list) and all(isinstance(t, str) for t in terms):
            return terms[:6]
    except Exception as e:
        logging.warning(f"Gemini query failed for '{keyword}': {e}")
    return None


def _expand_keyword(keyword: str):
    """한-영 매핑 확장: 성분사전(즉시) → Gemini캐시 → Gemini실시간"""
    kw = (keyword or "").lower()
    terms = [kw]

    # 1층: 성분 사전 (즉시, 정확도 100%)
    terms += INGREDIENT_MAP.get(kw, [])

    # 2층: Gemini 캐시
    cached = _get_cached(kw)
    if cached:
        terms += cached
    else:
        # 3층: Gemini 실시간 (사전에 없는 키워드만)
        g = _ask_gemini(kw)
        if g:
            _set_cached(kw, g)
            terms += g

    # 중복 제거 (순서 유지)
    return list(dict.fromkeys(terms))


# ============================================================
# 데이터 조회 헬퍼
# ============================================================

def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _cols(conn, table):
    return [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _pick(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


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

    return _rows(
        conn,
        f"""SELECT {sel} FROM trend_scores
            WHERE signal_date = ? ORDER BY {score} DESC LIMIT ?""",
        (latest, limit),
    ), latest


def _google_signals(conn, limit):
    return _rows(
        conn,
        """SELECT signal_date, platform, query, tag, region, text
           FROM raw_signals
           WHERE LOWER(platform) LIKE 'google%'
           ORDER BY id DESC LIMIT ?""",
        (limit,),
    )


def _top_rankings(conn, limit):
    latest = conn.execute("SELECT MAX(ranking_date) AS d FROM daily_rankings").fetchone()["d"]
    if not latest:
        return [], None
    return _rows(
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
    ), latest


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
    """Gemini + 성분사전 매핑으로 트렌드 → 상품 매칭"""
    matches = []
    for t in trends:
        kw = (t.get("keyword") or "").strip()
        if not kw:
            continue
        terms = _expand_keyword(kw)
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
                "matched_terms": terms,
                "products": products[:per],
            })
    return matches


# ============================================================
# 통합 엔드포인트
# ============================================================

@router.get("/home")
def app_home(
    trends_limit: int = Query(10, ge=1, le=30),
    rankings_limit: int = Query(10, ge=1, le=50),
    rising_limit: int = Query(10, ge=1, le=50),
    google_limit: int = Query(10, ge=1, le=50),
):
    _init_cache_db()

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
        except Exception as e:
            logging.warning(f"trend_product_matches failed: {e}")
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
