from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .services import (
    get_trend_dashboard, ranking_rows, load_products,
    get_ranking_change, get_search_suggestions
)
from .database import get_catalog_db, table_cols, sync_source_databases

BASE = Path(__file__).resolve().parent.parent
STATIC = BASE / 'static'

app = FastAPI(title='K-Beauty Trend Intelligence', version='6.0.0')

@app.on_event('startup')
def startup_sync_databases():
    sync_source_databases()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*']
)

if STATIC.exists():
    app.mount('/static', StaticFiles(directory=STATIC), name='static')

@app.get('/')
def root():
    return FileResponse(STATIC / 'index.html')

@app.get('/health')
def health():
    return {'status': 'healthy', 'version': '6.0.0'}

# ============================================================
# Trend APIs
# ============================================================
@app.get('/api/dashboard')
def dashboard():
    return get_trend_dashboard()

@app.get('/api/trends')
def trends(limit: int = Query(50, ge=1, le=500)):
    d = get_trend_dashboard()
    return {'latest_catalog': d['latest_catalog'], 'items': d['trends'][:limit]}

@app.get('/api/google')
def google(limit: int = Query(50, ge=1, le=500)):
    d = get_trend_dashboard()
    return {'items': d['google'][:limit]}

# ============================================================
# Ranking APIs
# ============================================================
@app.get('/api/rankings')
def rankings(kind: str = Query('overall'), limit: int = Query(50, ge=1, le=500)):
    items, date = ranking_rows(kind, limit)
    return {'kind': kind, 'latest_date': date, 'items': items}

@app.get('/api/rankings/change')
def rankings_change(limit: int = Query(50, ge=1, le=200)):
    """랭킹 변동 데이터 (신규/상승/하락)"""
    return get_ranking_change(limit=limit)

# ============================================================
# Product APIs
# ============================================================
@app.get('/api/products')
def products(q: str | None = None, category: str | None = None,
             source: str | None = None, keyword: str | None = None,
             limit: int = Query(200, ge=1, le=5000), offset: int = Query(0, ge=0)):
    items, date = load_products(limit, q, category, source, keyword, offset)
    return {'latest_date': date, 'count': len(items), 'has_more': len(items) == limit, 'items': items}

@app.get('/api/products/{product_id}')
def product_detail(product_id: str):
    items, _ = load_products(None, None, None, None, None)
    p = next((x for x in items if x['product_id'] == product_id), None)
    if not p:
        return {'found': False, 'product': None}
    c = get_catalog_db()
    snaps = []
    ranks = []
    if 'product_snapshots' in [r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        snaps = [dict(r) for r in c.execute('SELECT captured_at, price, sale_price, source, status FROM product_snapshots WHERE product_id=? ORDER BY id DESC LIMIT 30', (product_id,)).fetchall()]
    if 'daily_rankings' in [r['name'] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cols = table_cols(c, 'daily_rankings')
        d = next((x for x in ('run_date', 'ranking_date', 'date', 'captured_at') if x in cols), None)
        rcol = 'rank_num' if 'rank_num' in cols else 'rank'
        if d:
            ranks = [dict(r) for r in c.execute(f'SELECT {d} ranking_date, source, category, {rcol} rank_num FROM daily_rankings WHERE product_id=? ORDER BY {d} DESC LIMIT 60', (product_id,)).fetchall()]
    c.close()
    return {'found': True, 'product': p, 'snapshots': snaps, 'rankings': ranks}

@app.get('/api/categories')
def categories():
    c = get_catalog_db()
    rows = c.execute("SELECT COALESCE(parent_category, category, 'Other') category, COUNT(*) count FROM products WHERE status='ACTIVE' GROUP BY 1 ORDER BY count DESC").fetchall()
    c.close()
    return {'items': [dict(r) for r in rows]}

# ============================================================
# Search Suggestions
# ============================================================
@app.get('/api/suggestions')
def suggestions(limit: int = Query(40, ge=1, le=100)):
    return {'items': get_search_suggestions(limit)}
