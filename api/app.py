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
    # --- 성분 ---
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
    "beta-glucan": ["베타글루칸"],
    "heartleaf": ["어성초"],
    "mugwort": ["쑥"],
    "tea tree": ["티트리"],
    "aloe": ["알로에"],
    "ginseng": ["인삼", "홍삼"],
    "green tea": ["녹차"],
    "rice": ["쌀", "미", "라이스"],
    "bamboo": ["대나무"],
    "betaine": ["베타인"],
    "allantoin": ["알란토인"],
    "zinc": ["징크", "아연"],
    # --- 제품 유형 ---
    "ampoule": ["앰플"],
    "moisturiser": ["크림", "로션", "모이스처", "보습"],
    "moisturizer": ["크림", "로션", "모이스처", "보습"],
    "sunscreen": ["선크림", "선스크린", "선케어", "자외선차단"],
    "sunstick": ["선스틱", "선팩", "선케어", "자외선차단"],
    "spf": ["선크림", "선스크린", "자외선차단", "선크림"],
    # --- 효능/컨셉 ---
    "barrier": ["장벽", "피부장벽", "배리어"],
    "glow": ["광채", "글로우", "광"],
    "hydration": ["수분", "보습", "히알루론"],
    "brightening": ["화이트닝", "미백", "광채", "밝은"],
    "dark spot": ["잡티", "미백", "다크스팟"],
    "dark spots": ["잡티", "미백", "다크스팟"],
    "acne": ["트러블", "피지", "여드름"],
    "glass skin": ["광채", "글로우", "유리광", "광"],
    "anti-aging": ["주름", "탄력", "에이징"],
    "toner": ["토너"],
    "serum": ["세럼", "앰플"],
    "essence": ["에센스"],
    "cleanser": ["클렌징", "클렌저"],
    "mask": ["마스크팩", "팩"],
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
        _genai_client = genai.GenerativeModel("gemini-2.5-flash")
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

    # 2층
