"""앱 전용 통합 API — 트렌드 + 카탈로그 + Gemini 한영 매핑 + AI 분석"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Query
from api.database import get_trend_db, get_catalog_db

router = APIRouter(prefix="/api/app", tags=["App"])

# ============================================================
# 다이소 URL 재조립
# ============================================================
DAISO_PDP = "https://www.daisomall.co.kr/pd/pdp/SCR_PDP_0001?pdNo={}"
DAISO_SEARCH = "https://www.daisomall.co.kr/ssn/search/SearchGoods?searchTerm={}"

def _fix_daiso(row):
    pid = row.get("product_id") or ""
    if pid.startswith("DS_"):
        row["product_url"] = DAISO_PDP.format(pid[3:])
    row["search_url"] = DAISO_SEARCH.format(quote(row.get("product_name") or ""))
    return row

# ============================================================
# Gemini 한-영 매핑 자동화
# ============================================================
MAPPING_CACHE_PATH = Path("/tmp/mapping_cache.db")
MAPPING_TTL_DAYS = 7

INGREDIENT_MAP = {
    "ceramide": ["세라마이드"], "retinol": ["레티놀", "레티날"], "retinal": ["레티날"],
    "niacinamide": ["나이아신아마이드", "나이아신"], "hyaluronic": ["히알루론", "히아루론"],
    "hyaluronic acid": ["히알루론산", "히알루론"], "pdrn": ["피디알엔", "pdrn", "연어"],
    "azelaic": ["아젤라익"], "azelaic acid": ["아젤라익"], "panthenol": ["판테놀"],
    "centella": ["센텔라", "병풀", "시카"], "cica": ["시카", "센텔라", "병풀"],
    "propolis": ["프로폴리스"], "peptide": ["펩타이드"], "snail": ["달팽이", "스네일"],
    "snail mucin": ["달팽이점액", "달팽이", "스네일"], "collagen": ["콜라겐"],
    "vitamin c": ["비타민", "비타"], "ectoin": ["엑토인"], "spicule": ["스피큘"],
    "madecassoside": ["마데카소사이드"], "asiaticoside": ["아시아티코사이드"],
    "glutathione": ["글루타치온"], "tranexamic": ["트라넥삼"], "adenosine": ["아데노신"],
    "squalane": ["스쿠알란"], "bakuchiol": ["바쿠치올"], "salicylic": ["살리실", "bha"],
    "glycolic": ["글리콜", "aha"], "beta-glucan": ["베글루칸"], "heartleaf": ["어성초"],
    "mugwort": ["쑥"], "tea tree": ["티트리"], "aloe": ["알로에"], "ginseng": ["인삼", "홍삼"],
    "green tea": ["녹차"], "rice": ["쌀", "미", "라이스"], "bamboo": ["대나무"],
    "betaine": ["베타인"], "allantoin": ["알란토인"], "zinc": ["징크", "아연"],
    "ampoule": ["앰플"], "moisturiser": ["크림", "로션", "모이스처", "보습"],
    "moisturizer": ["크림", "로션", "모이스처", "보습"],
    "sunscreen": ["선크림", "선스크린", "선케어", "자외선차단"],
    "sunstick": ["선스틱", "선팩", "선케어", "자외선차단"],
    "spf": ["선크림", "선스크린", "자외선차단", "선크림"],
    "barrier": ["장벽", "피부장벽", "배리어"], "glow": ["광채", "글로우", "광"],
    "hydration": ["수분", "보습", "히알루론"], "brightening": ["화이트닝", "미백", "광채", "밝은"],
    "dark spot": ["잡티", "미백", "다크스팟"], "dark spots": ["잡티", "미백", "다크스팟"],
    "acne": ["트러블", "피지", "여드름"], "glass skin": ["광채", "글로우", "유리광", "광"],
    "anti-aging": ["주름", "탄력", "에이징"], "toner": ["토너"], "serum": ["세럼", "앰플"],
    "essence": ["에센스"], "cleanser": ["클렌징", "클렌저"], "mask": ["마스크팩", "팩"],
}

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
        _genai_client = genai.GenerativeModel("gemini-3.7-flash")
        return _genai_client
    except Exception as e:
        logging.warning(f"GenAI init failed: {e}")
        return None

def _init_cache_db():
    MAPPING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mapping_cache (
            keyword TEXT PRIMARY KEY, terms TEXT, cached_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def _get_cached(keyword: str):
    if not MAPPING_CACHE_PATH.exists():
        return None
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    try:
        row = conn.execute("SELECT terms, cached_at FROM mapping_cache WHERE keyword = ?", (keyword.lower(),)).fetchone()
        if not row:
            return None
        terms_json, cached_at_str = row
        if datetime.now() - datetime.fromisoformat(cached_at_str) > timedelta(days=MAPPING_TTL_DAYS):
            return None
        return json.loads(terms_json)
    finally:
        conn.close()

def _set_cached(keyword: str, terms: list):
    conn = sqlite3.connect(MAPPING_CACHE_PATH)
    try:
        conn.execute("INSERT OR REPLACE INTO mapping_cache (keyword, terms, cached_at) VALUES (?, ?, ?)",
                     (keyword.lower(), json.dumps(terms, ensure_ascii=False), datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def _ask_gemini(keyword: str):
    client = _get_genai()
    if client is None:
        return None
    prompt = f"""You are a K-beauty expert. For the Korean cosmetics trend keyword '{keyword}',
list 3-6 Korean expressions that would appear in Korean product names (상품명).
Return ONLY a JSON array of Korean strings, nothing else. No markdown, no explanation.
Keyword: '{keyword}'
Output:"""
    try:
        resp = client.generate_content(prompt, generation_config={"temperature": 0.3})
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
    kw = (keyword or "").lower()
    terms = [kw]
    terms += INGREDIENT_MAP.get(kw, [])
    cached = _get_cached(kw)
    if cached:
        terms += cached
    else:
        g = _ask_gemini(kw)
        if g:
            _set_cached(kw, g)
            terms += g
    return list(dict.fromkeys(terms))

# ============================================================
# 데이터 조회 헬퍼
# ============================================================
def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def _cols(conn, table):
    try:
        return [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')]
    except Exception:
        return []

def _parse(d):
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except Exception:
        return None

_PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

def _catalog_range(conn, period):
    latest = conn.execute("SELECT MAX(snapshot_date) AS d FROM product_snapshots").fetchone()["d"]
    d = _parse(latest) or datetime.now().date()
    return latest, (d - timedelta(days=_PERIOD_DAYS[period])).isoformat()

def _ranking_range(conn, period):
    latest = conn.execute("SELECT MAX(ranking_date) AS d FROM daily_rankings").fetchone()["d"]
    if not latest:
        return None, None
    d = _parse(latest) or datetime.now().date()
    cutoff = (d - timedelta(days=_PERIOD_DAYS[period])).isoformat()
    prev = conn.execute("SELECT MAX(ranking_date) AS d FROM daily_rankings WHERE ranking_date <= ?", (cutoff,)).fetchone()["d"]
    return latest, prev

def get_trends(conn, period, limit=15):
    try:
        cols = _cols(conn, "trend_scores")
        kw = next((c for c in ["keyword", "query", "term"] if c in cols), None)
        sc = next((c for c in ["score", "total_score", "trend_score"] if c in cols), None)
        if not kw or not sc:
            return []
        latest = conn.execute("SELECT MAX(signal_date) AS d FROM trend_scores").fetchone()["d"]
        if not latest:
            return []
        if period == "daily":
            return _rows(conn, f"SELECT {kw} AS keyword, {sc} AS score FROM trend_scores WHERE signal_date=? ORDER BY {sc} DESC LIMIT ?", (latest, limit))
        d = _parse(latest)
        cutoff = (d - timedelta(days=_PERIOD_DAYS[period])).isoformat()
        return _rows(conn, f"""
            SELECT {kw} AS keyword, MAX({sc}) AS score FROM trend_scores
            WHERE signal_date >= ? GROUP BY {kw} ORDER BY score DESC LIMIT ?
        """, (cutoff, limit))
    except Exception as e:
        logging.warning(f"get_trends failed: {e}")
        return []

def _oy_highlights(conn, period, limit=5):
    try:
        latest, prev = _ranking_range(conn, period)
        if not latest:
            return []
        return _rows(conn, """
            SELECT cur.product_id, p.product_name, p.brand, p.product_url,
                   cur.rank_num AS current_rank, prev.rank_num AS previous_rank,
                   COALESCE(prev.rank_num, 999) - cur.rank_num AS rank_change
            FROM daily_rankings cur
            JOIN products p ON p.product_id = cur.product_id
            LEFT JOIN daily_rankings prev
              ON prev.product_id = cur.product_id AND prev.source = cur.source
             AND prev.ranking_type = cur.ranking_type AND prev.category = cur.category
             AND prev.ranking_date = ?
            WHERE cur.ranking_date = ? AND LOWER(cur.source) = 'oliveyoung'
            ORDER BY rank_change DESC, cur.rank_num ASC LIMIT ?
        """, (prev, latest, limit))
    except Exception as e:
        logging.warning(f"oy_highlights failed: {e}")
        return []

def _daiso_by_reviews(conn, period, limit=30):
    try:
        latest, past = _catalog_range(conn, period)
        if not latest:
            return []
        if "review_count" not in _cols(conn, "product_snapshots"):
            rows = _rows(conn, """
                SELECT p.product_id, p.product_name, p.brand, p.product_url,
                       s2.price AS price, s2.sale_price AS sale_price,
                       0 AS review_growth, NULL AS review_count
                FROM products p
                JOIN product_snapshots s2 ON s2.product_id = p.product_id AND s2.snapshot_date = ?
                WHERE LOWER(p.source) = 'daiso'
                ORDER BY p.last_catalog_seen_at DESC LIMIT ?
            """, (latest, limit))
        else:
            rows = _rows(conn, """
                SELECT p.product_id, p.product_name, p.brand, p.product_url,
                       s2.price AS price, s2.sale_price AS sale_price,
                       s2.review_count AS review_count,
                       (COALESCE(s2.review_count,0) - COALESCE(s1.review_count,0)) AS review_growth
                FROM products p
                JOIN product_snapshots s2 ON s2.product_id = p.product_id AND s2.snapshot_date = ?
                LEFT JOIN product_snapshots s1 ON s1.product_id = p.product_id AND s1.snapshot_date = ?
                WHERE LOWER(p.source) = 'daiso'
                ORDER BY review_growth DESC, review_count DESC LIMIT ?
            """, (latest, past, limit))
        return [_fix_daiso(r) for r in rows]
    except Exception as e:
        logging.warning(f"daiso_by_reviews failed: {e}")
        return []

def _oy_rankings(conn, period, limit=30):
    try:
        latest, _ = _ranking_range(conn, period)
        if not latest:
            return []
        if period == "daily":
            date_cond, params = "r.ranking_date = ?", [latest]
        else:
            d = _parse(latest)
            cutoff = (d - timedelta(days=_PERIOD_DAYS[period])).isoformat()
            date_cond, params = "r.ranking_date >= ?", [cutoff]
        params.append(limit)
        return _rows(conn, f"""
            SELECT r.product_id, p.product_name, p.brand, p.product_url,
                   SUM(31 - r.rank_num) AS score,
                   (SELECT s.price FROM product_snapshots s WHERE s.product_id = r.product_id
                    ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS price,
                   (SELECT s.sale_price FROM product_snapshots s WHERE s.product_id = r.product_id
                    ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS sale_price
            FROM daily_rankings r
            JOIN products p ON p.product_id = r.product_id
            WHERE LOWER(r.source) = 'oliveyoung' AND {date_cond}
            GROUP BY r.product_id ORDER BY score DESC LIMIT ?
        """, params)
    except Exception as e:
        logging.warning(f"oy_rankings failed: {e}")
        return []

def _overall(oy, ds):
    out = []
    for i, p in enumerate(oy):
        out.append({**p, "final_score": 100 - i * 3, "platform_badge": "🌿"})
    for i, p in enumerate(ds):
        out.append({**p, "final_score": 100 - i * 3, "platform_badge": "💸"})
    out.sort(key=lambda x: x["final_score"], reverse=True)
    return out

# ============================================================
# AI 트렌드 분석 (기간별 요약 + 근거)
# ============================================================
AI_CACHE_PATH = Path("/tmp/ai_analysis_cache.db")
AI_TTL_HOURS = 6
_LANG_NAMES = {"ko": "Korean", "en": "English", "ar": "Arabic"}

def _init_ai_cache():
    conn = sqlite3.connect(AI_CACHE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_cache (
            cache_key TEXT PRIMARY KEY, payload TEXT, cached_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def _ai_cache_get(key):
    if not AI_CACHE_PATH.exists():
        return None
    conn = sqlite3.connect(AI_CACHE_PATH)
    try:
        row = conn.execute("SELECT payload, cached_at FROM ai_cache WHERE cache_key=?", (key,)).fetchone()
        if not row:
            return None
        if datetime.now() - datetime.fromisoformat(row[1]) > timedelta(hours=AI_TTL_HOURS):
            return None
        return json.loads(row[0])
    finally:
        conn.close()

def _ai_cache_set(key, payload):
    conn = sqlite3.connect(AI_CACHE_PATH)
    try:
        conn.execute("INSERT OR REPLACE INTO ai_cache (cache_key, payload, cached_at) VALUES (?,?,?)",
                     (key, json.dumps(payload, ensure_ascii=False), datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def _gather_ai_context(tconn, cconn):
    ctx = {}
    for period in ("daily", "weekly", "monthly"):
        trends = get_trends(tconn, period, 8)
        oy = _oy_rankings(cconn, period, 5)
        ds = _daiso_by_reviews(cconn, period, 5)
        hl = _oy_highlights(cconn, period, 3)
        ctx[period] = {
            "top_keywords": [t.get("keyword") for t in trends],
            "oliveyoung_top": [f"{p.get('product_name')}({p.get('brand') or ''})" for p in oy],
            "daiso_top": [f"{p.get('product_name')} / 리뷰증가 +{p.get('review_growth') or 0}" for p in ds],
            "rank_rising": [f"{h.get('product_name')} (+{h.get('rank_change')})" for h in hl],
        }
    return ctx

def _fallback_analysis(ctx, lang):
    """Gemini가 없으면 데이터 기반으로 간단 요약 생성"""
    L = {
        "ko": {"kw": "주요 키워드", "oy": "올리브영 강세", "ds": "다이소 리뷰 상승", "rise": "순위 급등"},
        "en": {"kw": "Top keywords", "oy": "Olive Young strong", "ds": "Daiso review surge", "rise": "Rank risers"},
        "ar": {"kw": "كلمات رئيسية", "oy": "قوي في أوليف يونغ", "ds": "ارتفاع مراجعات دايسو", "rise": "صاعدو التصنيف"},
    }.get(lang, {"kw": "Top keywords", "oy": "Olive Young strong", "ds": "Daiso review surge", "rise": "Rank risers"})
    out = {}
    for period, c in ctx.items():
        kw = ", ".join(filter(None, c["top_keywords"][:5])) or "-"
        oy = ", ".join(filter(None, c["oliveyoung_top"][:3])) or "-"
        ds = ", ".join(filter(None, c["daiso_top"][:3])) or "-"
        rise = ", ".join(filter(None, c["rank_rising"][:3])) or "-"
        out[period] = {
            "summary": f"{L['kw']}: {kw} | {L['oy']}: {oy} | {L['ds']}: {ds}",
            "evidence": [f"{L['kw']}: {kw}", f"{L['oy']}: {oy}", f"{L['ds']}: {ds}", f"{L['rise']}: {rise}"],
        }
    return out

def _ask_gemini_analysis(ctx, lang_name):
    client = _get_genai()
    if client is None:
        return None
    shape = '{"daily":{"summary":"...","evidence":["..."]},"weekly":{"summary":"...","evidence":["..."]},"monthly":{"summary":"...","evidence":["..."]}}'
    prompt = (
        "You are a K-beauty market analyst advising a reseller of Korean cosmetics in the Netherlands.\n"
        "Using ONLY the data provided, write a short actionable analysis for each period (daily, weekly, monthly).\n"
        'For each period provide: "summary" (2-3 sentences: what is trending, what to consider stocking) and '
        '"evidence" (2-4 bullet strings citing concrete data points: keyword/product names, numbers).\n'
        f"Write everything in {lang_name}. Return ONLY valid JSON in this shape:\n{shape}\n\n"
        f"DATA:\n{json.dumps(ctx, ensure_ascii=False)}"
    )
    try:
        resp = client.generate_content(prompt, generation_config={"temperature": 0.3})
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(text)
        if all(k in data for k in ("daily", "weekly", "monthly")):
            return data
    except Exception as e:
        logging.warning(f"AI analysis failed: {e}")
    return None

@router.get("/ai")
def ai_analysis(lang: str = Query("ko")):
    if lang not in _LANG_NAMES:
        lang = "ko"
    _init_ai_cache()
    key = f"{lang}_{datetime.now().strftime('%Y-%m-%d')}"
    cached = _ai_cache_get(key)
    if cached:
        return {"lang": lang, "source": "cache", "analysis": cached}
    tconn, cconn = get_trend_db(), get_catalog_db()
    try:
        ctx = _gather_ai_context(tconn, cconn)
    finally:
        tconn.close()
        cconn.close()
    analysis = _ask_gemini_analysis(ctx, _LANG_NAMES[lang]) or _fallback_analysis(ctx, lang)
    _ai_cache_set(key, analysis)
    return {"lang": lang, "source": "gemini", "analysis": analysis}

# ============================================================
# 엔드포인트
# ============================================================
@router.get("/dashboard")
def get_dashboard(period: str = Query("daily")):
    if period not in _PERIOD_DAYS:
        period = "daily"
    tconn, cconn = get_trend_db(), get_catalog_db()
    try:
        oy = _oy_rankings(cconn, period)
        ds = _daiso_by_reviews(cconn, period)
        for p in oy: p["platform_badge"] = "🌿"
        for p in ds: p["platform_badge"] = "💸"
        return {
            "period": period,
            "trends": get_trends(tconn, period),
            "highlights": {
                "oliveyoung": _oy_highlights(cconn, period, 5),
                "daiso": _daiso_by_reviews(cconn, period, 5),
            },
            "rankings": {"oliveyoung": oy, "daiso": ds, "overall": _overall(oy, ds)},
        }
    finally:
        tconn.close()
        cconn.close()

@router.get("/keyword/{keyword}")
def get_keyword_detail(keyword: str):
    conn = get_catalog_db()
    try:
        terms = _expand_keyword(keyword)
        has_review = "review_count" in _cols(conn, "product_snapshots")
        extra = """, (SELECT s.price FROM product_snapshots s WHERE s.product_id = products.product_id
                      ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS price,
                     (SELECT s.sale_price FROM product_snapshots s WHERE s.product_id = products.product_id
                      ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS sale_price"""
        if has_review:
            extra += """, (SELECT s.review_count FROM product_snapshots s WHERE s.product_id = products.product_id
                           ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS review_count"""
        products, seen = [], set()
        for term in terms:
            for r in _rows(conn, f"""
                SELECT product_id, source, brand, product_name, product_url, category {extra}
                FROM products WHERE LOWER(product_name) LIKE LOWER(?)
            """, (f"%{term}%",)):
                if r["product_id"] not in seen:
                    seen.add(r["product_id"])
                    r["platform_badge"] = "🌿" if (r.get("source") or "").lower() == "oliveyoung" else "💸"
                    if (r.get("product_id") or "").startswith("DS_"):
                        _fix_daiso(r)
                    products.append(r)
        products.sort(key=lambda x: x.get("review_count") or 0, reverse=True)
        return {"keyword": keyword, "count": len(products), "products": products}
    finally:
        conn.close()
