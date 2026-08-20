import json
import math
import re
from datetime import datetime, timedelta
from collections import Counter
from .database import get_catalog_db, get_trend_db, table_cols

# ============================================================
# V3 Lifecycle & Theme Rules
# ============================================================
LIFECYCLE_LABELS = {
    "DORMANT": {"label": "Dormant", "color": "#6b7280", "icon": "⚫"},
    "NOISE_CANDIDATE": {"label": "Possible Noise", "color": "#9ca3af", "icon": "⚪"},
    "SEED": {"label": "Early Signal", "color": "#f59e0b", "icon": "🌱"},
    "WATCH": {"label": "Watch", "color": "#eab308", "icon": "👀"},
    "EMERGING": {"label": "Rising", "color": "#10b981", "icon": "📈"},
    "SCALING": {"label": "Spreading", "color": "#3b82f6", "icon": "🚀"},
    "ESTABLISHED": {"label": "Steady", "color": "#8b5cf6", "icon": "✅"},
    "COOLING": {"label": "Cooling", "color": "#ef4444", "icon": "📉"},
}

THEME_RULES = [
    ("barrier_soothing", ["ceramide", "centella", "cica", "panthenol", "ectoin", "barrier", "sensitive skin", "redness", "rosacea", "soothing"]),
    ("sun_protection", ["sunscreen", "sun stick", "sunstick", "spf", "sun care"]),
    ("acne_pore", ["salicylic", "azelaic", "acne", "pore", "blemish", "bha", "aha"]),
    ("brightening_pigment", ["vitamin c", "niacinamide", "tranexamic", "kojic", "dark spot", "hyperpigmentation", "brightening", "glow"]),
    ("antiaging_regeneration", ["retinol", "retinal", "bakuchiol", "peptide", "collagen", "exosome", "pdrn", "polynucleotide", "antiaging", "anti-aging", "firming", "reedle", "spicule", "volufiline"]),
    ("hydration", ["hyaluronic", "hydrat", "dry skin", "dehydrated", "snail", "propolis", "squalane", "urea"]),
]

def lifecycle_label(status: str) -> dict:
    """V3 라이프사이클 라벨 반환"""
    status_upper = (status or "").strip().upper()
    if status_upper in LIFECYCLE_LABELS:
        return LIFECYCLE_LABELS[status_upper]
    return {"label": "Unknown", "color": "#6b7280", "icon": "❓"}

def keyword_theme(keyword: str) -> str:
    """키워드를 테마로 분류"""
    kw = (keyword or "").lower()
    for theme, terms in THEME_RULES:
        if any(t in kw for t in terms):
            return theme
    return "other"

THEME_LABELS = {
    "barrier_soothing": {"label": "장벽·진정", "color": "#10b981", "icon": "🛡️"},
    "sun_protection": {"label": "자외선 차단", "color": "#f59e0b", "icon": "☀️"},
    "acne_pore": {"label": "여드름·모공", "color": "#ef4444", "icon": "🔴"},
    "brightening_pigment": {"label": "미백·색소", "color": "#fbbf24", "icon": "✨"},
    "antiaging_regeneration": {"label": "안티에이징·재생", "color": "#8b5cf6", "icon": "💎"},
    "hydration": {"label": "수분·보습", "color": "#3b82f6", "icon": "💧"},
    "other": {"label": "기타", "color": "#6b7280", "icon": "📦"},
}

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
# Trend API (V3 업그레이드)
# ============================================================
def get_daily_trends(limit: int = 50) -> dict:
    """일간 트렌드 (V3 스코어 포함)"""
    t = get_trend_db()
    cols = table_cols(t, 'trend_scores')
    
    # 최신 날짜
    mx = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not mx:
        t.close()
        return {"date": None, "trends": [], "raw_signal_count": 0}
    
    # V3 컬럼 확인
    v3_cols = []
    for col in ['ema_velocity', 'z_score', 'novelty_score', 'engagement_score', 'lifecycle']:
        if col in cols:
            v3_cols.append(col)
    
    select_cols = ['keyword', 'trend_score', 'volume_score', 'velocity_score',
                   'persistence_score', 'cross_platform_score', 'regional_score',
                   'platform_normalized_score', 'today_mentions']
    
    # today_mentions 컬럼 확인
    if 'today_mentions' not in cols:
        select_cols = [c for c in select_cols if c != 'today_mentions']
    
    all_cols = select_cols + v3_cols
    query = f'''SELECT {", ".join(all_cols)} FROM trend_scores 
                WHERE signal_date=? ORDER BY trend_score DESC LIMIT ?'''
    
    rows = t.execute(query, (mx, limit)).fetchall()
    trends = []
    for r in rows:
        item = dict(r)
        # 라이프사이클 정보 추가
        status = item.get('lifecycle', 'WATCH')
        item['lifecycle_info'] = lifecycle_label(status)
        # 테마 분류
        item['theme'] = keyword_theme(item['keyword'])
        item['theme_info'] = THEME_LABELS.get(item['theme'], THEME_LABELS['other'])
        trends.append(item)
    
    # Raw signal count
    raw_count = 0
    if 'raw_signals' in [r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        raw_count = t.execute('SELECT COUNT(*) c FROM raw_signals').fetchone()['c']
    
    # Google signals
    google = []
    if 'google_signals' in [r[0] for r in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        gmx = t.execute('SELECT MAX(signal_date) d FROM google_signals').fetchone()['d']
        if gmx:
            google = [dict(r) for r in t.execute('''SELECT keyword, region, intent, interest_score, 
                           rising_score, source FROM google_signals 
                           WHERE signal_date=? ORDER BY rising_score DESC, interest_score DESC LIMIT 20''', (gmx,)).fetchall()]
    
    t.close()
    return {
        "date": mx,
        "trends": trends,
        "raw_signal_count": raw_count,
        "google": google,
        "total_keywords": len(trends)
    }

def get_theme_rollup(days: int = 7) -> dict:
    """테마별 집계"""
    t = get_trend_db()
    
    # 날짜 범위 계산
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"themes": []}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    
    rows = t.execute('''
        SELECT keyword, SUM(trend_score) as total_score, 
               COUNT(DISTINCT signal_date) as active_days,
               AVG(trend_score) as avg_score
        FROM trend_scores 
        WHERE signal_date >= ? AND signal_date <= ?
        GROUP BY keyword
    ''', (start_date, end_date)).fetchall()
    
    # 테마별 집계
    themes = {}
    for r in rows:
        theme = keyword_theme(r['keyword'])
        if theme not in themes:
            themes[theme] = {"keywords": [], "total_score": 0, "count": 0}
        themes[theme]["keywords"].append({
            "keyword": r['keyword'],
            "score": r['total_score'],
            "active_days": r['active_days'],
            "avg_score": r['avg_score']
        })
        themes[theme]["total_score"] += r['total_score']
        themes[theme]["count"] += 1
    
    # 정렬 및 포맷팅
    result = []
    for theme, data in themes.items():
        if theme == "other":
            continue
        info = THEME_LABELS.get(theme, THEME_LABELS['other'])
        top_keywords = sorted(data["keywords"], key=lambda x: -x["score"])[:5]
        result.append({
            "theme": theme,
            "label": info["label"],
            "icon": info["icon"],
            "color": info["color"],
            "total_score": data["total_score"],
            "keyword_count": data["count"],
            "top_keywords": top_keywords
        })
    
    result.sort(key=lambda x: -x["total_score"])
    t.close()
    return {"themes": result, "period_days": days}

def get_trend_delta(period: str = "weekly") -> dict:
    """주간/월간 델타 (신규/상승/냉각)"""
    t = get_trend_db()
    
    if period == "weekly":
        days = 7
    else:
        days = 30
    
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"new": [], "rising": [], "cooling": []}
    
    current_start = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    previous_end = current_start
    previous_start = (datetime.fromisoformat(previous_end) - timedelta(days=days)).isoformat()
    
    # 현재 기간 점수
    current = t.execute('''
        SELECT keyword, SUM(trend_score) as score
        FROM trend_scores 
        WHERE signal_date >= ? AND signal_date < ?
        GROUP BY keyword
    ''', (current_start, end_date)).fetchall()
    
    # 이전 기간 점수
    previous = t.execute('''
        SELECT keyword, SUM(trend_score) as score
        FROM trend_scores 
        WHERE signal_date >= ? AND signal_date < ?
        GROUP BY keyword
    ''', (previous_start, previous_end)).fetchall()
    
    current_map = {r['keyword']: r['score'] for r in current}
    previous_map = {r['keyword']: r['score'] for r in previous}
    
    new_entries = []
    rising = []
    cooling = []
    
    for kw in set(current_map) | set(previous_map):
        cur_s = current_map.get(kw, 0)
        prev_s = previous_map.get(kw, 0)
        
        if prev_s == 0 and cur_s > 0:
            new_entries.append({"keyword": kw, "score": cur_s})
        elif prev_s > 0 and cur_s == 0:
            cooling.append({"keyword": kw, "prev_score": prev_s})
        elif prev_s > 0 and cur_s >= prev_s * 1.5:
            rising.append({"keyword": kw, "prev_score": prev_s, "curr_score": cur_s})
        elif prev_s > 0 and cur_s <= prev_s * 0.5:
            cooling.append({"keyword": kw, "prev_score": prev_s, "curr_score": cur_s})
    
    new_entries.sort(key=lambda x: -x["score"])
    rising.sort(key=lambda x: -(x["curr_score"] - x["prev_score"]))
    cooling.sort(key=lambda x: (x["prev_score"] - x.get("curr_score", 0)) * -1 if x.get("curr_score") else -x["prev_score"])
    
    t.close()
    return {
        "period": period,
        "period_days": days,
        "new": new_entries[:15],
        "rising": rising[:15],
        "cooling": cooling[:15]
    }

def get_weekly_trends(limit: int = 25) -> dict:
    """주간 트렌드 (7일 집계)"""
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"date": None, "trends": [], "delta": {}}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=7)).isoformat()
    
    rows = t.execute('''
        SELECT keyword, 
               SUM(trend_score) as total_score,
               AVG(trend_score) as avg_score,
               MAX(trend_score) as peak_score,
               COUNT(DISTINCT signal_date) as active_days
        FROM trend_scores 
        WHERE signal_date >= ? AND signal_date <= ?
        GROUP BY keyword
        ORDER BY total_score DESC LIMIT ?
    ''', (start_date, end_date, limit)).fetchall()
    
    trends = []
    for r in rows:
        item = dict(r)
        item['theme'] = keyword_theme(item['keyword'])
        item['theme_info'] = THEME_LABELS.get(item['theme'], THEME_LABELS['other'])
        trends.append(item)
    
    delta = get_trend_delta("weekly")
    t.close()
    return {"date": end_date, "start_date": start_date, "trends": trends, "delta": delta}

def get_monthly_trends(limit: int = 30) -> dict:
    """월간 트렌드 (30일 집계)"""
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close()
        return {"date": None, "trends": [], "delta": {}}
    
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=30)).isoformat()
    
    rows = t.execute('''
        SELECT keyword, 
               SUM(trend_score) as total_score,
               AVG(trend_score) as avg_score,
               MAX(trend_score) as peak_score,
               COUNT(DISTINCT signal_date) as active_days
        FROM trend_scores 
        WHERE signal_date >= ? AND signal_date <= ?
        GROUP BY keyword
        ORDER BY total_score DESC LIMIT ?
    ''', (start_date, end_date, limit)).fetchall()
    
    trends = []
    for r in rows:
        item = dict(r)
        item['theme'] = keyword_theme(item['keyword'])
        item['theme_info'] = THEME_LABELS.get(item['theme'], THEME_LABELS['other'])
        trends.append(item)
    
    delta = get_trend_delta("monthly")
    t.close()
    return {"date": end_date, "start_date": start_date, "trends": trends, "delta": delta}

# ============================================================
# 기존 Dashboard (호환성 유지)
# ============================================================
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
# Product APIs (기존 유지)
# ============================================================
def load_products(limit=None, q=None, category=None, source=None, keyword=None, offset=0):
    c = get_catalog_db()
    cols = table_cols(c, 'products')
    attr_exists = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'"
    ).fetchone() is not None
    
    base = [
        'p.product_id', 'p.source', 'p.brand', 'p.product_name', 'p.product_url',
        'p.category', 'p.parent_category', 'p.price', 'p.sale_price', 'p.review_count',
        'p.rating', 'p.daiso_score', 'p.is_new', 'p.status'
    ]
    if attr_exists:
        base += [
            'a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns',
            'a.texture', 'a.key_ingredients', 'a.claims'
        ]
    else:
        for x in ('product_type', 'keywords', 'skin_type', 'concerns', 'texture', 'key_ingredients', 'claims'):
            if x in cols:
                base.append(f'p.{x}')
    
    where = ["p.status='ACTIVE'"]
    args = []
    if q or keyword:
        qv = f'%{q or keyword}%'
        search_fields = [
            'p.product_name', 'p.brand', 'p.category', 'p.parent_category'
        ]
        if attr_exists:
            search_fields += [
                'a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns',
                'a.texture', 'a.key_ingredients', 'a.claims'
            ]
        else:
            search_fields += [
                f'p.{x}' for x in ('product_type', 'keywords', 'skin_type', 'concerns', 'texture', 'key_ingredients', 'claims')
                if x in cols
            ]
        where.append('(' + ' OR '.join(
            f'LOWER(COALESCE({x},\'\')) LIKE LOWER(?)' for x in search_fields
        ) + ')')
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
    attr_exists = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'"
    ).fetchone() is not None
    
    fields = [
        'p.product_id', 'p.source', 'p.brand', 'p.product_name', 'p.product_url',
        'p.category', 'p.parent_category', 'p.price', 'p.sale_price',
        'p.review_count', 'p.rating', 'p.daiso_score', 'p.is_new'
    ]
    if attr_exists:
        fields += ['a.product_type', 'a.keywords', 'a.skin_type', 'a.concerns', 'a.texture', 'a.key_ingredients', 'a.claims']
    
    join = " LEFT JOIN product_attributes a ON a.product_id=p.product_id" if attr_exists else ""
    rows = [dict(r) for r in c.execute(
        f"SELECT {','.join(fields)} FROM products p{join} WHERE p.status='ACTIVE'"
    ).fetchall()]
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
