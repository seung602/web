import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

try:
    from api.database import get_catalog_db
except Exception:
    from database import get_catalog_db

router = APIRouter(prefix="/api/periods", tags=["Periods"])
logger = logging.getLogger(__name__)

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


@router.get("/rankings")
def get_period_rankings(period: str = Query("daily"), limit: int = Query(30)):
    """일간/주간/월간 랭킹 + 순위 변동 + 다이소 자체랭킹 반환"""
    days = PERIOD_DAYS.get(period, 1)
    conn = get_catalog_db()
    try:
        row = conn.execute(
            "SELECT MAX(run_date) AS d FROM daily_rankings WHERE source='oliveyoung'"
        ).fetchone()
        latest = row["d"] if row else None
        if not latest:
            return {"period": period, "insufficient": True, "latest_date": None,
                    "base_date": None, "rankings": [], "rising": [], "daiso": []}

        latest_d = datetime.strptime(latest, "%Y-%m-%d")
        target = (latest_d - timedelta(days=days)).strftime("%Y-%m-%d")
        base_row = conn.execute(
            "SELECT MAX(run_date) AS d FROM daily_rankings "
            "WHERE source='oliveyoung' AND run_date <= ?", (target,)
        ).fetchone()
        base = base_row["d"] if base_row and base_row["d"] else None

        insufficient = False
        if period != "daily":
            if base is None:
                insufficient = True
            else:
                days_diff = (latest_d - datetime.strptime(base, "%Y-%m-%d")).days
                insufficient = days_diff < (days - 2)

        cur = conn.execute(
            """SELECT r.rank_num, r.product_id, p.brand, p.product_name, p.product_url,
                      p.price, p.sale_price
               FROM daily_rankings r LEFT JOIN products p ON p.product_id = r.product_id
               WHERE r.source='oliveyoung' AND r.run_date=?
               ORDER BY r.rank_num ASC LIMIT 100""", (latest,)
        ).fetchall()

        base_map = {}
        if base and not insufficient:
            for b in conn.execute(
                "SELECT product_id, rank_num FROM daily_rankings "
                "WHERE source='oliveyoung' AND run_date=?", (base,)
            ).fetchall():
                base_map[b["product_id"]] = b["rank_num"]

        rankings = []
        for c in cur:
            item = dict(c)
            item["source"] = "oliveyoung"
            prev = base_map.get(item["product_id"])
            item["previous_rank"] = prev
            item["change"] = (prev - item["rank_num"]) if prev else None
            rankings.append(item)

        rising = sorted([r for r in rankings if r["change"]],
                        key=lambda x: -x["change"])[:10]

        daiso = conn.execute(
            """SELECT product_id, brand, product_name, product_url, price, sale_price, daiso_score
               FROM products
               WHERE source='daiso' AND status='ACTIVE' AND daiso_score > 0
               ORDER BY daiso_score DESC LIMIT 10"""
        ).fetchall()

        return {
            "period": period, "insufficient": insufficient,
            "latest_date": latest, "base_date": base,
            "rankings": rankings[:limit], "rising": rising,
            "daiso": [dict(d) for d in daiso],
        }
    except Exception as e:
        logger.error(f"period rankings error: {e}")
        return {"period": period, "insufficient": True, "latest_date": None,
                "base_date": None, "rankings": [], "rising": [], "daiso": []}
    finally:
        conn.close()
