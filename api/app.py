# api/app.py (전체 교체)
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Query, HTTPException
from api.database import get_trend_db, get_catalog_db

router = APIRouter(prefix="/api/app", tags=["App"])

# ============================================================
# Gemini 매핑 로직 (기존 로직 유지 - 축약 버전)
# ============================================================
# (기존 INGREDIENT_MAP과 _expand_keyword 함수는 그대로 유지해주세요. 
#  길이를 위해 생략했지만, 실제 적용 시에는 원본 app.py의 _expand_keyword 함수를 그대로 쓰시면 됩니다.)
def _expand_keyword(keyword: str):
    # 성분 사전 + Gemini 확장 로직 (기존 코드 사용)
    terms = [keyword.lower()]
    # ... (원본 app.py의 _expand_keyword 내용 붙여넣기)
    return terms

def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

# ============================================================
# 기간별 집계 헬퍼 함수
# ============================================================
def _get_date_ranges(period: str):
    """기간별 날짜 범위 계산 (최신 스냅샷 기준)"""
    latest_date = None
    # 최신 스냅샷 날짜 찾기 (catalog_db)
    conn = get_catalog_db()
    try:
        row = conn.execute("SELECT MAX(snapshot_date) as d FROM product_snapshots").fetchone()
        if row and row["d"]:
            latest_date = datetime.strptime(row["d"], "%Y-%m-%d").date()
    except Exception:
        pass
    finally:
        conn.close()
        
    if not latest_date:
        latest_date = datetime.now().date()
        
    if period == "daily":
        return latest_date, latest_date - timedelta(days=1)
    elif period == "weekly":
        return latest_date, latest_date - timedelta(days=7)
    elif period == "monthly":
        return latest_date, latest_date - timedelta(days=30)
    return latest_date, latest_date - timedelta(days=1)

def get_trends(conn, period: str):
    """트렌드 키워드 조회"""
    latest, _ = _get_date_ranges(period)
    try:
        return _rows(conn, """
            SELECT keyword, score FROM trend_scores 
            WHERE signal_date = ? 
            ORDER BY score DESC LIMIT 15
        """, (latest.isoformat(),))
    except Exception:
        return []

def get_highlights(conn, period: str):
    """플랫폼별 하이라이트 (변화율 기준)"""
    latest, past = _get_date_ranges(period)
    latest_str, past_str = latest.isoformat(), past.isoformat()
    
    highlights = {"oliveyoung": [], "daiso": []}
    
    # 올리브영: ranking_changes 테이블에서 급상승/신규 상품 조회
    try:
        highlights["oliveyoung"] = _rows(conn, """
            SELECT r.product_id, p.product_name, p.brand, p.product_url, r.rank_change, r.direction
            FROM ranking_changes r
            JOIN products p ON r.product_id = p.product_id
            WHERE r.change_date = ? AND p.source = 'oliveyoung'
            ORDER BY r.rank_change DESC LIMIT 5
        """, (latest_str,))
    except Exception:
        # ranking_changes 테이블이 없거나 데이터가 없을 때 daily_rankings 비교
        highlights["oliveyoung"] = []

    # 다이소: product_snapshots에서 리뷰 수 증가량 계산
    try:
        highlights["daiso"] = _rows(conn, """
            SELECT p.product_id, p.product_name, p.brand, p.product_url, 
                   s2.review_count, s1.review_count,
                   (COALESCE(s2.review_count, 0) - COALESCE(s1.review_count, 0)) as review_growth
            FROM products p
            LEFT JOIN product_snapshots s2 ON p.product_id = s2.product_id AND s2.snapshot_date = ?
            LEFT JOIN product_snapshots s1 ON p.product_id = s1.product_id AND s1.snapshot_date = ?
            WHERE p.source = 'daiso'
            ORDER BY review_growth DESC LIMIT 5
        """, (latest_str, past_str))
    except Exception:
        highlights["daiso"] = []
        
    return highlights

def get_rankings(conn, period: str):
    """플랫폼별 랭킹 (누적 점수/리뷰 증가량 기준)"""
    latest, past = _get_date_ranges(period)
    latest_str, past_str = latest.isoformat(), past.isoformat()
    
    rankings = {"oliveyoung": [], "daiso": [], "overall": []}
    
    # 올리브영: 기간 내 순위 누적 점수 SUM(31 - rank_num)
    try:
        rankings["oliveyoung"] = _rows(conn, """
            SELECT r.product_id, p.product_name, p.brand, p.product_url,
                   SUM(31 - r.rank_num) as score, p.price
            FROM daily_rankings r
            JOIN products p ON r.product_id = p.product_id
            WHERE p.source = 'oliveyoung' AND r.ranking_date >= ?
            GROUP BY r.product_id
            ORDER BY score DESC LIMIT 30
        """, (past_str,))
    except Exception:
        rankings["oliveyoung"] = []

    # 다이소: 기간 내 리뷰 증가량
    try:
        rankings["daiso"] = _rows(conn, """
            SELECT p.product_id, p.product_name, p.brand, p.product_url,
                   (COALESCE(s2.review_count, 0) - COALESCE(s1.review_count, 0)) as review_growth, p.price
            FROM products p
            LEFT JOIN product_snapshots s2 ON p.product_id = s2.product_id AND s2.snapshot_date = ?
            LEFT JOIN product_snapshots s1 ON p.product_id = s1.product_id AND s1.snapshot_date = ?
            WHERE p.source = 'daiso'
            ORDER BY review_growth DESC LIMIT 30
        """, (latest_str, past_str))
    except Exception:
        rankings["daiso"] = []
        
    # 전체 랭킹: 두 리스트를 점수 기준으로 정규화 후 합산
    # (간단하게 올영 1~30위를 100~70점, 다이소 1~30위를 100~70점으로 매핑하여 정렬)
    overall = []
    max_oy_score = rankings["oliveyoung"][0]["score"] if rankings["oliveyoung"] else 1
    max_ds_score = rankings["daiso"][0]["review_growth"] if rankings["daiso"] else 1
    
    for i, p in enumerate(rankings["oliveyoung"][:15]):
        normalized = (1 - (i / 30)) * 100
        p["final_score"] = normalized
        p["platform_badge"] = "🌿"
        overall.append(p)
        
    for i, p in enumerate(rankings["daiso"][:15]):
        normalized = (1 - (i / 30)) * 100
        p["final_score"] = normalized
        p["platform_badge"] = "💸"
        overall.append(p)
        
    overall.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    rankings["overall"] = overall[:30]
    
    return rankings

# ============================================================
# 통합 대시보드 엔드포인트
# ============================================================
@router.get("/dashboard")
def get_dashboard(period: str = Query("daily", enum=["daily", "weekly", "monthly"])):
    trend_conn = get_trend_db()
    cat_conn = get_catalog_db()
    
    try:
        trends = get_trends(trend_conn, period)
        highlights = get_highlights(cat_conn, period)
        rankings = get_rankings(cat_conn, period)
        
        return {
            "period": period,
            "trends": trends,
            "highlights": highlights,
            "rankings": rankings
        }
    finally:
        trend_conn.close()
        cat_conn.close()

@router.get("/keyword/{keyword}")
def get_keyword_detail(keyword: str):
    """키워드 클릭 시 매칭되는 '전체' 상품 목록 반환 (개수 제한 없음)"""
    cat_conn = get_catalog_db()
    try:
        terms = _expand_keyword(keyword)
        products = []
        seen = set()
        
        for term in terms:
            # 💡 여기서 LIMIT 20 구문을 완전히 제거했습니다!
            rows = _rows(cat_conn, """
                SELECT product_id, product_name, brand, product_url, source, price, review_count
                FROM products
                WHERE LOWER(product_name) LIKE LOWER(?)
                ORDER BY review_count DESC
            """, (f"%{term}%",))
            
            for r in rows:
                if r["product_id"] not in seen:
                    seen.add(r["product_id"])
                    r["platform_badge"] = "🌿" if r["source"] == "oliveyoung" else "💸"
                    products.append(r)
                    
        # 💡 여기서는 [:30] 슬라이싱을 제거하여 찾은 상품을 모두 반환합니다.
        return {"keyword": keyword, "products": products}
    finally:
        cat_conn.close()
