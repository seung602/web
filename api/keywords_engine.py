import json
import logging
import math
import os
import re
import threading
from datetime import datetime

from fastapi import APIRouter, Query

try:
    from api.database import get_catalog_db, get_trend_db
except Exception:
    from database import get_catalog_db, get_trend_db

router = APIRouter(tags=["KeywordsEngine"])
logger = logging.getLogger(__name__)

KEYWORD_DEFS = [
    ("pdrn", ["pdrn", "디엔에이"]), ("retinol", ["레티놀", "retinol"]),
    ("ceramide", ["세라마이드", "ceramide"]), ("cica", ["시카", "centella", "병풀", "센텔라", "마데카"]),
    ("niacinamide", ["나이아신아마이드", "niacinamide"]), ("hyaluron", ["히알루론", "hyaluron", "히아루론"]),
    ("collagen", ["콜라겐", "collagen"]), ("peptide", ["펩타이드", "peptide"]),
    ("glutathione", ["글루타치온", "glutathione"]), ("vitamin", ["비타민", "vitamin", "비타씨"]),
    ("panthenol", ["판테놀", "panthenol"]), ("azulene", ["아줄렌", "azulene"]),
    ("propolis", ["프로폴리스", "propolis"]), ("mugwort", ["쑥", "mugwort", "어성초", "heartleaf"]),
    ("teatree", ["티트리", "tea tree"]), ("snail", ["달팽이", "snail", "뮤신", "mucin"]),
    ("zinc", ["징크", "zinc", "트러블", "acne"]), ("madecasso", ["마데카소사이드", "madecassoside"]),
    ("biotin", ["비오틴", "biotin"]), ("ahabha", ["아하", "바하", "aha", "bha"]),
    ("squalane", ["스쿠알란", "squalane"]), ("lacto", ["락토", "lacto", "프로바이오틱스"]),
    ("green", ["녹두", "녹차"]), ("allantoin", ["알란토인", "allantoin"]),
    ("toner", ["토너", "toner"]), ("serum", ["세럼", "serum", "앰플", "ampoule"]),
    ("cream", ["크림", "cream"]), ("lotion", ["로션", "lotion", "에멀전", "emulsion"]),
    ("essence", ["에센스", "essence"]), ("mask", ["마스크", "mask"]),
    ("pad", ["패드", "pad"]), ("mist", ["미스트", "mist"]),
    ("eyecream", ["아이크림", "eye cream"]), ("cleansing", ["클렌징", "cleans", "클렌저"]),
    ("peeling", ["필링", "peeling", "스크럽", "scrub", "각질"]),
    ("suncream", ["선림", "sun cream", "sunscreen", "자외선"]),
    ("sunstick", ["선스틱", "sunstick", "sun stick"]), ("cushion", ["쿠션", "cushion"]),
    ("base", ["파운데이션", "foundation", "프라이머", "primer", "컨실러", "concealer"]),
    ("lip", ["립", "lip", "틴트", "tint", "글로스", "gloss"]),
    ("powder", ["파우더", "powder", "팩트", "pact", "블러"]),
    ("shampoo", ["샴푸", "shampoo"]), ("treatment", ["트리트먼트", "treatment", "헤어", "hair", "염색", "염모", "탈모"]),
    ("body", ["바디", "body"]), ("hand", ["핸드", "hand"]),
    ("men", ["올인원", "all-in-one", "맨즈", "포맨", "for men"]),
    ("perfume", ["향수", "perfume", "오드", "eau de", "코롱", "cologne"]),
]

SYNONYMS = {
    "ceramide": ["세라마이드", "ceramide"], "sunstick": ["선스틱", "sun stick", "sunstick"],
    "sunscreen": ["선림", "선쿠션", "선스틱", "spf", "자외선"], "spf": ["spf", "자외선", "선림", "선스틱"],
    "centella": ["병풀", "시카", "센텔라", "centella", "cica", "마데카"], "cica": ["시카", "병풀", "centella"],
    "panthenol": ["판테놀", "panthenol"], "barrier": ["장벽", "배리어", "barrier", "세라마이드"],
    "hyaluronic": ["히알루론", "hyaluron", "수분"], "hydration": ["수분", "히알루론", "moistur"],
    "moisturiser": ["보습", "수분", "moistur", "로션", "크림"], "moisturizer": ["보습", "수분", "moistur"],
    "ampoule": ["앰플", "ampoule"], "serum": ["세럼", "serum"], "exosome": ["엑소좀", "exosome"],
    "spicule": ["스피큘", "spicule"], "pdrn": ["pdrn", "디엔에이", "연어"], "retinol": ["레티놀", "retinol"],
    "collagen": ["콜라겐", "collagen"], "peptide": ["펩타이드", "peptide"],
    "vitamin": ["비타민", "비타", "vitamin"], "brightening": ["미백", "브라이트", "톤업", "bright", "광채"],
    "glow": ["광채", "글로우", "glow", "톤업"], "acne": ["트러블", "여드름", "acne", "징크"],
    "niacinamide": ["나이아신아마이드", "niacinamide"], "cleansing": ["클렌징", "클렌저", "cleans"],
    "toner": ["토너", "toner"], "cream": ["크림", "cream"], "mask": ["마스크", "팩", "mask"],
    "mist": ["미스트", "mist"], "pad": ["패드", "pad"], "cushion": ["쿠션", "cushion"],
    "lip": ["립", "틴트", "lip", "tint"], "shampoo": ["샴푸", "shampoo"],
    "perfume": ["향수", "perfume"], "azulene": ["아줄렌", "azulene"], "propolis": ["프로폴리스", "propolis"],
    "mugwort": ["쑥", "mugwort"], "teatree": ["티트리", "tea tree"], "snail": ["달팽이", "snail", "뮤신"],
    "squalane": ["스쿠알란", "squalane"], "allantoin": ["알란토인", "allantoin"],
    "madecassoside": ["마데카소사이드", "madecassoside"], "glutathione": ["글루타치온", "glutathione"],
    "biotin": ["비오틴", "biotin"],
}

_state = {"ready": False}


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _match_def(text, tokens):
    for cond in tokens:
        if isinstance(cond, list):
            if all(c.lower() in text for c in cond): return True
        elif cond.lower() in text: return True
    return False


def _score_of(rev, rat, rank, is_new):
    rev_score = 0.0
    if rev and rev > 0: rev_score += min(60.0, math.log10(rev + 1) * 15)
    if rat and rat > 0:
        try: rev_score += (min(float(rat), 5.0) / 5.0) * 20
        except Exception: pass
    rank_score = max(0.0, 101.0 - rank) if rank else 0.0
    s = max(rev_score, rank_score)
    if is_new: s += 5
    return round(s, 1)


def _gemini_expand(keyword):
    """🚨 유일한 AI 호출 지점: 진짜 신조어일 때만 1회 (3.5 Flash Lite)"""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key: return []
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        for model_name in ("gemini-3.5-flash-lite", "gemini-2.0-flash-lite"):
            try:
                model = genai.GenerativeModel(model_name)
                prompt = (f'뷰티 키워드 "{keyword}" 관련 한국 화장품 상품명 검색 토큰을 '
                          f'한/영 혼합 5~10개 JSON 배열로만 답해. 예: ["스피큘","spicule"]')
                text = model.generate_content(prompt).text.strip()
                m = re.search(r"\[.*\]", text, re.S)
                if m: return [str(x) for x in json.loads(m.group(0))][:10]
            except Exception: continue
    except Exception as e:
        logger.warning(f"gemini expand failed ({keyword}): {e}")
    return []


def _top_trend_keywords(limit=20):
    """trendbot DB에서 상위 트렌드 키워드 추출"""
    try:
        conn = get_trend_db()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for t in tables:
            cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({t})")}
            kw = next((c for c in ("keyword", "kw", "term") if c in cols), None)
            if not kw: continue
            score = next((c for c in ("total_score", "score", "velocity") if c in cols), None)
            order = f"ORDER BY {score} DESC" if score else ""
            rows = conn.execute(f"SELECT {kw} AS k FROM {t} {order} LIMIT {limit}").fetchall()
            conn.close()
            return [r["k"] for r in rows if r["k"]]
    except Exception as e:
        logger.warning(f"trend keyword load failed: {e}")
    return []


def _add_tag(conn, pid, tag):
    row = conn.execute("SELECT keywords FROM product_keywords WHERE product_id=?", (pid,)).fetchone()
    cur = json.loads(row["keywords"]) if row and row["keywords"] else []
    if tag not in cur:
        cur.append(tag)
        conn.execute("INSERT OR REPLACE INTO product_keywords VALUES (?,?,?)",
                     (pid, json.dumps(cur, ensure_ascii=False), _now()))


def _resolve_and_match(conn, k):
    """신조어 해결 + 전상품 스캔 + 결과 저장 (이후 AI 호출 불필요)"""
    row = conn.execute("SELECT product_ids FROM trend_keyword_products WHERE keyword=?", (k,)).fetchone()
    if row: return  # ✅ 이미 캐시됨

    terms = None
    mrow = conn.execute("SELECT terms FROM trend_keyword_map WHERE keyword=?", (k,)).fetchone()
    if mrow:
        terms = json.loads(mrow["terms"])
    else:
        if k in SYNONYMS:
            terms = [k] + SYNONYMS[k]
        else:
            # 사용자가 커밋한 AI 태그 어휘에 이미 있으면 AI 안 씀
            vr = conn.execute("SELECT 1 FROM product_keywords WHERE keywords LIKE ?", (f'%"{k}"%',)).fetchone()
            if vr:
                terms = [k]
            else:
                for kid, toks in KEYWORD_DEFS:
                    if kid == k or k in [t.lower() for t in toks if isinstance(t, str)]:
                        terms = [k] + [t for t in toks if isinstance(t, str)]
                        break
        if terms is None:
            terms = [k] + _gemini_expand(k)  # 🚨 신조어 1회 호출
        conn.execute("INSERT OR REPLACE INTO trend_keyword_map VALUES (?,?,?)",
                     (k, json.dumps(terms, ensure_ascii=False), _now()))

    # 전상품 스캔
    rows = conn.execute("SELECT product_id, product_name, brand, category FROM products WHERE status='ACTIVE'").fetchall()
    ids = []
    for r in rows:
        text = f"{r['product_name']} {r['brand']} {r['category']}".lower()
        if any(t.lower() in text for t in terms if t): ids.append(r["product_id"])

    # 🚨 매칭 결과 + 태그 저장 (영구 캐시)
    conn.execute("INSERT OR REPLACE INTO trend_keyword_products VALUES (?,?,?)",
                 (k, json.dumps(ids), _now()))
    for pid in ids: _add_tag(conn, pid, k)
    conn.commit()
    logger.info(f"✅ 트렌드 키워드 매칭 저장: {k} → {len(ids)}개 상품")


def _build_index():
    try:
        conn = get_catalog_db()
        conn.execute("CREATE TABLE IF NOT EXISTS product_scores (product_id TEXT PRIMARY KEY, score REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS product_keywords (product_id TEXT PRIMARY KEY, keywords TEXT, updated_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS trend_keyword_map (keyword TEXT PRIMARY KEY, terms TEXT, updated_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS trend_keyword_products (keyword TEXT PRIMARY KEY, product_ids TEXT, updated_at TEXT)")
        conn.commit()

        rows = conn.execute("""
            SELECT product_id, product_name, brand, category, parent_category,
                   review_count, rating, is_new FROM products WHERE status='ACTIVE'
        """).fetchall()

        rank_map = {}
        try:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(daily_rankings)")}
            dcol = next((c for c in ("run_date", "ranking_date", "date") if c in cols), None)
            if dcol:
                latest = conn.execute(f"SELECT MAX({dcol}) d FROM daily_rankings WHERE source='oliveyoung'").fetchone()["d"]
                if latest:
                    for r in conn.execute(f"SELECT product_id, rank_num FROM daily_rankings WHERE source='oliveyoung' AND {dcol}=?", (latest,)):
                        rank_map[r["product_id"]] = r["rank_num"]
        except Exception: pass

        # 점수 인덱스
        conn.executemany("INSERT OR REPLACE INTO product_scores VALUES (?,?)",
                         [(r["product_id"], _score_of(r["review_count"], r["rating"], rank_map.get(r["product_id"]), r["is_new"])) for r in rows])

        # 사용자가 커밋한 AI 태그가 없으면 룰 기반 폴백 태깅
        cnt = conn.execute("SELECT COUNT(*) c FROM product_keywords").fetchone()["c"]
        if cnt == 0:
            now = _now()
            conn.executemany("INSERT OR REPLACE INTO product_keywords VALUES (?,?,?)",
                             [(r["product_id"],
                               json.dumps([kid for kid, toks in KEYWORD_DEFS
                                           if _match_def(f"{r['product_name']} {r['brand']} {r['category']} {r['parent_category']}".lower(), toks)],
                                          ensure_ascii=False), now) for r in rows])
        conn.commit()

        # 🚨 trendbot 신조어 사전 매칭 (기동 시 1회, 유저 호출 아님)
        for kw in _top_trend_keywords():
            k = str(kw).strip().lower()
            if k: _resolve_and_match(conn, k)

        conn.close()
        _state["ready"] = True
        logger.info(f"✅ 키워드 엔진 준비 완료: {len(rows)}개 상품")
    except Exception as e:
        logger.error(f"index build error: {e}")


@router.on_event("startup")
def _start():
    threading.Thread(target=_build_index, daemon=True).start()


@router.get("/api/keywords/top")
def top_keywords(limit: int = Query(60)):
    conn = get_catalog_db()
    freq = {}
    try:
        for r in conn.execute("SELECT keywords FROM product_keywords").fetchall():
            for k in json.loads(r["keywords"] or "[]"):
                freq[k] = freq.get(k, 0) + 1
    except Exception: pass
    conn.close()
    top = sorted(freq.items(), key=lambda x: -x[1])[:limit]
    return {"keywords": [{"keyword": k, "count": c} for k, c in top]}


@router.get("/api/keywords/products")
def products_by_keyword(keyword: str = Query(...), limit: int = Query(300)):
    """유저 클릭 시 AI 호출 0회 (저장된 캐시만 조회)"""
    k = keyword.strip().lower()
    conn = get_catalog_db()
    row = conn.execute("SELECT product_ids FROM trend_keyword_products WHERE keyword=?", (k,)).fetchone()
    if not row:
        _resolve_and_match(conn, k)  # 기동 시 놓친 키워드만 여기서 1회 처리
        row = conn.execute("SELECT product_ids FROM trend_keyword_products WHERE keyword=?", (k,)).fetchone()
    ids = json.loads(row["product_ids"]) if row else []

    if not ids:
        conn.close()
        return {"keyword": keyword, "count": 0, "ready": _state["ready"], "products": []}

    scores = {}
    for r in conn.execute("SELECT product_id, score FROM product_scores").fetchall():
        scores[r["product_id"]] = r["score"]
    ph = ",".join("?" * len(ids))
    prods = [dict(r) for r in conn.execute(
        f"SELECT * FROM products WHERE product_id IN ({ph}) AND status='ACTIVE'", ids)]
    conn.close()
    for p in prods: p["score"] = scores.get(p["product_id"], 0)
    prods.sort(key=lambda x: -x["score"])
    return {"keyword": keyword, "count": len(prods), "ready": _state["ready"], "products": prods[:limit]}


@router.get("/api/app/keyword/{keyword}")
def legacy_keyword(keyword: str, limit: int = Query(300)):
    return products_by_keyword(keyword, limit)
