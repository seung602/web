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


def _cols(conn, table):
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _find_trend_meta(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    best = None
    for t in tables:
        cols = _cols(conn, t)
        kw = next((c for c in ("keyword", "kw", "term", "query") if c in cols), None)
        if not kw:
            continue
        score = next((c for c in ("total_score", "score", "velocity", "mentions") if c in cols), None)
        date = next((c for c in ("date", "run_date", "collected_at", "created_at") if c in cols), None)
        src = next((c for c in ("source", "platform") if c in cols), None)
        best = {"table": t, "kw": kw, "score": score, "date": date, "src": src}
        if score and date:
            break
    return best


def _aggregate(rows, meta, max_date, days):
    cutoff = (max_date - timedelta(days=days)).strftime("%Y-%m-%d") if meta["date"] else None
    agg = {}
    for r in rows:
        d = str(r[meta["date"]])[:10] if meta["date"] else None
        if cutoff and d and d < cutoff:
            continue
        k = str(r[meta["kw"]]).strip()
        if not k:
            continue
        a = agg.setdefault(k, {"keyword": k, "score": 0.0, "mentions": 0, "platforms": {}})
        a["mentions"] += 1
        if meta["score"] and r[meta["score"]] is not None:
            try:
                a["score"] = max(a["score"], float(r[meta["score"]]))
            except Exception:
                pass
        if meta["src"] and r[meta["src"]]:
            p = str(r[meta["src"]]).lower()
            a["platforms"][p] = a["platforms"].get(p, 0) + 1
    return sorted(agg.values(), key=lambda x: (-x["score"], -x["mentions"]))[:10]


def _gemini_summary(lang, period, top):
    if not (genai and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))):
        return None
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        lang_name = {"ko": "Korean", "en": "English", "ar": "Arabic"}.get(lang, "Korean")
        data_text = "; ".join(
            f"{t['keyword']} (score {t['score']:.0f}, mentions {t['mentions']}, "
            f"platforms: {','.join(t['platforms'].keys())})" for t in top)
        prompt = (
            f"You are a beauty market analyst for Korean cosmetics sellers. "
            f"Analyze ONLY Western social/search trends (TikTok/YouTube/Instagram/Google/Amazon). "
            f"Write a {lang_name} summary (3-5 sentences) of current Western beauty trends. "
            f"Do NOT mention Olive Young or Daiso.\nTrend data ({period}): {data_text}")
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        logger.error(f"gemini error: {e}")
        return None


def _fallback_summary(lang, period, top):
    kws = ", ".join(t["keyword"] for t in top[:6])
    if lang == "en":
        return f"Key Western trends ({period}): {kws}. These ingredients/formats are gaining traction on TikTok, YouTube and Google."
    if lang == "ar":
        return f"أبرز الاتجاهات الغربية ({period}): {kws}."
    return f"서구권 주요 트렌드 ({period}): {kws}. TikTok·YouTube·Google에서 상승 중인 키워드입니다."


def _evidence(top):
    out = []
    for t in top[:8]:
        plats = ", ".join(sorted(t["platforms"].keys())) or "global"
        out.append(f"#{t['keyword']} — score {t['score']:.1f} / mentions {t['mentions']} / {plats}")
    return out


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

        max_date = None
        if meta["date"]:
            dates = [str(r[meta["date"]])[:10] for r in rows if r[meta["date"]]]
            max_date = datetime.strptime(max(dates), "%Y-%m-%d") if dates else None

        periods = {"daily": 1, "weekly": 7, "monthly": 30}
        for period, days in periods.items():
            top = _aggregate(rows, meta, max_date, days)
            if not top:
                continue
            summary = _gemini_summary(lang, period, top) or _fallback_summary(lang, period, top)
            result[period] = {"summary": summary, "evidence": _evidence(top)}
            if period == "daily" or (period == "weekly" and not result["popular"]):
                result["popular"] = ", ".join(t["keyword"] for t in top[:5])
        return result
    except Exception as e:
        logger.error(f"ai analysis error: {e}")
        return result
    finally:
        conn.close()
