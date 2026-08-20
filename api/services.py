import json, math, re
from datetime import datetime, timedelta
from .database import get_catalog_db, get_trend_db, table_cols


def _latest_catalog_date(conn):
    cols=table_cols(conn,'daily_rankings')
    d=next((x for x in ('run_date','ranking_date','date','captured_at') if x in cols),None)
    if not d:return None,d
    r=conn.execute(f'SELECT MAX("{d}") d FROM daily_rankings').fetchone()
    return (r['d'] if r and r['d'] else None),d

def _trend_scores(conn):
    cols=table_cols(conn,'trend_scores')
    if not {'keyword','trend_score'}.issubset(cols): return {}
    date='signal_date' if 'signal_date' in cols else None
    if date:
        mx=conn.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
        rows=conn.execute('SELECT keyword, trend_score FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC',(mx,)).fetchall() if mx else []
    else: rows=conn.execute('SELECT keyword, trend_score FROM trend_scores ORDER BY trend_score DESC').fetchall()
    return {str(r['keyword']).strip().lower():float(r['trend_score'] or 0) for r in rows}

def _product_text(p):
    vals=[]
    for k in ('product_name','brand','category','parent_category','ingredients','product_type','keywords','skin_type','concerns','texture','key_ingredients','claims'):
        v=p.get(k)
        if v: vals.append(str(v))
    return ' '.join(vals).lower()

def _list_field(v):
    if not v:return []
    if isinstance(v,list):return v
    s=str(v).strip()
    try:
        x=json.loads(s)
        if isinstance(x,list):return [str(a).strip() for a in x if str(a).strip()]
    except Exception:pass
    return [x.strip() for x in re.split(r'[,|;/\n]+',s) if x.strip()]

def product_score(p, trend_map, olive_rank=None, daiso_score=None):
    # 0-100 unified score. Rank scores use smooth decay so rank 100 is still meaningfully different from rank 1.
    olive = (100.0 / (1.0 + 0.045*(olive_rank-1))) if olive_rank else 0.0
    daiso = float(daiso_score or 0)
    txt=_product_text(p)
    matched=[s for k,s in trend_map.items() if k and k in txt]
    trend=max(matched) if matched else 0.0
    reviews=float(p.get('review_count') or 0)
    rating=float(p.get('rating') or 0)
    review_score=min(100.0, math.log10(reviews+1)*22) if reviews else 0
    rating_score=min(100.0, rating/5*100) if rating else 0
    new_bonus=8 if p.get('is_new') else 0
    # Channel presence + momentum + quality. Missing channels are not punished as hard as a zero score.
    parts=[]; weights=[]
    if olive_rank: parts.append(olive); weights.append(0.32)
    if daiso_score: parts.append(daiso); weights.append(0.25)
    if trend: parts.append(trend); weights.append(0.23)
    if review_score: parts.append(review_score); weights.append(0.12)
    if rating_score: parts.append(rating_score); weights.append(0.08)
    if not parts:return round(float(new_bonus),1)
    base=sum(v*w for v,w in zip(parts,weights))/sum(weights)
    return round(min(100.0,base+new_bonus),1)

def load_rank_maps(conn, latest):
    dcol=_latest_catalog_date(conn)[1]
    if not dcol or not latest:return {},{}
    rcol='rank_num' if 'rank_num' in table_cols(conn,'daily_rankings') else 'rank'
    rows=conn.execute(f'SELECT product_id,{rcol} rank_num,source FROM daily_rankings WHERE "{dcol}"=?',(latest,)).fetchall()
    olive={}; daiso={}
    for r in rows:
        if r['source']=='oliveyoung': olive[r['product_id']]=r['rank_num']
        elif r['source']=='daiso': daiso[r['product_id']]=r['rank_num']
    return olive,daiso

def load_products(limit=None, q=None, category=None, source=None, keyword=None, offset=0):
    c = get_catalog_db()
    cols = table_cols(c, 'products')
    attr_exists = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'"
    ).fetchone() is not None

    base = [
        'p.product_id','p.source','p.brand','p.product_name','p.product_url',
        'p.category','p.parent_category','p.price','p.sale_price','p.review_count',
        'p.rating','p.daiso_score','p.is_new','p.status'
    ]
    if attr_exists:
        base += [
            'a.product_type','a.keywords','a.skin_type','a.concerns',
            'a.texture','a.key_ingredients','a.claims'
        ]
    else:
        for x in ('product_type','keywords','skin_type','concerns','texture','key_ingredients','claims'):
            if x in cols:
                base.append(f'p.{x}')

    where = ["p.status='ACTIVE'"]
    args = []

    if q or keyword:
        qv = f'%{q or keyword}%'
        search_fields = [
            'p.product_name','p.brand','p.category','p.parent_category'
        ]
        if attr_exists:
            search_fields += [
                'a.product_type','a.keywords','a.skin_type','a.concerns',
                'a.texture','a.key_ingredients','a.claims'
            ]
        else:
            search_fields += [
                f'p.{x}' for x in ('product_type','keywords','skin_type','concerns','texture','key_ingredients','claims')
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

def get_trend_dashboard():
    c=get_catalog_db(); latest,_=_latest_catalog_date(c); c.close()
    t=get_trend_db();
    tm=_trend_scores(t)
    # latest trend scores
    trend_rows=[]
    if table_cols(t,'trend_scores'):
        mx=t.execute('SELECT MAX(signal_date) d FROM trend_scores').fetchone()['d']
        if mx:
            trend_rows=[dict(r) for r in t.execute('SELECT keyword,volume_score,velocity_score,persistence_score,cross_platform_score,regional_score,trend_score FROM trend_scores WHERE signal_date=? ORDER BY trend_score DESC LIMIT 20',(mx,)).fetchall()]
    google=[]
    if table_cols(t,'google_signals'):
        mx=t.execute('SELECT MAX(signal_date) d FROM google_signals').fetchone()['d']
        if mx:
            google=[dict(r) for r in t.execute('SELECT keyword,region,interest_score,rising_score,source FROM google_signals WHERE signal_date=? ORDER BY rising_score DESC, interest_score DESC LIMIT 20',(mx,)).fetchall()]
    raw_count=t.execute('SELECT COUNT(*) c FROM raw_signals').fetchone()['c'] if table_cols(t,'raw_signals') else 0
    t.close()
    return {'latest_catalog':latest,'trends':trend_rows,'google':google,'raw_signal_count':raw_count,'top_keywords':[{'keyword':k,'score':v} for k,v in list(tm.items())[:20]]}

def ranking_rows(kind='overall', limit=50):
    c = get_catalog_db()
    latest, _ = _latest_catalog_date(c)
    olive, daiso = load_rank_maps(c, latest)
    cols = table_cols(c, 'products')
    attr_exists = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_attributes'"
    ).fetchone() is not None

    fields = [
        'p.product_id','p.source','p.brand','p.product_name','p.product_url',
        'p.category','p.parent_category','p.price','p.sale_price',
        'p.review_count','p.rating','p.daiso_score','p.is_new'
    ]
    if attr_exists:
        fields += ['a.product_type','a.keywords','a.skin_type','a.concerns','a.texture','a.key_ingredients','a.claims']

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

