import json, math, re
from datetime import datetime, timedelta
from .database import get_catalog_db, get_trend_db, table_cols

THEME_RULES = [
    ("barrier_soothing", ["ceramide","centella","cica","panthenol","ectoin","barrier","sensitive skin","redness","rosacea","soothing"]),
    ("sun_protection", ["sunscreen","sun stick","sunstick","spf","sun care"]),
    ("acne_pore", ["salicylic","azelaic","acne","pore","blemish","bha","aha"]),
    ("brightening_pigment", ["vitamin c","niacinamide","tranexamic","kojic","dark spot","hyperpigmentation","brightening","glow"]),
    ("antiaging_regeneration", ["retinol","retinal","bakuchiol","peptide","collagen","exosome","pdrn","polynucleotide","antiaging","anti-aging","firming","reedle","spicule","volufiline"]),
    ("hydration", ["hyaluronic","hydrat","dry skin","dehydrated","snail","propolis","squalane","urea"]),
]
THEME_META = {
    "barrier_soothing": {"icon":"🛡️","color":"#10b981"},
    "sun_protection": {"icon":"☀️","color":"#f59e0b"},
    "acne_pore": {"icon":"🔴","color":"#ef4444"},
    "brightening_pigment": {"icon":"✨","color":"#fbbf24"},
    "antiaging_regeneration": {"icon":"💎","color":"#8b5cf6"},
    "hydration": {"icon":"💧","color":"#3b82f6"},
}

def keyword_theme(keyword):
    kw = (keyword or "").lower()
    for theme, terms in THEME_RULES:
        if any(t in kw for t in terms):
            return theme
    return "other"

def _latest_catalog_date(conn):
    cols = table_cols(conn, 'daily_rankings')
    d = next((x for x in ('run_date','ranking_date','date','captured_at') if x in cols), None)
    if not d: return None, d
    r = conn.execute(f'SELECT MAX("{d}") d FROM daily_rankings').fetchone()
    return (r['d'] if r and r['d'] else None), d

def _product_text(p):
    vals = []
    for k in ('product_name','brand','category','parent_category','ingredients','product_type','keywords','skin_type','concerns','texture','key_ingredients','claims'):
        v = p.get(k)
        if v: vals.append(str(v))
    return ' '.join(vals).lower()

def _list_field(v):
    if not v: return []
    if isinstance(v, list): return v
    s = str(v).strip()
    try:
        x = json.loads(s)
        if isinstance(x, list): return [str(a).strip() for a in x if str(a).strip()]
    except Exception: pass
    return [x.strip() for x in re.split(r'[,|;\n]+', s) if x.strip()]

def _trend_scores(conn):
    cols = table_cols(conn, 'trend_scores')
    if not {'keyword','trend_score'}.issubset(cols): return {}
    mx = conn.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    rows = conn.execute('SELECT keyword, trend_score FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC', (mx,)).fetchall() if mx else []
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
    parts, weights = [], []
    if olive_rank: parts.append(olive); weights.append(0.32)
    if daiso_score: parts.append(daiso); weights.append(0.25)
    if trend: parts.append(trend); weights.append(0.23)
    if review_score: parts.append(review_score); weights.append(0.12)
    if rating_score: parts.append(rating_score); weights.append(0.08)
    if not parts: return round(float(new_bonus), 1)
    base = sum(v*w for v, w in zip(parts, weights)) / sum(weights)
    return round(min(100.0, base + new_bonus), 1)

def load_rank_maps(conn, latest):
    dcol = _latest_catalog_date(conn)[1]
    if not dcol or not latest: return {}, {}
    rcol = 'rank_num' if 'rank_num' in table_cols(conn, 'daily_rankings') else 'rank'
    rows = conn.execute(f'SELECT product_id, {rcol} rank_num, source FROM daily_rankings WHERE "{dcol}"=?', (latest,)).fetchall()
    olive, daiso = {}, {}
    for r in rows:
        if r['source'] == 'oliveyoung': olive[r['product_id']] = r['rank_num']
        elif r['source'] == 'daiso': daiso[r['product_id']] = r['rank_num']
    return olive, daiso

def get_daily_trends(limit=50):
    t = get_trend_db()
    try:
        mx = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()
        if not mx or not mx['d']:
            t.close(); return {"date": None, "trends": [], "raw_signal_count": 0, "google": []}
        max_date = mx['d']
        cols = table_cols(t, 'trend_scores')
        sel = ['keyword','trend_score']
        for c in ['volume_score','velocity_score','persistence_score','cross_platform_score','regional_score','platform_normalized_score']:
            if c in cols: sel.append(c)
        rows = t.execute(f'SELECT {", ".join(sel)} FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC LIMIT ?', (max_date, limit)).fetchall()
        trends = []
        for r in rows:
            item = dict(r)
            item.setdefault('velocity_score', 0); item.setdefault('cross_platform_score', 0); item.setdefault('persistence_score', 0)
            item['has_history'] = bool(item.get('velocity_score'))
            item['theme'] = keyword_theme(r['keyword'])
            trends.append(item)
        raw_count = 0
        tables = [x[0] for x in t.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'raw_signals' in tables:
            raw_count = t.execute('SELECT COUNT(*) c FROM raw_signals').fetchone()['c']
        google = []
        if 'google_signals' in tables:
            gmx = t.execute('SELECT MAX(signal_date) d FROM google_signals').fetchone()
            if gmx and gmx['d']:
                google = [dict(r) for r in t.execute('SELECT keyword, region, intent, interest_score, rising_score, source FROM google_signals WHERE signal_date=? ORDER BY rising_score DESC LIMIT 20', (gmx['d'],)).fetchall()]
        t.close()
        return {"date": max_date, "trends": trends, "raw_signal_count": raw_count, "google": google}
    except Exception as e:
        print(f"[Trend API Error] {e}")
        t.close()
        return {"date": None, "trends": [], "raw_signal_count": 0, "google": []}

def get_theme_rollup(days=7):
    t = get_trend_db()
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close(); return {"themes": []}
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    rows = t.execute('SELECT keyword, SUM(trend_score) AS total_score, COUNT(DISTINCT signal_date) AS active_days, AVG(trend_score) AS avg_score FROM trend_scores WHERE signal_date >= ? AND signal_date <= ? GROUP BY keyword', (start_date, end_date)).fetchall()
    t.close()
    themes = {}
    for r in rows:
        theme = keyword_theme(r['keyword'])
        if theme == "other": continue
        agg = themes.setdefault(theme, {"keywords": [], "total_score": 0, "count": 0})
        agg["keywords"].append({"keyword": r['keyword'], "score": r['total_score'], "active_days": r['active_days'], "avg_score": r['avg_score']})
        agg["total_score"] += r['total_score']; agg["count"] += 1
    result = []
    for theme, data in themes.items():
        meta = THEME_META.get(theme, {"icon":"📦","color":"#6b7280"})
        top = sorted(data["keywords"], key=lambda x: -x["score"])
        result.append({"theme": theme, "icon": meta["icon"], "color": meta["color"], "total_score": data["total_score"], "keyword_count": data["count"], "top_keywords": top})
    result.sort(key=lambda x: -x["total_score"])
    return {"themes": result, "period_days": days}

def get_trend_delta(period="weekly"):
    t = get_trend_db()
    days = 7 if period == "weekly" else 30
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close(); return {"new": [], "rising": [], "cooling": []}
    cur_start = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    prev_end = cur_start
    prev_start = (datetime.fromisoformat(prev_end) - timedelta(days=days)).isoformat()
    cur = t.execute('SELECT keyword, SUM(trend_score) s FROM trend_scores WHERE signal_date >= ? AND signal_date <= ? GROUP BY keyword', (cur_start, end_date)).fetchall()
    prev = t.execute('SELECT keyword, SUM(trend_score) s FROM trend_scores WHERE signal_date >= ? AND signal_date < ? GROUP BY keyword', (prev_start, prev_end)).fetchall()
    t.close()
    cm = {r['keyword']: r['s'] for r in cur}; pm = {r['keyword']: r['s'] for r in prev}
    new_e, rising, cooling = [], [], []
    for kw in set(cm) | set(pm):
        c, p = cm.get(kw, 0), pm.get(kw, 0)
        if p == 0 and c > 0: new_e.append({"keyword": kw, "score": c})
        elif p > 0 and c == 0: cooling.append({"keyword": kw, "prev_score": p})
        elif p > 0 and c >= p * 1.5: rising.append({"keyword": kw, "prev_score": p, "curr_score": c})
        elif p > 0 and c <= p * 0.5: cooling.append({"keyword": kw, "prev_score": p, "curr_score": c})
    new_e.sort(key=lambda x: -x["score"]); rising.sort(key=lambda x: -(x["curr_score"]-x["prev_score"])); cooling.sort(key=lambda x: -x["prev_score"])
    return {"period": period, "new": new_e[:15], "rising": rising[:15], "cooling": cooling[:15]}

def _period_trends(period, limit):
    t = get_trend_db()
    days = 7 if period == "weekly" else 30
    end_date = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
    if not end_date:
        t.close(); return {"date": None, "trends": [], "delta": {}}
    start_date = (datetime.fromisoformat(end_date) - timedelta(days=days)).isoformat()
    rows = t.execute('SELECT keyword, SUM(trend_score) total_score, AVG(trend_score) avg_score, COUNT(DISTINCT signal_date) active_days FROM trend_scores WHERE signal_date >= ? AND signal_date <= ? GROUP BY keyword ORDER BY total_score DESC LIMIT ?', (start_date, end_date, limit)).fetchall()
    t.close()
    trends = [{"keyword": r['keyword'], "total_score": r['total_score'], "avg_score": r['avg_score'], "active_days": r['active_days'], "theme": keyword_theme(r['keyword'])} for r in rows]
    return {"date": end_date, "start_date": start_date, "trends": trends, "delta": get_trend_delta(period)}

def get_weekly_trends(limit=25): return _period_trends("weekly", limit)
def get_monthly_trends(limit=30): return _period_trends("monthly", limit)

def get_trend_dashboard():
    d = get_daily_trends(limit=20)
    return {"latest_catalog": None, "trends": d["trends"], "google": d["google"], "raw_signal_count": d["raw_signal_count"], "top_keywords": [{"keyword": t["keyword"], "score": t["trend_score"]} for t in d["trends"][:20]]}

def load_products(limit=None, q=None, category=None, source=None, keyword=None, offset=0):
    c = get_catalog_db()
    cols = table_cols(c, 'products')
    attr_exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'").fetchone() is not None
    has_en = 'product_name_en' in cols
    base = ['p.product_id','p.source','p.brand','p.product_name','p.product_url','p.category','p.parent_category','p.price','p.sale_price','p.review_count','p.rating','p.daiso_score','p.is_new','p.status']
    if has_en: base.append('p.product_name_en')
    if attr_exists:
        base += ['a.product_type','a.keywords','a.skin_type','a.concerns','a.texture','a.key_ingredients','a.claims']
    else:
        for x in ('product_type','keywords','skin_type','concerns','texture','key_ingredients','claims'):
            if x in cols: base.append(f'p.{x}')
    where = ["p.status='ACTIVE'"]; args = []
    if q or keyword:
        qv = f'%{q or keyword}%'
        sf = ['p.product_name','p.brand','p.category','p.parent_category']
        if has_en: sf.append('p.product_name_en')
        if attr_exists: sf += ['a.product_type','a.keywords','a.skin_type','a.concerns','a.texture','a.key_ingredients','a.claims']
        else: sf += [f'p.{x}' for x in ('product_type','keywords','skin_type','concerns','texture','key_ingredients','claims') if x in cols]
        where.append('(' + ' OR '.join(f'LOWER(COALESCE({x},\'\')) LIKE LOWER(?)' for x in sf) + ')')
        args += [qv] * len(sf)
    if category: where.append('(p.category=? OR p.parent_category=?)'); args += [category, category]
    if source: where.append('p.source=?'); args.append(source)
    join = " LEFT JOIN product_attributes a ON a.product_id=p.product_id" if attr_exists else ""
    sql = f"SELECT {','.join(base)} FROM products p{join} WHERE " + ' AND '.join(where)
    if limit: sql += f' LIMIT {int(limit)} OFFSET {int(offset)}'
    rows = [dict(r) for r in c.execute(sql, args).fetchall()]
    latest, _ = _latest_catalog_date(c)
    olive, daiso = load_rank_maps(c, latest)
    t = get_trend_db(); tm = _trend_scores(t); t.close()
    for p in rows:
        p['olive_rank'] = olive.get(p['product_id']); p['daiso_rank'] = daiso.get(p['product_id'])
        p['overall_score'] = product_score(p, tm, p['olive_rank'], p.get('daiso_score'))
        p['keyword_list'] = _list_field(p.get('keywords')); p['ingredient_list'] = _list_field(p.get('key_ingredients'))
    c.close()
    return rows, latest

def ranking_rows(kind='overall', limit=50):
    c = get_catalog_db()
    latest, _ = _latest_catalog_date(c)
    olive, daiso = load_rank_maps(c, latest)
    attr_exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'").fetchone() is not None
    cols = table_cols(c, 'products')
    fields = ['p.product_id','p.source','p.brand','p.product_name','p.product_url','p.category','p.parent_category','p.price','p.sale_price','p.review_count','p.rating','p.daiso_score','p.is_new']
    if 'product_name_en' in cols: fields.append('p.product_name_en')
    if attr_exists: fields += ['a.product_type','a.keywords','a.skin_type','a.concerns','a.texture','a.key_ingredients','a.claims']
    join = " LEFT JOIN product_attributes a ON a.product_id=p.product_id" if attr_exists else ""
    rows = [dict(r) for r in c.execute(f"SELECT {','.join(fields)} FROM products p{join} WHERE p.status='ACTIVE'").fetchall()]
    c.close()
    t = get_trend_db(); tm = _trend_scores(t); t.close()
    for p in rows:
        p['olive_rank'] = olive.get(p['product_id']); p['daiso_rank'] = daiso.get(p['product_id'])
        p['overall_score'] = product_score(p, tm, p['olive_rank'], p.get('daiso_score'))
        p['keyword_list'] = _list_field(p.get('keywords')); p['ingredient_list'] = _list_field(p.get('key_ingredients'))
    if kind == 'olive':
        rows = [p for p in rows if p['olive_rank']]; rows.sort(key=lambda x: x['olive_rank'])
    elif kind == 'daiso':
        rows = [p for p in rows if p.get('daiso_score')]; rows.sort(key=lambda x: float(x.get('daiso_score') or 0), reverse=True)
    else:
        rows.sort(key=lambda x: x['overall_score'], reverse=True)
    for i, p in enumerate(rows[:limit], 1): p['display_rank'] = i
    return rows[:limit], latest

def get_ranking_change(limit=50):
    c = get_catalog_db()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'daily_rankings' not in tables:
        c.close(); return {"new": [], "rising": [], "falling": []}
    cols = table_cols(c, 'daily_rankings')
    dcol = next((x for x in ('run_date','ranking_date','date','captured_at') if x in cols), None)
    if not dcol:
        c.close(); return {"new": [], "rising": [], "falling": []}
    rcol = 'rank_num' if 'rank_num' in cols else 'rank'
    dates = c.execute(f"SELECT DISTINCT {dcol} FROM daily_rankings ORDER BY {dcol} DESC LIMIT 2").fetchall()
    if len(dates) < 2:
        c.close(); return {"new": [], "rising": [], "falling": []}
    pcols = table_cols(c, 'products')
    name_en_sel = ", p.product_name_en" if 'product_name_en' in pcols else ""
    today_rows = c.execute(f"SELECT r.product_id, r.{rcol} AS rank_num, r.source, COALESCE(p.product_url, p.product_id) AS product_url, p.product_name{name_en_sel} FROM daily_rankings r LEFT JOIN products p ON p.product_id=r.product_id WHERE r.{dcol}=?", (dates[0][dcol],)).fetchall()
    yesterday_rows = c.execute(f"SELECT product_id, {rcol} AS rank_num FROM daily_rankings WHERE {dcol}=?", (dates[1][dcol],)).fetchall()
    today_map = {r['product_id']: {'rank': r['rank_num'], 'source': r['source'], 'product_url': r['product_url'], 'product_name': r['product_name'], 'product_name_en': r['product_name_en'] if 'product_name_en' in pcols else None} for r in today_rows}
    yesterday_map = {r['product_id']: r['rank_num'] for r in yesterday_rows}
    new_e, rising, falling = [], [], []
    for pid, ti in today_map.items():
        base = {"product_id": pid, "product_name": ti.get('product_name') or pid, "product_name_en": ti.get('product_name_en'), "source": ti['source'], "product_url": ti.get('product_url') or "#", "rank": ti['rank']}
        if pid not in yesterday_map:
            new_e.append(base)
        else:
            diff = yesterday_map[pid] - ti['rank']
            if diff > 0: rising.append({**base, "diff": diff})
            elif diff < 0: falling.append({**base, "diff": abs(diff)})
    new_e.sort(key=lambda x: x['rank']); rising.sort(key=lambda x: -x['diff']); falling.sort(key=lambda x: -x['diff'])
    c.close()
    return {"new": new_e[:limit], "rising": rising[:limit], "falling": falling[:limit]}

def get_search_suggestions(limit=40):
    out = []
    try:
        t = get_trend_db()
        mx = t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
        if mx:
            rows = t.execute('SELECT keyword FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC LIMIT 20', (mx,)).fetchall()
            out += [r['keyword'] for r in rows]
        t.close()
    except Exception:
        pass
    out += ["레티놀 세럼","레티날 크림","시카 수분 크림","히알루론산 토너","나이아신아마이드 세럼","비타민C 세럼","센텔라 수분 마스크","엑소좀 스부스터","PDRN 연어 주사","폴리뉴클레오타이드","세라마이드 장벽 크림","병풀 추출물","스피큘 토닝","아젤라산 세럼","살리실산 각질","판테놀 수분","스쿠알란 오일","자외선 차단제","선스틱","유기자차","무기자차","여드름 트러블","모공 관리","색소침착","미백 기능성","안티에이징","주름 개선","탄력","수분 공급","장벽 강화"]
    seen, res = set(), []
    for k in out:
        k = str(k).strip()
        if k and k.lower() not in seen:
            seen.add(k.lower()); res.append(k)
        if len(res) >= limit: break
    return res
