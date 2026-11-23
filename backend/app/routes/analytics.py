"""Analytics API — real aggregation queries for the Analytics & Reports page.

Endpoints:
  GET /analytics/business    — revenue, orders, top products, customers
  GET /analytics/ai          — runs, agents, success rates, pending approvals
  GET /analytics/workflows   — daily runs, status, avg duration, retries
  GET /analytics/operational — time saved, intervention rate, approval rate
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, text, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth_deps import get_current_user
from ..database import get_session
from ..database.auth_models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/business")
async def business_analytics(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Revenue, orders, top products, customer metrics."""
    tenant = user.tenant_id

    # Revenue + order metrics (current month + previous month)
    revenue_sql = text("""
        SELECT
          COALESCE(SUM(CASE WHEN date_trunc('month', order_date) = date_trunc('month', CURRENT_DATE)
            THEN total ELSE 0 END), 0) AS current_month_revenue,
          COALESCE(SUM(CASE WHEN date_trunc('month', order_date) = date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
            THEN total ELSE 0 END), 0) AS prev_month_revenue,
          COUNT(CASE WHEN date_trunc('month', order_date) = date_trunc('month', CURRENT_DATE)
            THEN 1 END) AS current_month_orders,
          COUNT(CASE WHEN date_trunc('month', order_date) = date_trunc('month', CURRENT_DATE - INTERVAL '1 month')
            THEN 1 END) AS prev_month_orders,
          COALESCE(AVG(CASE WHEN date_trunc('month', order_date) = date_trunc('month', CURRENT_DATE)
            THEN total END), 0) AS current_avg_order_value,
          COUNT(DISTINCT customer_id) AS total_customers
        FROM orders
        WHERE tenant_id = :t
    """)
    r = (await session.execute(revenue_sql, {"t": tenant})).mappings().first()

    current_rev = float(r["current_month_revenue"] or 0)
    prev_rev = float(r["prev_month_revenue"] or 0)
    rev_change = ((current_rev - prev_rev) / prev_rev * 100) if prev_rev > 0 else 0

    # Revenue trend — last 30 days daily
    trend_sql = text("""
        SELECT date_trunc('day', order_date)::date AS day, SUM(total) AS revenue, COUNT(*) AS orders
        FROM orders
        WHERE tenant_id = :t AND order_date >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY day ORDER BY day
    """)
    trend_rows = (await session.execute(trend_sql, {"t": tenant})).mappings().all()
    revenue_trend = [
        {"date": row["day"].isoformat(), "revenue": float(row["revenue"] or 0), "orders": int(row["orders"])}
        for row in trend_rows
    ]

    # Top 5 products by revenue (last 90 days)
    top_sql = text("""
        SELECT p.name AS product_name, p.category,
               SUM(oi.line_total) AS revenue, SUM(oi.quantity) AS units
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        JOIN products p ON p.id = oi.product_id
        WHERE o.tenant_id = :t AND o.order_date >= CURRENT_DATE - INTERVAL '90 days'
        GROUP BY p.name, p.category
        ORDER BY revenue DESC LIMIT 5
    """)
    top_rows = (await session.execute(top_sql, {"t": tenant})).mappings().all()
    top_products = [
        {"name": row["product_name"], "category": row["category"],
         "revenue": float(row["revenue"] or 0), "units": int(row["units"] or 0)}
        for row in top_rows
    ]

    return {
        "current_month_revenue": current_rev,
        "prev_month_revenue": prev_rev,
        "revenue_change_pct": round(rev_change, 2),
        "current_month_orders": int(r["current_month_orders"] or 0),
        "prev_month_orders": int(r["prev_month_orders"] or 0),
        "avg_order_value": round(float(r["current_avg_order_value"] or 0), 2),
        "total_customers": int(r["total_customers"] or 0),
        "revenue_trend": revenue_trend,
        "top_products": top_products,
    }


@router.get("/ai")
async def ai_analytics(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Agent activity, runs, success rates."""
    tenant = user.tenant_id

    # Runs summary
    runs_sql = text("""
        SELECT
          COUNT(*) AS total_runs,
          COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed,
          COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed,
          COUNT(CASE WHEN status = 'pending_approval' THEN 1 END) AS pending,
          COALESCE(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))), 0) AS avg_duration_s
        FROM runs WHERE tenant_id = :t
    """)
    r = (await session.execute(runs_sql, {"t": tenant})).mappings().first()

    total = int(r["total_runs"] or 0)
    completed = int(r["completed"] or 0)
    success_rate = round((completed / total * 100), 1) if total > 0 else 0

    # Agent usage — safe parse: only try jsonb cast on rows where state_json
    # is a valid JSON object. Filter with a regex first, then cast.
    agent_sql = text("""
        SELECT
          (elem ->> 'agent_type')::text AS agent_type,
          COUNT(*)::int AS task_count
        FROM runs,
             jsonb_array_elements(
               CASE
                 WHEN state_json ~ '^\s*\{'
                 THEN state_json::jsonb -> 'tasks'
                 ELSE '[]'::jsonb
               END
             ) AS elem
        WHERE tenant_id = :t AND state_json IS NOT NULL
        GROUP BY agent_type
        ORDER BY task_count DESC LIMIT 10
    """)
    try:
        agent_rows = (await session.execute(agent_sql, {"t": tenant})).mappings().all()
        agent_usage = [{"agent": row["agent_type"] or "unknown", "tasks": int(row["task_count"])} for row in agent_rows]
    except Exception as e:
        print(f"[analytics] agent_usage query failed: {e}")
        agent_usage = []

    # Approvals summary
    appr_sql = text("""
        SELECT
          COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending,
          COUNT(CASE WHEN status IN ('approved', 'executed') THEN 1 END) AS approved,
          COUNT(CASE WHEN status = 'rejected' THEN 1 END) AS rejected
        FROM approvals WHERE tenant_id = :t
    """)
    a = (await session.execute(appr_sql, {"t": tenant})).mappings().first()

    return {
        "total_runs": total,
        "completed": completed,
        "failed": int(r["failed"] or 0),
        "pending_approval": int(r["pending"] or 0),
        "success_rate": success_rate,
        "avg_duration_s": round(float(r["avg_duration_s"] or 0), 1),
        "agent_usage": agent_usage,
        "pending_approvals": int(a["pending"] or 0),
        "approved_approvals": int(a["approved"] or 0),
        "rejected_approvals": int(a["rejected"] or 0),
    }

@router.get("/workflows")
async def workflow_analytics(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Daily run counts, status distribution, avg duration by agent."""
    tenant = user.tenant_id

    # Daily runs — last 14 days
    daily_sql = text("""
        SELECT date_trunc('day', created_at)::date AS day,
               COUNT(*) AS total,
               COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed,
               COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed,
               COUNT(CASE WHEN status = 'pending_approval' THEN 1 END) AS pending
        FROM runs
        WHERE tenant_id = :t AND created_at >= CURRENT_DATE - INTERVAL '14 days'
        GROUP BY day ORDER BY day
    """)
    daily_rows = (await session.execute(daily_sql, {"t": tenant})).mappings().all()
    daily_runs = [
        {"date": row["day"].isoformat(), "total": int(row["total"]),
         "completed": int(row["completed"]), "failed": int(row["failed"]), "pending": int(row["pending"])}
        for row in daily_rows
    ]

    # Retry analysis
    retry_sql = text("""
        SELECT
          COUNT(*) FILTER (WHERE retry_count > 0) AS runs_with_retries,
          MAX(retry_count) AS max_retries,
          SUM(retry_count) AS total_retries
        FROM runs WHERE tenant_id = :t
    """)
    rt = (await session.execute(retry_sql, {"t": tenant})).mappings().first()

    # Hourly pattern — what time of day do runs happen most
    hourly_sql = text("""
        SELECT EXTRACT(HOUR FROM created_at)::int AS hour, COUNT(*) AS cnt
        FROM runs WHERE tenant_id = :t
        GROUP BY hour ORDER BY hour
    """)
    hourly_rows = (await session.execute(hourly_sql, {"t": tenant})).mappings().all()
    hourly_pattern = [{"hour": int(row["hour"]), "count": int(row["cnt"])} for row in hourly_rows]

    return {
        "daily_runs": daily_runs,
        "runs_with_retries": int(rt["runs_with_retries"] or 0),
        "max_retries": int(rt["max_retries"] or 0),
        "total_retries": int(rt["total_retries"] or 0),
        "hourly_pattern": hourly_pattern,
    }


@router.get("/operational")
async def operational_analytics(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Time saved, intervention rate, approval rate, recent events."""
    tenant = user.tenant_id

    # Approval rate
    appr_sql = text("""
        SELECT
          COUNT(*) FILTER (WHERE status IN ('approved', 'executed')) AS approved,
          COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
          COUNT(*) FILTER (WHERE status = 'pending') AS pending,
          COUNT(*) AS total
        FROM approvals WHERE tenant_id = :t
    """)
    a = (await session.execute(appr_sql, {"t": tenant})).mappings().first()
    total_appr = int(a["total"] or 0)
    approved_count = int(a["approved"] or 0)
    approval_rate = round((approved_count / total_appr * 100), 1) if total_appr > 0 else 0

    # Runs count for time saved heuristic
    runs_sql = text("SELECT COUNT(*) FROM runs WHERE tenant_id = :t AND status = 'completed'")
    completed_runs = (await session.execute(runs_sql, {"t": tenant})).scalar() or 0

    # Recent audit events (last 10)
    events_sql = text("""
        SELECT event_type, subject_type, subject_id, created_at
        FROM audit_events
        WHERE tenant_id = :t
        ORDER BY created_at DESC LIMIT 10
    """)
    events_rows = (await session.execute(events_sql, {"t": tenant})).mappings().all()
    recent_events = [
        {
            "event_type": row["event_type"],
            "subject_type": row["subject_type"],
            "subject_id": str(row["subject_id"]) if row["subject_id"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in events_rows
    ]

    # Documents stats
    docs_sql = text("SELECT COUNT(*), COALESCE(SUM(size_bytes), 0) FROM documents WHERE tenant_id = :t")
    d = (await session.execute(docs_sql, {"t": tenant})).first()

    return {
        "approval_rate": approval_rate,
        "total_approvals": total_appr,
        "approved": approved_count,
        "rejected": int(a["rejected"] or 0),
        "pending_approvals": int(a["pending"] or 0),
        "completed_runs": int(completed_runs),
        "time_saved_minutes": int(completed_runs) * 5,  # 5 min per completed workflow heuristic
        "human_intervention_rate": round((total_appr / max(int(completed_runs), 1) * 100), 1),
        "recent_events": recent_events,
        "documents_count": int(d[0] or 0),
        "documents_total_bytes": int(d[1] or 0),
    }