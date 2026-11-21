"""
DB helpers for the Operations Agent.

Matched to real schema:
  products  (id, tenant_id, name, category, unit_price)
  customers (id, tenant_id, name, email, segment, created_at)
  orders    (id, tenant_id, customer_id, order_date, total, status)
  order_items (id, order_id, product_id, quantity, unit_price, line_total)
"""
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from ..database import SessionFactory


# ---------------------------------------------------------------
# Reads
# ---------------------------------------------------------------

async def list_products(
    tenant_id: str,
    name_filter: str | None = None,
    category: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    q = (
        "SELECT id, name, category, unit_price "
        "FROM products WHERE tenant_id = :tid"
    )
    params: dict[str, Any] = {"tid": tenant_id}
    if name_filter:
        q += " AND name ILIKE :name"
        params["name"] = f"%{name_filter}%"
    if category:
        q += " AND category = :cat"
        params["cat"] = category
    q += " ORDER BY name LIMIT :lim"
    params["lim"] = limit

    async with SessionFactory() as session:
        async with session.begin():
            rows = (await session.execute(text(q), params)).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "category": r["category"],
            "unit_price": float(r["unit_price"]),
        }
        for r in rows
    ]


async def get_product_by_name(
    tenant_id: str,
    name: str,
) -> dict[str, Any] | None:
    async with SessionFactory() as session:
        async with session.begin():
            row = (await session.execute(
                text(
                    "SELECT id, name, category, unit_price "
                    "FROM products WHERE tenant_id = :tid AND name ILIKE :name "
                    "ORDER BY name LIMIT 1"
                ),
                {"tid": tenant_id, "name": f"%{name}%"},
            )).mappings().first()
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "category": row["category"],
        "unit_price": float(row["unit_price"]),
    }


async def get_customer_by_email(
    tenant_id: str,
    email: str,
) -> dict[str, Any] | None:
    async with SessionFactory() as session:
        async with session.begin():
            row = (await session.execute(
                text(
                    "SELECT id, name, email, segment "
                    "FROM customers WHERE tenant_id = :tid AND email = :email "
                    "LIMIT 1"
                ),
                {"tid": tenant_id, "email": email},
            )).mappings().first()
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "email": row["email"],
        "segment": row["segment"],
    }


async def list_orders(
    tenant_id: str,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    q = (
        "SELECT o.id, o.customer_id, c.name AS customer_name, "
        "       o.order_date, o.total, o.status "
        "FROM orders o JOIN customers c ON c.id = o.customer_id "
        "WHERE o.tenant_id = :tid"
    )
    params: dict[str, Any] = {"tid": tenant_id}
    if status:
        q += " AND o.status = :status"
        params["status"] = status
    q += " ORDER BY o.order_date DESC LIMIT :lim"
    params["lim"] = limit

    async with SessionFactory() as session:
        async with session.begin():
            rows = (await session.execute(text(q), params)).mappings().all()
    return [
        {
            "id": str(r["id"]),
            "customer_id": str(r["customer_id"]),
            "customer_name": r["customer_name"],
            "order_date": r["order_date"].isoformat(),
            "total": float(r["total"]),
            "status": r["status"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------
# Writes — called only from approve route (or direct-execute path)
# ---------------------------------------------------------------

async def insert_order(
    tenant_id: str,
    customer_id: str,
    items: list[dict[str, Any]],
    status: str = "confirmed",
) -> dict[str, Any]:
    """
    Insert one order + its order_items atomically.

    `items`: [{"product_id": str, "quantity": int, "unit_price": float}]
    Returns {order_id, total}.
    """
    order_id = uuid4()
    total = round(sum(i["quantity"] * i["unit_price"] for i in items), 2)

    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text(
                    "INSERT INTO orders "
                    "(id, tenant_id, customer_id, order_date, total, status) "
                    "VALUES (:id, :tid, :cid, NOW(), :total, :status)"
                ),
                {
                    "id": str(order_id),
                    "tid": tenant_id,
                    "cid": customer_id,
                    "total": total,
                    "status": status,
                },
            )
            for item in items:
                line_total = round(item["quantity"] * item["unit_price"], 2)
                await session.execute(
                    text(
                        "INSERT INTO order_items "
                        "(id, order_id, product_id, quantity, unit_price, line_total) "
                        "VALUES (:id, :oid, :pid, :qty, :price, :lt)"
                    ),
                    {
                        "id": str(uuid4()),
                        "oid": str(order_id),
                        "pid": item["product_id"],
                        "qty": item["quantity"],
                        "price": item["unit_price"],
                        "lt": line_total,
                    },
                )
    return {"order_id": str(order_id), "total": total}


async def update_customer_segment(
    tenant_id: str,
    customer_id: str,
    segment: str,
) -> bool:
    async with SessionFactory() as session:
        async with session.begin():
            r = await session.execute(
                text(
                    "UPDATE customers SET segment = :seg "
                    "WHERE tenant_id = :tid AND id = :cid"
                ),
                {"seg": segment, "tid": tenant_id, "cid": customer_id},
            )
    return r.rowcount > 0
