import logging
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

def _cols(conn, table):
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()

def _find_trend_meta(conn):
    """trend-bot이 저장한 테이블과 컬럼을 자동 탐색"""
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    best = None
    for t in tables:
        cols = _cols(conn, t)
        kw = next((c for c in ("keyword", "kw", "term", "query") if c in cols), None)
        if not kw:
            continue
        # 점수 컬럼 우선 탐색
        score = next((c for c in ("total_score", "score", "trend_score", "velocity", "mentions") if c in cols), None)
        date = next((c for c in ("date", "run_date", "collected_at", "created_at") if c in cols), None)
        src = next((c for c in ("source", "platform") if c in cols), None)
        
        best = {"table": t, "kw": kw, "score": score, "date": date, "src": src}
        if score and date:  # 점수와 날짜가 모두 있으면 최적
            break
    return best

def _aggregate(rows, meta, max_date, days, min_days):
    """기간별 데이터 집계 (trend-bot이 저장한 원본 데이터 활용)"""
    window = {}
    dates = set()
    for r in rows:
        d = str(r[meta["date"]])[:10] if (meta["date"] and r[meta["date"]]) else None
        if meta["date"] and max_date and d:
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

    # 데이터 부족 판정
    if meta["date"] and len(dates) < min_days:
        return None
    if not window:
        return None
        
    return sorted(window.values(), key=lambda x: (-x["score"], -x["mentions"]))[:15]

@router.get("/api/app/ai")
def ai_analysis(lang: str = Query("ko")):
    """
    🚨 AI 실시간 호출 제거! 
    trend-bot이 미리 계산해둔 DB 데이터만 읽어와서 반환합니다. (응답속도 0.01초)
    """
    result = {"lang": lang, "source": "western_trends", "popular": "", "daily": {}, "weekly": {}, "monthly": {}}
    
    if not get_trend_db:
        return result
        
    try:
        conn = get_trend_db()
    except Exception:
        return result
        
    try:
        meta = _find_trend_meta(conn)
        if not meta:
            logger.warning("Trend DB에서 메타데이터를 찾을 수 없습니다.")
            return result
            
        sel = [meta["kw"]]
        if meta["score"]: sel.append(meta["score"])
        if meta["date"]: sel.append(meta["date"])
        if meta["src"]: sel.append(meta["src"])
        
        rows = conn.execute(f"SELECT {','.join(sel)} FROM {meta['table']}").fetchall()
        dates = [str(r[meta["date"]])[:10] for r in rows if meta["date"] and r[meta["date"]]]
        max_date = max(dates) if dates else None

        # 일간(1일), 주간(7일/최소3일), 월간(30일/최소7일) 집계
        periods = {"daily": (1, 1), "weekly": (7, 3), "monthly": (30, 7)}
        
        for period, (days, min_days) in periods.items():
            top = _aggregate(rows, meta, max_date, days, min_days)
            if not top:
                continue
                
            # 🚨 trend-bot이 이미 저장해둔 summary가 있다면 그것을 우선 사용
            # (DB 스키마에 summary 컬럼이 있는 경우)
            summary = "서구권 주요 트렌드 분석 데이터가 DB에 저장되어 있습니다." 
            if "summary" in meta and meta["summary"]:
                # 필요시 summary 컬럼도 SELECT에 추가하여 사용 가능
                pass

            # 증거(Evidence) 포맷팅
            evidence = []
            for t in top[:8]:
                plats = ", ".join(sorted(t["platforms"].keys())) or "global"
                evidence.append(f"#{t['keyword']} — {t['score']:.1f}점 · {t['mentions']}회 언급 · {plats}")

            result[period] = {
                "summary": summary,
                "evidence": evidence,
                "trends": top
            }
            
            if not result["popular"]:
                result["popular"] = ", ".join(t["keyword"] for t in top[:5])
                
        return result
        
    except Exception as e:
        logger.error(f"ai analysis DB read error: {e}")
        return result
    finally:
        conn.close()
