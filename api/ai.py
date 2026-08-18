import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

router = APIRouter(tags=["AI"])
logger = logging.getLogger(__name__)

try:
    from api.database import get_trend_db
except Exception:
    try:
        from database import get_trend_db
    except Exception:
        get_trend_db = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

GEMINI_MODELS = [
    "gemini-3.6-flash", "gemini-3.6-flash-preview",
    "gemini-3.0-flash", "gemini-2.5-flash", "gemini-2.0-flash",
]

# period: (window days, 최소 필요 일수) → 데이터 부족 판정용
PERIODS = {"daily": (1, 1), "weekly": (7, 3), "monthly": (30, 7)}


def _cols(conn, table):
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _pick_score_col(conn, table, cols):
    """실제로 값이 들어있는 점수 컬럼을 우선 선택 (0.0 점수 버그 방지)"""
    for c in ("total_score", "score", "trend_score", "velocity", "mentions"):
        if c in cols:
            try:
                row = conn.execute(
                    f"SELECT COUNT(*) AS n FROM {table} WHERE {c} IS NOT NULL AND {c} != ''"
                ).fetchone()
                if row["n"] > 0:
                    return c
            except Exception:
                pass
    return None


def _find_trend_meta(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    best = None
    for t in tables:
        cols = _cols(conn, t)
        kw = next((c for c in ("keyword", "kw", "term", "query") if c in cols), None)
        if not kw:
            continue
        score = _pick_score_col(conn, t, cols)
        date = next((c for c in ("date", "run_date", "collected_at", "created_at") if c in cols), None)
        src = next((c for c in ("source", "platform") if c in cols), None)
        best = {"table": t, "kw": kw, "score": score, "date": date, "src": src}
        if score and date:
            break
    return best


def _aggregate(rows, meta, max_date, days, min_days):
    """기간 윈도우 내 키워드 집계. 데이터 부족 시 None 반환."""
    window = {}
    dates = set()
    for r in rows:
        d = str(r[meta["date"]])[:10] if (meta["date"] and r[meta["date"]]) else None
        if meta["date"] and max_date:
            if not d:
                continue
            try:
                if (datetime.strptime(max_date, "%Y-%m-%d") - datetime.strptime(d, "%Y-%m-%d")).days > days:
                    continue
            except Exception:
                continue
        k = str(r[meta["kw"]]).strip()
        if not k:
            continue
        if d:
            dates.add(d)
        a = window.setdefault(k, {"keyword": k, "score": 0.0, "mentions": 0, "platforms": {}})
        a["mentions"] += 1
        if meta["score"]:
            try:
                v = float(r[meta["score"]])
                if v > a["score"]:
                    a["score"] = v
            except Exception:
                pass
        if meta["src"] and r[meta["src"]]:
            p = str(r[meta["src"]]).lower()
            a["platforms"][p] = a["platforms"].get(p, 0) + 1

    if meta["date"] and len(dates) < min_days:
        return None  # 🚨 데이터 부족
    if not window:
        return None
    return sorted(window.values(), key=lambda x: (-x["score"], -x["mentions"]))[:15]


def _evidence(top):
    out = []
    for t in top[:8]:
        plats = ", ".join(sorted(t["platforms"].keys())) or "global"
        out.append(f"#{t['keyword']} — {t['score']:.1f}점 · {t['mentions']}회 언급 · {plats}")
    return out


def _gemini_summary(lang, period, top):
    if not (genai and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))):
        return None
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    except Exception:
        return None
    lang_name = {"ko": "Korean", "en": "English", "ar": "Arabic"}.get(lang, "Korean")
    data_text = "; ".join(
        f"{t['keyword']} (score {t['score']:.0f}, mentions {t['mentions']}, "
        f"platforms: {','.join(t['platforms'].keys())})" for t in top)
    prompt = (
        f"You are a beauty market analyst for Korean cosmetics sellers. "
        f"Analyze ONLY Western social/search trends (TikTok/YouTube/Instagram/Google/Amazon). "
        f"Write a {lang_name} summary (3-5 sentences) of current Western beauty trends. "
        f"Do NOT mention Olive Young or Daiso.\nTrend data ({period}): {data_text}")
    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            logger.info(f"✅ Gemini success: {model_name}")
            return model.generate_content(prompt).text.strip()
        except Exception as e:
            logger.warning(f"gemini {model_name} failed: {e}")
            continue
    return None


def _fallback_summary(lang, period, top):
    kws = ", ".join(t["keyword"] for t in top[:6])
    if lang == "en":
        return f"Key Western trends ({period}): {kws}. These ingredients/formats are gaining traction on TikTok, YouTube and Google."
    if lang == "ar":
        return f"أبرز الاتجاهات الغربية ({period}): {kws}."
    return f"서구권 주요 트렌드 ({period}): {kws}. TikTok·YouTube·Google에서 상승 중인 키워드입니다."


@router.get("/api/app/ai")
def ai_analysis(lang: str = Query("ko")):
    result = {"lang": lang, "source": "western_trends", "popular": "",
              "daily": {}, "weekly": {}, "monthly": {}}
    if not get_trend_db:
        return result
    try:
        conn = get_trend_db()
    except Exception:
        return result
    try:
        meta = _find_trend_meta(conn)
        if not meta:
            return result
        sel = [meta["kw"]]
        if meta["score"]:
            sel.append(meta["score"])
        if meta["date"]:
            sel.append(meta["date"])
        if meta["src"]:
            sel.append(meta["src"])
        rows = conn.execute(f"SELECT {','.join(sel)} FROM {meta['table']}").fetchall()

        dates = [str(r[meta["date"]])[:10] for r in rows if meta["date"] and r[meta["date"]]]
        max_date = max(dates) if dates else None

        for period, (days, min_days) in PERIODS.items():
            top = _aggregate(rows, meta, max_date, days, min_days)
            if not top:
                continue
            summary = _gemini_summary(lang, period, top) or _fallback_summary(lang, period, top)
            result[period] = {"summary": summary, "evidence": _evidence(top), "trends": top}
            if not result["popular"]:
                result["popular"] = ", ".join(t["keyword"] for t in top[:5])
        return result
    except Exception as e:
        logger.error(f"ai analysis error: {e}")
        return result
    finally:
        conn.close()
