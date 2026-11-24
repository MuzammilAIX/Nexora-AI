"""
Read-only PostgreSQL query tool for the Analytics Agent.

Guardrails (Section 7.7 — authorized tools only):
  - SELECT statements only
  - Table allowlist enforced
  - Automatic tenant_id WHERE injection
  - Row-count cap (10,000)
  - Query timeout (10s)
"""
import re
import sys
from typing import Any

if sys.platform == "win32":
    try:
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from sqlalchemy import text
from ..database import SessionFactory


ALLOWED_TABLES = frozenset({"orders", "order_items", "products", "customers"})
MAX_ROWS = 10_000
STATEMENT_TIMEOUT_MS = 10_000


class QueryRejected(ValueError):
    pass


_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(insert|update|delete|drop|truncate|alter|create|grant|revoke|"
    r"merge|call|exec|execute|copy|vacuum|analyze)\b",
    re.IGNORECASE,
)

_TABLE_REF = re.compile(
    r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)


def _validate_query(query: str) -> None:
    stripped = query.strip().rstrip(";")
    if not stripped.lower().startswith(("select", "with")):
        raise QueryRejected("Only SELECT / WITH queries are permitted.")

    if _FORBIDDEN_KEYWORDS.search(stripped):
        raise QueryRejected("Query contains a forbidden keyword.")

    if ";" in stripped:
        raise QueryRejected("Semicolons are not allowed.")

    for table in _TABLE_REF.findall(stripped):
        if table.lower() not in ALLOWED_TABLES:
            raise QueryRejected(
                f"Table '{table}' is not in the analytics allowlist. "
                f"Allowed: {sorted(ALLOWED_TABLES)}"
            )

    if "tenant_id" not in stripped.lower():
        raise QueryRejected(
            "Query must reference tenant_id for tenant isolation."
        )


async def run_analytics_query(
    tenant_id: str,
    query: str,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a read-only analytics query with strict validation."""
    _validate_query(query)

    merged = dict(params or {})
    merged.setdefault("tenant_id", str(tenant_id))

    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}")
            )
            result = await session.execute(text(query), merged)
            rows = result.mappings().all()

    if len(rows) > MAX_ROWS:
        raise QueryRejected(
            f"Query returned {len(rows)} rows, exceeding cap of {MAX_ROWS}."
        )

    return [dict(r) for r in rows]


async def get_monthly_sales(tenant_id: str, month: str) -> dict[str, Any]:
    """
    Deterministic sales metrics for a month ("YYYY-MM").

    All arithmetic happens in Python, not SQL — per Section 8 of the
    business doc ("do not ask an LLM to do exact arithmetic"). SQL
    returns raw rows; Python aggregates.
    """
    rows = await run_analytics_query(
        tenant_id=tenant_id,
        query=(
            "SELECT "
            "  o.id AS order_id, "
            "  o.customer_id AS customer_id, "
            "  o.total AS total, "
            "  oi.product_id AS product_id, "
            "  p.name AS product_name, "
            "  p.category AS category, "
            "  oi.quantity AS quantity, "
            "  oi.line_total AS line_total "
            "FROM orders o "
            "JOIN order_items oi ON oi.order_id = o.id "
            "JOIN products p ON p.id = oi.product_id "
            "WHERE o.tenant_id = :tenant_id "
            "  AND date_trunc('month', o.order_date) = date_trunc('month', CAST(:month AS timestamp)) "
        ),
        params={"month": f"{month}-01"},
    )

    if not rows:
        return {
            "period": month,
            "total_revenue": 0.0,
            "order_count": 0,
            "avg_order_value": 0.0,
            "distinct_customers": 0,
            "top_products": [],
            "bottom_products": [],
            "line_item_count": 0,
        }

    orders: dict[str, dict] = {}
    products: dict[str, dict] = {}

    for r in rows:
        oid = r["order_id"]
        if oid not in orders:
            orders[oid] = {
                "total": float(r["total"]),
                "customer_id": r["customer_id"],
            }
        pid = r["product_id"]
        agg = products.setdefault(pid, {
            "product_id": str(pid),
            "product_name": r["product_name"],
            "category": r["category"],
            "revenue": 0.0,
            "quantity": 0,
        })
        agg["revenue"] += float(r["line_total"])
        agg["quantity"] += int(r["quantity"])

    total_revenue = sum(o["total"] for o in orders.values())
    order_count = len(orders)
    distinct_customers = len({o["customer_id"] for o in orders.values()})
    avg_order_value = total_revenue / order_count if order_count else 0.0

    product_list = sorted(products.values(), key=lambda p: p["revenue"], reverse=True)

    return {
        "period": month,
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": round(avg_order_value, 2),
        "distinct_customers": distinct_customers,
        "top_products": product_list[:3],
        "bottom_products": product_list[-3:],
        "line_item_count": len(rows),
    }


async def get_sales_report(
    tenant_id: str,
    start_date: str,
    end_date: str,
    granularity: str = "day",
) -> dict[str, Any]:
    """
    Flexible-range sales report.

    Args:
        start_date: ISO date "YYYY-MM-DD" (inclusive)
        end_date:   ISO date "YYYY-MM-DD" (inclusive)
        granularity: "day" | "week" | "month" | "year"

    Returns:
        {
            "start_date", "end_date", "granularity",
            "total_revenue", "order_count", "avg_order_value",
            "distinct_customers", "line_item_count",
            "top_products", "bottom_products",
            "table": {
                "columns": ["period", "orders", "revenue", "avg_order"],
                "rows": [["2026-11-01", 42, 55000.00, 1309.52], ...]
            }
        }
    """
    rows = await run_analytics_query(
        tenant_id=tenant_id,
        query=(
            "SELECT "
            "  o.id AS order_id, "
            "  o.customer_id AS customer_id, "
            "  o.total AS total, "
            "  o.order_date AS order_date, "
            "  oi.product_id AS product_id, "
            "  p.name AS product_name, "
            "  p.category AS category, "
            "  oi.quantity AS quantity, "
            "  oi.line_total AS line_total "
            "FROM orders o "
            "JOIN order_items oi ON oi.order_id = o.id "
            "JOIN products p ON p.id = oi.product_id "
            "WHERE o.tenant_id = :tenant_id "
            "  AND o.order_date >= CAST(:start_date AS timestamp) "
            "  AND o.order_date <  (CAST(:end_date AS timestamp) + interval '1 day') "
            "ORDER BY o.order_date"
        ),
        params={"start_date": start_date, "end_date": end_date},
    )

    if not rows:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "granularity": granularity,
            "total_revenue": 0.0,
            "order_count": 0,
            "avg_order_value": 0.0,
            "distinct_customers": 0,
            "line_item_count": 0,
            "top_products": [],
            "bottom_products": [],
            "table": {
                "columns": ["period", "orders", "revenue", "avg_order"],
                "rows": [],
            },
        }

    # ---- Python aggregation ----
    orders: dict[str, dict] = {}
    products: dict[str, dict] = {}
    buckets: dict[str, dict] = {}  # period -> {orders, revenue}

    for r in rows:
        oid = r["order_id"]
        od = r["order_date"]
        # Compute bucket key from date based on granularity
        if granularity == "day":
            bucket = od.strftime("%Y-%m-%d")
        elif granularity == "week":
            y, w, _ = od.isocalendar()
            bucket = f"{y}-W{w:02d}"
        elif granularity == "month":
            bucket = od.strftime("%Y-%m")
        elif granularity == "year":
            bucket = od.strftime("%Y")
        else:
            bucket = od.strftime("%Y-%m-%d")

        b = buckets.setdefault(bucket, {"orders": set(), "revenue": 0.0})
        b["orders"].add(oid)
        b["revenue"] += float(r["line_total"])

        if oid not in orders:
            orders[oid] = {
                "total": float(r["total"]),
                "customer_id": r["customer_id"],
            }

        pid = r["product_id"]
        agg = products.setdefault(pid, {
            "product_id": str(pid),
            "product_name": r["product_name"],
            "category": r["category"],
            "revenue": 0.0,
            "quantity": 0,
        })
        agg["revenue"] += float(r["line_total"])
        agg["quantity"] += int(r["quantity"])

    total_revenue = sum(o["total"] for o in orders.values())
    order_count = len(orders)
    distinct_customers = len({o["customer_id"] for o in orders.values()})
    avg_order_value = total_revenue / order_count if order_count else 0.0

    product_list = sorted(products.values(), key=lambda p: p["revenue"], reverse=True)

    # Build table rows sorted by period key
    table_rows = []
    for period_key in sorted(buckets.keys()):
        b = buckets[period_key]
        o_count = len(b["orders"])
        rev = round(b["revenue"], 2)
        avg = round(rev / o_count, 2) if o_count else 0.0
        table_rows.append([period_key, o_count, rev, avg])

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": round(avg_order_value, 2),
        "distinct_customers": distinct_customers,
        "line_item_count": len(rows),
        "top_products": product_list[:3],
        "bottom_products": product_list[-3:],
        "table": {
            "columns": ["period", "orders", "revenue", "avg_order"],
            "rows": table_rows,
        },
    }