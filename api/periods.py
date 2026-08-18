import logging
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

try:
    from api.database import get_catalog_db
except Exception:
    from database import get_catalog_db

router = APIRouter(prefix="/api/periods", tags=["Periods"])
logger = logging.getLogger(__name__)

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


def _cols(conn, table):
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _date_col(conn):
    cols = _cols(conn, "daily_rankings")
    for c in ("run_date", "ranking_date", "date", "captured_at"):
        if c in cols:
            return c
    return None


@router.get("/rankings")
def get_period_rankings(period: str = Query("daily"), limit: int = Query(30)):
    days = PERIOD_DAYS.get(period, 1)
    conn = get_catalog_db()
    try:
        dcol = _date_col(conn)
        if not dcol:
            return {"period": period, "insufficient": True, "latest_date": None,
                    "base_date": None, "rankings": [], "rising": [], "daiso": []}

        row = conn.execute(
            f"SELECT MAX({dcol}) AS d FROM daily_rankings WHERE source='oliveyoung'"
        ).fetchone()
        latest = row["d"] if row else None
        if not latest:
            return {"period": period, "insufficient": True, "latest_date": None,
                    "base_date": None, "rankings": [], "rising": [], "daiso": []}

        latest_d = datetime.strptime(latest[:10], "%Y-%m-%d")
        target = (latest_d - timedelta(days=days)).strftime("%Y-%m-%d")
        base_row = conn.execute(
            f"SELECT MAX({dcol}) AS d FROM daily_rankings "
            f"WHERE source='oliveyoung' AND {dcol} <= ?", (target,)
        ).fetchone()
        base = base_row["d"] if base_row and base_row["d"] else None

        insufficient = False
        if period != "daily":
            if base is None:
                insufficient = True
            else:
                days_diff = (latest_d - datetime.strptime(base[:10], "%Y-%m-%d")).days
                insufficient = days_diff < (days - 2)

        sel_cols = _cols(conn, "daily_rankings")
        rank_col = "rank_num" if "rank_num" in sel_cols else "rank"

        cur = conn.execute(
            f"""SELECT r.{rank_col} AS rank_num, r.product_id, p.brand, p.product_name, p.product_url,
                       p.price, p.sale_price
                FROM daily_rankings r LEFT JOIN products p ON p.product_id = r.product_id
                WHERE r.source='oliveyoung' AND r.{dcol}=?
                ORDER BY r.{rank_col} ASC LIMIT 100""", (latest,)
        ).fetchall()

        base_map = {}
        if base and not insufficient:
            for b in conn.execute(
                f"SELECT product_id, {rank_col} AS rank_num FROM daily_rankings "
                f"WHERE source='oliveyoung' AND {dcol}=?", (base,)
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

        pcols = _cols(conn, "products")
        daiso = []
        if "daiso_score" in pcols:
            daiso = [dict(d) for d in conn.execute(
                """SELECT product_id, brand, product_name, product_url, price, sale_price, daiso_score
                   FROM products
                   WHERE source='daiso' AND status='ACTIVE' AND daiso_score > 0
                   ORDER BY daiso_score DESC LIMIT 10"""
            ).fetchall()]

        return {
            "period": period, "insufficient": insufficient,
            "latest_date": latest, "base_date": base,
            "rankings": rankings[:limit], "rising": rising, "daiso": daiso,
        }
    except Exception as e:
        logger.error(f"period rankings error: {e}")
        return {"period": period, "insufficient": True, "latest_date": None,
                "base_date": None, "rankings": [], "rising": [], "daiso": []}
    finally:
        conn.close()


@router.get("/products")
def full_products():
    """전체 상품(14,000+) + 인기도 점수 + 가격 NULL 백필"""
    conn = get_catalog_db()
    try:
        cols = _cols(conn, "products")
        want = ["product_id", "source", "brand", "product_name", "product_url",
                "category", "parent_category", "price", "sale_price",
                "review_count", "rating", "daiso_score", "is_new", "status"]
        sel = [c for c in want if c in cols]
        rows = conn.execute(
            f"SELECT {','.join(sel)} FROM products WHERE status='ACTIVE'"
        ).fetchall()

        # 🚨 가격 NULL 백필: product_snapshots에서 최신 가격 가져오기
        snap_map = {}
        try:
            for r in conn.execute("""
                SELECT product_id, price, sale_price
                FROM product_snapshots
                WHERE price IS NOT NULL
                ORDER BY id DESC
            """).fetchall():
                if r["product_id"] not in snap_map:
                    snap_map[r["product_id"]] = (r["price"], r["sale_price"])
        except Exception:
            pass

        dcol = _date_col(conn)
        rank_map = {}
        if dcol:
            latest = conn.execute(
                f"SELECT MAX({dcol}) AS d FROM daily_rankings WHERE source='oliveyoung'"
            ).fetchone()["d"]
            if latest:
                rcol = "rank_num" if "rank_num" in _cols(conn, "daily_rankings") else "rank"
                for r in conn.execute(
                    f"SELECT product_id, {rcol} AS rank_num FROM daily_rankings "
                    f"WHERE source='oliveyoung' AND {dcol}=?", (latest,)
                ).fetchall():
                    rank_map[r["product_id"]] = r["rank_num"]

        items = []
        for r in rows:
            it = dict(r)
            # 🚨 price NULL이면 snapshot에서 복원
            if it.get("price") is None and it["product_id"] in snap_map:
                it["price"], it["sale_price"] = snap_map[it["product_id"]]

            rank = rank_map.get(it["product_id"])
            it["rank"] = rank
            pop = 0.0
            if rank:
                pop = 10000.0 - rank
            elif it.get("daiso_score"):
                pop = float(it["daiso_score"])
            elif it.get("review_count"):
                pop = math.log10(it["review_count"] + 1) * 10
            it["pop"] = pop
            items.append(it)

        return {"total": len(items), "items": items}
    except Exception as e:
        logger.error(f"full_products error: {e}")
        return {"total": 0, "items": []}
    finally:
        conn.close()
