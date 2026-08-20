import json
import math
import re
from datetime import datetime, timedelta
from collections import Counter
from .database import get_catalog_db, get_trend_db, table_cols

# ============================================================
# Catalog helpers
# ============================================================
def _latest_catalog_date(conn):
    cols = table_cols(conn, 'daily_rankings')
    d = next((x for x in ('run_date', 'ranking_date', 'date', 'captured_at') if x in cols), None)
    if not d:
        return None, d
    r = conn.execute(f'SELECT MAX("{d}") d FROM daily_rankings').fetchone()
    return (r['d'] if r and r['d'] else None), d

def _product_text(p):
    vals = []
    for k in ('product_name', 'brand', 'category', 'parent_category', 'ingredients',
              'product_type', 'keywords', 'skin_type', 'concerns', 'texture',
              'key_ingredients', 'claims'):
        v = p.get(k)
        if v:
            vals.append(str(v))
    return ' '.join(vals).lower()

def _list_field(v):
    if not v:
        return []
    if isinstance(v, list):
        return v
    s = str(v).strip()
    try:
        x = json.loads(s)
        if isinstance(x, list):
            return [str(a).strip() for a in x if str(a).strip()]
    except Exception:
        pass
    return [x.strip() for x in re.split(r'[,|;\n]+', s) if x.strip()]

def _trend_scores(conn):
    cols = table_cols(conn, 'trend_scores')
    if not {'keyword', 'trend_score'}.issubset(cols):
        return {}
    date = 'signal_date' if 'signal_date' in cols else None
    if date:
        mx = conn.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
        rows = conn.execute('''SELECT keyword, trend_score FROM trend_scores 
                              WHERE signal_date=? ORDER BY trend_score DESC''', (mx,)).fetchall() if mx else []
    else:
        rows = conn.execute('SELECT keyword, trend_score FROM trend_scores ORDER BY trend_score DESC').fetchall()
    return {str(r['keyword']).strip().lower(): float(r['trend_score'] or 0) for r in rows}

def product_score(p, trend_map, olive_rank=None, daiso_score=None):
    olive = (100.0 / (1.0 + 0.045 * (olive_rank - 1))) if olive_rank else 0.0
    daiso = float(daiso_score or 0)
    txt = _product_text(p)
    matched = [s for k, s in trend_map.items() if k and k in txt]
    trend = max(matched) if matched else 0.0
    reviews = float(p.get('review_count') or 0)
    rating = float(p.get('rating') or 0)
    review_score = min(100.0, math.log10(reviews + 1) * 22) if reviews else 0
    rating_score = min(100.0, rating / 5 * 100) if rating else 0
    new_bonus = 8 if p.get('is_new') else 0
    parts = []
    weights = []
    if olive_rank:
        parts.append(olive)
        weights.append(0.32)
    if daiso_score:
        parts.append(daiso)
        weights.append(0.25)
    if trend:
        parts.append(trend)
        weights.append(0.23)
    if review_score:
        parts.append(review_score)
        weights.append(0.12)
    if rating_score:
        parts.append(rating_score)
        weights.append(0.08)
    if not parts:
        return round(float(new_bonus), 1)
    base = sum(v * w for v, w in zip(parts, weights)) / sum(weights)
    return round(min(100.0, base + new_bonus), 1)

def load_rank_maps(conn, latest):
    dcol = _latest_catalog_date(conn)[1]
    if not dcol or not latest:
        return {}, {}
    rcol = 'rank_num' if 'rank_num' in table_cols(conn, 'daily_rankings') else 'rank'
    rows = conn.execute(f'SELECT product_id, {rcol} rank_num, source FROM daily_rankings WHERE "{dcol}"=?', (latest,)).fetchall()
    olive = {}
    daiso = {}
    for r in rows:
        if r['source'] == 'oliveyoung':
            olive[r['product_id']] = r['rank_num']
        elif r['source'] == 'daiso':
            daiso[r['product_id']] = r['rank_num']
    return olive, daiso

# ============================================================
# Trend APIs
# ============================================================
def get_daily_trends(limit: int = 50) -> dict:
    """일간 트렌드 (V3 스코어 포함) — today_mentions 컬럼 없음"""
    t = get_trend_db()
    try:
        mx = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()
        if not mx or not mx['d']:
            t.close()
            return {"date": None, "trends": [], "raw_signal_count": 0, "google": []}
        
        max_date = mx['d']
        
        # ✅ 수정: today_mentions 제거, 실제 존재하는 컬럼만 SELECT
        rows = t.execute('''
            SELECT keyword, trend_score, volume_score, velocity_score,
                   persistence_score, cross_platform_score, regional_score,
                   platform_normalized_score
            FROM trend_scores 
            WHERE signal_date=? 
            ORDER BY trend_score DESC 
            LIMIT ?
        ''', (max_date, limit)).fetchall()
        
        trends = []
        for r in rows:
            item = dict(r)
            # 기본값 채우기
            item.setdefault('velocity_score', 0)
            item.setdefault('cross_platform_score', 0)
            item.setdefault('persistence_score', 0)
            item.setdefault('platform_normalized_score', 0)
            item['theme'] = "other"
            item['theme_info'] = {"label": "기타", "color": "#6b7280", "icon": "📦"}
            trends.append(item)
        
        raw_count = 0
        tables = [r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'raw_signals' in tables:
            raw_count = t.execute('SELECT COUNT(*) c FROM raw_signals').fetchone()['c']
        
        google = []
        if 'google_signals' in tables:
            gmx = t.execute('SELECT MAX(signal_date) d FROM google_signals').fetchone()
            if gmx and gmx['d']:
                google = [dict(r) for r in t.execute('''
                    SELECT keyword, region, intent, interest_score, 
                           rising_score, source 
                    FROM google_signals 
                    WHERE signal_date=? 
                    ORDER BY rising_score DESC, interest_score DESC 
                    LIMIT 20
                ''', (gmx['d'],)).fetchall()]
        
        t.close()
        return {"date": max_date, "trends": trends, "raw_signal_count": raw_count, "google": google}
    except Exception as e:
        print(f"[Trend API Error] {e}")
        try:
            t.close()
        except:
            pass
        return {"date": None, "trends": [], "raw_signal_count": 0, "google": []}

def get_theme_rollup(days: int = 7) -> dict:
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"themes": []}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    rows = t.execute('''
        SELECT keyword, SUM(trend_score) as total_score, 
               COUNT(DISTINCT signal_date) as active_days, AVG(trend_score) as avg_score
        FROM trend_scores WHERE signal_date >= ? AND signal_date <= ? GROUP BY keyword
    ''', (start_date, end_date)).fetchall()
    
    themes = {}
    for r in rows:
        theme = "other" # Simplified theme mapping for stability
        if theme not in themes:
            themes[theme] = {"keywords": [], "total_score": 0, "count": 0}
        themes[theme]["keywords"].append({"keyword": r['keyword'], "score": r['total_score'], "active_days": r['active_days'], "avg_score": r['avg_score']})
        themes[theme]["total_score"] += r['total_score']
        themes[theme]["count"] += 1
    
    result = []
    for theme, data in themes.items():
        if theme == "other": continue
        info = {"label": "기타", "color": "#6b7280", "icon": "📦"}
        top_keywords = sorted(data["keywords"], key=lambda x: -x["score"])[:5]
        result.append({"theme": theme, "label": info["label"], "icon": info["icon"], "color": info["color"], "total_score": data["total_score"], "keyword_count": data["count"], "top_keywords": top_keywords})
    
    result.sort(key=lambda x: -x["total_score"])
    t.close()
    return {"themes": result, "period_days": days}

def get_trend_delta(period: str = "weekly") -> dict:
    t = get_trend_db()
    days = 7 if period == "weekly" else 30
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"new": [], "rising": [], "falling": []}
    
    current_start = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    previous_end = current_start
    previous_start = (datetime.fromisoformat(previous_end) - timedelta(days=days)).isoformat()
    
    current = t.execute('SELECT keyword, SUM(trend_score) as score FROM trend_scores WHERE signal_date >= ? AND signal_date < ? GROUP BY keyword', (current_start, end_date)).fetchall()
    previous = t.execute('SELECT keyword, SUM(trend_score) as score FROM trend_scores WHERE signal_date >= ? AND signal_date < ? GROUP BY keyword', (previous_start, previous_end)).fetchall()
    
    current_map = {r['keyword']: r['score'] for r in current}
    previous_map = {r['keyword']: r['score'] for r in previous}
    
    new_entries, rising, falling = [], [], []
    for kw in set(current_map) | set(previous_map):
        cur_s = current_map.get(kw, 0)
        prev_s = previous_map.get(kw, 0)
        if prev_s == 0 and cur_s > 0:
            new_entries.append({"keyword": kw, "score": cur_s})
        elif prev_s > 0 and cur_s == 0:
            falling.append({"keyword": kw, "prev_score": prev_s})
        elif prev_s > 0 and cur_s >= prev_s * 1.5:
            rising.append({"keyword": kw, "prev_score": prev_s, "curr_score": cur_s})
        elif prev_s > 0 and cur_s <= prev_s * 0.5:
            falling.append({"keyword": kw, "prev_score": prev_s, "curr_score": cur_s})
    
    new_entries.sort(key=lambda x: -x["score"])
    rising.sort(key=lambda x: -(x["curr_score"] - x["prev_score"]))
    falling.sort(key=lambda x: (x["prev_score"] - x.get("curr_score", 0)) * -1 if x.get("curr_score") else -x["prev_score"])
    
    t.close()
    return {"period": period, "period_days": days, "new": new_entries[:15], "rising": rising[:15], "falling": falling[:15]}

def get_weekly_trends(limit: int = 25) -> dict:
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"date": None, "trends": [], "delta": {}}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=7)).isoformat()
    rows = t.execute('''
        SELECT keyword, SUM(trend_score) as total_score, AVG(trend_score) as avg_score,
               MAX(trend_score) as peak_score, COUNT(DISTINCT signal_date) as active_days
        FROM trend_scores WHERE signal_date >= ? AND signal_date <= ?
        GROUP BY keyword ORDER BY total_score DESC LIMIT ?
    ''', (start_date, end_date, limit)).fetchall()
    
    trends = [{"keyword": r['keyword'], "total_score": r['total_score'], "avg_score": r['avg_score'], "active_days": r['active_days'], "theme": "other", "theme_info": {"label": "기타", "color": "#6b7280", "icon": "📦"}} for r in rows]
    delta = get_trend_delta("weekly")
    t.close()
    return {"date": end_date, "start_date": start_date, "trends": trends, "delta": delta}

def get_monthly_trends(limit: int = 30) -> dict:
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"date": None, "trends": [], "delta": {}}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=30)).isoformat()
    rows = t.execute('''
        SELECT keyword, SUM(trend_score) as total_score, AVG(trend_score) as avg_score,
               MAX(trend_score) as peak_score, COUNT(DISTINCT signal_date) as active_days
        FROM trend_scores WHERE signal_date >= ? AND signal_date <= ?
        GROUP BY keyword ORDER BY total_score DESC LIMIT ?
    ''', (start_date, end_date, limit)).fetchall()
    
    trends = [{"keyword": r['keyword'], "total_score": r['total_score'], "avg_score": r['avg_score'], "active_days": r['active_days'], "theme": "other", "theme_info": {"label": "기타", "color": "#6b7280", "icon": "📦"}} for r in rows]
    delta = get_trend_delta("monthly")
    t.close()
    return {"date": end_date, "start_date": start_date, "trends": trends, "delta": delta}

def get_trend_dashboard():
    data = get_daily_trends(limit=20)
    return {
        "latest_catalog": None,
        "trends": data["trends"],
        "google": data["google"],
        "raw_signal_count": data["raw_signal_count"],
        "top_keywords": [{"keyword": t["keyword"], "score": t["trend_score"]} for t in data["trends"][:20]]
    }

# ============================================================
# Product APIs
# ============================================================
def load_products(limit=None, q=None, category=None, source=None, keyword=None, offset=0):
    c = get_catalog_db()
    cols = table_cols(c, 'products')
    attr_exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'").fetchone() is not None
    
    base = ['p.product_id', 'p.source', 'p.brand', 'p.product_name', 'p.product_url', 'p.category', 'p.parent_category', 'p.price', 'p.sale_price', 'p.review_count', 'p.rating', 'p.daiso_score', 'p.is_new', 'p.status']
    if attr_exists:
        base += ['a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns', 'a.texture', 'a.key_ingredients', 'a.claims']
    else:
        for x in ('product_type', 'keywords', 'skin_type', 'concerns', 'texture', 'key_ingredients', 'claims'):
            if x in cols: base.append(f'p.{x}')
    
    where = ["p.status='ACTIVE'"]
    args = []
    if q or keyword:
        qv = f'%{q or keyword}%'
        search_fields = ['p.product_name', 'p.brand', 'p.category', 'p.parent_category']
        if attr_exists:
            search_fields += ['a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns', 'a.texture', 'a.key_ingredients', 'a.claims']
        else:
            search_fields += [f'p.{x}' for x in ('product_type', 'keywords', 'skin_type', 'concerns', 'texture', 'key_ingredients', 'claims') if x in cols]
        where.append('(' + ' OR '.join(f'LOWER(COALESCE({x},\'\')) LIKE LOWER(?)' for x in search_fields) + ')')
        args += [qv] * len(search_fields)
    
    if category:
        where.append('(p.category=? OR p.parent_category=?)')
        args += [category, category]
    if source:
        where.append('p.source=?')
        args.append(source)
    
    join = " LEFT JOIN product_attributes a ON a.product_id=p.product_id" if attr_exists else ""
    sql = f"SELECT {','.join(base)} FROM products p{join} WHERE " + ' AND '.join(where)
    if limit:
        sql += f' LIMIT {int(limit)} OFFSET {int(offset)}'
    
    rows = [dict(r) for r in c.execute(sql, args).fetchall()]
    latest, _ = _latest_catalog_date(c)
    olive, daiso = load_rank_maps(c, latest)
    t = get_trend_db()
    tm = _trend_scores(t)
    t.close()
    
    for p in rows:
        p['olive_rank'] = olive.get(p['product_id'])
        p['daiso_rank'] = daiso.get(p['product_id'])
        p['overall_score'] = product_score(p, tm, p['olive_rank'], p.get('daiso_score'))
        p['keyword_list'] = _list_field(p.get('keywords'))
        p['ingredient_list'] = _list_field(p.get('key_ingredients'))
    c.close()
    return rows, latest

def ranking_rows(kind='overall', limit=50):
    c = get_catalog_db()
    latest, _ = _latest_catalog_date(c)
    olive, daiso = load_rank_maps(c, latest)
    cols = table_cols(c, 'products')
    attr_exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'").fetchone() is not None
    
    fields = ['p.product_id', 'p.source', 'p.brand', 'p.product_name', 'p.product_url', 'p.category', 'p.parent_category', 'p.price', 'p.sale_price', 'p.review_count', 'p.rating', 'p.daiso_score', 'p.is_new']
    if attr_exists:
        fields += ['a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns', 'a.texture', 'a.key_ingredients', 'a.claims']
    
    join = " LEFT JOIN product_attributes a ON a.product_id=p.product_id" if attr_exists else ""
    rows = [dict(r) for r in c.execute(f"SELECT {','.join(fields)} FROM products p{join} WHERE p.status='ACTIVE'").fetchall()]
    c.close()
    
    t = get_trend_db()
    tm = _trend_scores(t)
    t.close()
    
    for p in rows:
        p['olive_rank'] = olive.get(p['product_id'])
        p['daiso_rank'] = daiso.get(p['product_id'])
        p['overall_score'] = product_score(p, tm, p['olive_rank'], p.get('daiso_score'))
        p['keyword_list'] = _list_field(p.get('keywords'))
        p['ingredient_list'] = _list_field(p.get('key_ingredients'))
    
    if kind == 'olive':
        rows = [p for p in rows if p['olive_rank']]
        rows.sort(key=lambda x: x['olive_rank'])
    elif kind == 'daiso':
        rows = [p for p in rows if p.get('daiso_score')]
        rows.sort(key=lambda x: float(x.get('daiso_score') or 0), reverse=True)
    else:
        rows.sort(key=lambda x: x['overall_score'], reverse=True)
    
    for i, p in enumerate(rows[:limit], 1):
        p['display_rank'] = i
    return rows[:limit], latest

# ============================================================
# Ranking Change & Search Suggestions (NEW)
# ============================================================
def get_ranking_change(limit: int = 50) -> dict:
    """어제 vs 오늘 랭킹 변동 계산"""
    c = get_catalog_db()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'daily_rankings' not in tables:
        c.close()
        return {"new": [], "rising": [], "falling": []}
    
    cols = table_cols(c, 'daily_rankings')
    dcol = next((x for x in ('run_date', 'ranking_date', 'date', 'captured_at') if x in cols), None)
    if not dcol:
        c.close()
        return {"new": [], "rising": [], "falling": []}
    
    rcol = 'rank_num' if 'rank_num' in cols else 'rank'
    dates = c.execute(f"SELECT DISTINCT {dcol} FROM daily_rankings ORDER BY {dcol} DESC LIMIT 2").fetchall()
    if len(dates) < 2:
        c.close()
        return {"new": [], "rising": [], "falling": []}
    
    today_date = dates[0][dcol]
    yesterday_date = dates[1][dcol]
    
    today_rows = c.execute(f"SELECT product_id, {rcol} rank_num, source FROM daily_rankings WHERE {dcol}=?", (today_date,)).fetchall()
    yesterday_rows = c.execute(f"SELECT product_id, {rcol} rank_num, source FROM daily_rankings WHERE {dcol}=?", (yesterday_date,)).fetchall()
    
    today_map = {r['product_id']: {'rank': r['rank_num'], 'source': r['source']} for r in today_rows}
    yesterday_map = {r['product_id']: {'rank': r['rank_num'], 'source': r['source']} for r in yesterday_rows}
    
    prod_rows = c.execute("SELECT product_id, product_name FROM products").fetchall()
    prod_names = {r['product_id']: r['product_name'] for r in prod_rows}
    c.close()
    
    new_entries, rising, falling = [], [], []
    for pid, today_info in today_map.items():
        if pid not in yesterday_map:
            new_entries.append({"product_id": pid, "product_name": prod_names.get(pid, pid), "source": today_info['source'], "rank": today_info['rank']})
        else:
            diff = yesterday_map[pid]['rank'] - today_info['rank']
            if diff > 0:
                rising.append({"product_id": pid, "product_name": prod_names.get(pid, pid), "source": today_info['source'], "diff": diff, "today_rank": today_info['rank'], "yesterday_rank": yesterday_map[pid]['rank']})
            elif diff < 0:
                falling.append({"product_id": pid, "product_name": prod_names.get(pid, pid), "source": today_info['source'], "diff": abs(diff), "today_rank": today_info['rank'], "yesterday_rank": yesterday_map[pid]['rank']})
    
    new_entries.sort(key=lambda x: x['rank'])
    rising.sort(key=lambda x: -x['diff'])
    falling.sort(key=lambda x: -x['diff'])
    
    return {"new": new_entries[:limit], "rising": rising[:limit], "falling": falling[:limit]}

def get_search_suggestions(limit: int = 40) -> list:
    """검색창 자동완성용 키워드 예시 (실제 트렌드 상위 + 구체적 뷰티 용어)."""
    out = []
    try:
        t = get_trend_db()
        mx = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
        if mx:
            # 실제 DB에서 trending 중인 키워드를 우선적으로 가져옴
            rows = t.execute('SELECT keyword FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC LIMIT 20', (mx,)).fetchall()
            out += [r['keyword'] for r in rows]
        t.close()
    except Exception:
        pass
    
    # 실제 사용자가 검색할 법한 구체적이고 인기 있는 뷰티 용어 풀
    real_search_terms = [
        "레티놀 세럼", "레티날 크림", "시카 수분 크림", "히알루론산 토너",
        "나이아신아마이드 세럼", "비타민C 세럼", "센텔라 수분 마스크",
        "엑소좀 스킨부스터", "PDRN 연어 주사", "폴리뉴클레오타이드",
        "세라마이드 장벽 크림", "병풀 추출물", "스피큘 토닝",
        "아젤라산 세럼", "살리실산 각질", "판테놀 수분", "스쿠알란 오일",
        "자외선 차단제", "선스틱", "유기자차", "무기자차",
        "여드름 트러블", "모공 관리", "색소침착", "미백 기능성",
        "안티에이징", "주름 개선", "탄력", "수분 공급", "장벽 강화"
    ]
    out += real_search_terms
    
    # 중복 제거 및 정리
    seen, res = set(), []
    for k in out:
        k = str(k).strip()
        if k and k.lower() not in seen:
            seen.add(k.lower())
            res.append(k)
        if len(res) >= limit:
            break
    return res
