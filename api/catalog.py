from fastapi import APIRouter, HTTPException, Query
from api.database import get_catalog_db

router = APIRouter(prefix="/api/catalog", tags=["Catalog"])


def _rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


@router.get("/summary")
def catalog_summary():
    conn = get_catalog_db()
    try:
        tables = _rows(
            conn,
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        )
        summary = {}
        for t in tables:
            summary[t["name"]] = conn.execute(
                f'SELECT COUNT(*) AS c FROM "{t["name"]}"'
            ).fetchone()["c"]

        return {
            "tables": summary,
            "latest_ranking_date": conn.execute(
                "SELECT MAX(ranking_date) AS d FROM daily_rankings"
            ).fetchone()["d"],
            "latest_snapshot_date": conn.execute(
                "SELECT MAX(snapshot_date) AS d FROM product_snapshots"
            ).fetchone()["d"],
        }
    finally:
        conn.close()


@router.get("/rankings/today")
def rankings_today(
    source: str = Query(None),
    limit: int = Query(500, ge=1, le=1000),
):
    conn = get_catalog_db()
    try:
        latest = conn.execute(
            "SELECT MAX(ranking_date) AS d FROM daily_rankings"
        ).fetchone()["d"]
        if not latest:
            return {"ranking_date": None, "count": 0, "items": []}

        sql = """
            SELECT r.ranking_date, r.source, r.ranking_type, r.category,
                   r.rank_num, r.product_id,
                   p.brand, p.product_name, p.product_url, p.status,
                   (SELECT s.price FROM product_snapshots s
                     WHERE s.product_id = r.product_id
                     ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS price,
                   (SELECT s.sale_price FROM product_snapshots s
                     WHERE s.product_id = r.product_id
                     ORDER BY s.snapshot_date DESC, s.id DESC LIMIT 1) AS sale_price
            FROM daily_rankings r
            LEFT JOIN products p ON p.product_id = r.product_id
            WHERE r.ranking_date = ?
        """
        params = [latest]
        if source:
            sql += " AND LOWER(r.source) = LOWER(?)"
            params.append(source)
        sql += " ORDER BY r.source, r.ranking_type, r.category, r.rank_num LIMIT ?"
        params.append(limit)

        items = _rows(conn, sql, params)
        return {"ranking_date": latest, "count": len(items), "items": items}
    finally:
        conn.close()


@router.get("/rankings/change")
def rankings_change(limit: int = Query(100, ge=1, le=500)):
    """ranking_changes 테이블이 비어있으므로, 오늘 vs 어제 직접 비교"""
    conn = get_catalog_db()
    try:
        latest = conn.execute(
            "SELECT MAX(ranking_date) AS d FROM daily_rankings"
        ).fetchone()["d"]
        if not latest:
            return {"current_date": None, "previous_date": None, "items": []}
        previous = conn.execute(
            "SELECT MAX(ranking_date) AS d FROM daily_rankings WHERE ranking_date < ?",
            (latest,),
        ).fetchone()["d"]

        rows = _rows(
            conn,
            """
            SELECT cur.source, cur.ranking_type, cur.category,
                   cur.rank_num AS current_rank,
                   prev.rank_num AS previous_rank,
                   cur.product_id,
                   p.brand, p.product_name, p.product_url
            FROM daily_rankings cur
            LEFT JOIN daily_rankings prev
              ON prev.product_id = cur.product_id
             AND prev.source = cur.source
             AND prev.ranking_type = cur.ranking_type
             AND prev.category = cur.category
             AND prev.ranking_date = ?
            LEFT JOIN products p ON p.product_id = cur.product_id
            WHERE cur.ranking_date = ?
            """,
            [previous, latest],
        )

        items = []
        for r in rows:
            it = dict(r)
            if r["previous_rank"] is not None:
                it["rank_change"] = r["previous_rank"] - r["current_rank"]
                it["direction"] = (
                    "up" if it["rank_change"] > 0
                    else "down" if it["rank_change"] < 0
                    else "same"
                )
            else:
                it["rank_change"] = None
                it["direction"] = "new"
            items.append(it)

        items.sort(
            key=lambda x: x["rank_change"] if x["rank_change"] is not None else -9999,
            reverse=True,
        )
        return {
            "current_date": latest,
            "previous_date": previous,
            "count": len(items),
            "items": items[:limit],
        }
    finally:
        conn.close()


@router.get("/products")
def list_products(
    q: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    conn = get_catalog_db()
    try:
        where, params = "", []
        if q:
            where = (" WHERE LOWER(product_name) LIKE LOWER(?) "
                     "OR LOWER(brand) LIKE LOWER(?)")
            params = [f"%{q}%", f"%{q}%"]

        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM products{where}", params
        ).fetchone()["c"]

        items = _rows(
            conn,
            f"""SELECT product_id, source, brand, product_name, product_url,
                       category, status, updated_at
                FROM products{where}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        return {"total": total, "items": items}
    finally:
        conn.close()


@router.get("/products/{product_id}")
def product_detail(product_id: str):
    conn = get_catalog_db()
    try:
        product = conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        if not product:
            raise HTTPException(404, "Product not found")

        snapshots = _rows(
            conn,
            """SELECT snapshot_date, price, sale_price, status
               FROM product_snapshots
               WHERE product_id = ?
               ORDER BY snapshot_date DESC, id DESC LIMIT 30""",
            (product_id,),
        )
        rankings = _rows(
            conn,
            """SELECT ranking_date, source, ranking_type, category, rank_num
               FROM daily_rankings
               WHERE product_id = ?
               ORDER BY ranking_date DESC LIMIT 30""",
            (product_id,),
        )
        return {
            "product": dict(product),
            "snapshots": snapshots,
            "rankings": rankings,
        }
    finally:
        conn.close()
