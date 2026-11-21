"""
Idempotent seed for the Analytics Agent demo data.

Creates:
  products, customers, orders, order_items

Populates:
  8 products, 20 customers, ~120 orders across Oct + Nov 2026

Design intent:
  November is deliberately ~20-25% DOWN vs October so the
  November report has a story to tell ("revenue declined...")
  and the Analytics Agent's MoM detection has something to find.

All rows carry tenant_id so the read-only query tool's
tenant filter has real data to exercise.
"""
import asyncio
import sys
import random
from datetime import datetime, timezone
from uuid import uuid4

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import SessionFactory

# --------------------------------------------------
# Tenant — must match the tenant used in tests
# --------------------------------------------------
TENANT_ID = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"

# --------------------------------------------------
# Reference data
# --------------------------------------------------
PRODUCTS = [
    {"name": "Widget Basic",    "category": "hardware",  "unit_price": 49.00},
    {"name": "Widget Pro",      "category": "hardware",  "unit_price": 129.00},
    {"name": "Widget Enterprise","category": "hardware", "unit_price": 399.00},
    {"name": "Cloud Starter",   "category": "software",  "unit_price": 29.00},
    {"name": "Cloud Pro",       "category": "software",  "unit_price": 99.00},
    {"name": "Cloud Enterprise","category": "software",  "unit_price": 499.00},
    {"name": "Support Standard","category": "services",  "unit_price": 199.00},
    {"name": "Support Premium", "category": "services",  "unit_price": 899.00},
]

CUSTOMERS = [
    ("Acme Corp",           "ops@acmecorp.com",           "mid-market"),
    ("Beta Industries",     "buyer@beta.com",             "mid-market"),
    ("Gamma LLC",           "hi@gamma.com",               "smb"),
    ("Delta Systems",       "team@delta.io",              "enterprise"),
    ("Epsilon Labs",        "contact@epsilon.dev",        "smb"),
    ("Zeta Holdings",       "info@zeta.co",               "enterprise"),
    ("Eta Consulting",      "hello@eta.io",               "smb"),
    ("Theta Group",         "sales@theta.com",            "mid-market"),
    ("Iota Studios",        "hi@iota.fm",                 "smb"),
    ("Kappa Services",      "team@kappa.co",              "mid-market"),
    ("Lambda Retail",       "info@lambda.shop",           "smb"),
    ("Mu Manufacturing",    "buyer@mu.mfg",               "enterprise"),
    ("Nu Logistics",        "ops@nu.logistics",           "mid-market"),
    ("Xi Media",            "contact@xi.media",           "smb"),
    ("Omicron Financial",   "team@omicron.fin",           "enterprise"),
    ("Pi Analytics",        "hi@pi.ai",                   "smb"),
    ("Rho Ventures",        "info@rho.vc",                "enterprise"),
    ("Sigma Devices",       "buyer@sigma.io",             "mid-market"),
    ("Tau Software",        "team@tau.dev",               "smb"),
    ("Upsilon Cloud",       "contact@upsilon.cloud",      "mid-market"),
]

# Weights drive volume by segment
SEGMENT_WEIGHTS = {"smb": 1, "mid-market": 3, "enterprise": 6}

# --------------------------------------------------
# DDL
# --------------------------------------------------
DDL = """
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    segment TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE products (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id),
    order_date TIMESTAMP WITH TIME ZONE NOT NULL,
    total NUMERIC(12, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'paid'
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL
);

CREATE INDEX idx_orders_tenant_date ON orders(tenant_id, order_date);
CREATE INDEX idx_order_items_order ON order_items(order_id);
"""


def month_range(month_start: datetime, days: int) -> list[datetime]:
    """Return `days` datetimes spread across a month."""
    return [
        month_start.replace(day=random.randint(1, 28))
        .replace(hour=random.randint(8, 20))
        .replace(minute=random.randint(0, 59))
        for _ in range(days)
    ]


async def main() -> None:
    random.seed(42)  # reproducible seed

    async with SessionFactory() as session:
        async with session.begin():
            # 1. DDL
            for stmt in DDL.strip().split(";"):
                if stmt.strip():
                    await session.execute(text(stmt))
            print("+ created tables: customers, products, orders, order_items")

            # 2. Products
            product_ids = []
            for p in PRODUCTS:
                pid = uuid4()
                product_ids.append((pid, p))
                await session.execute(
                    text(
                        "INSERT INTO products (id, tenant_id, name, category, unit_price) "
                        "VALUES (:id, :tid, :name, :cat, :price)"
                    ),
                    {"id": str(pid), "tid": TENANT_ID, "name": p["name"],
                     "cat": p["category"], "price": p["unit_price"]},
                )
            print(f"+ inserted {len(product_ids)} products")

            # 3. Customers
            customer_ids = []
            for name, email, segment in CUSTOMERS:
                cid = uuid4()
                customer_ids.append((cid, segment))
                await session.execute(
                    text(
                        "INSERT INTO customers (id, tenant_id, name, email, segment, created_at) "
                        "VALUES (:id, :tid, :name, :email, :seg, :created)"
                    ),
                    {"id": str(cid), "tid": TENANT_ID, "name": name,
                     "email": email, "seg": segment,
                     "created": datetime(2026, 1, 1, tzinfo=timezone.utc)},
                )
            print(f"+ inserted {len(customer_ids)} customers")

            # 4. Orders — Oct heavier than Nov (deliberate MoM decline)
            oct_dates = month_range(datetime(2026, 10, 1, tzinfo=timezone.utc), 70)
            nov_dates = month_range(datetime(2026, 11, 1, tzinfo=timezone.utc), 50)
            order_specs = [(d, "oct") for d in oct_dates] + [(d, "nov") for d in nov_dates]

            total_orders = 0
            total_items = 0
            oct_total = 0.0
            nov_total = 0.0

            for order_date, month_label in order_specs:
                cid, segment = random.choice(customer_ids)
                weight = SEGMENT_WEIGHTS[segment]

                # 1-4 line items per order, weighted by segment
                n_items = random.randint(1, weight)
                chosen_products = random.sample(product_ids, k=min(n_items, len(product_ids)))

                line_totals = []
                items_for_order = []
                for pid, p in chosen_products:
                    qty = random.randint(1, 3)
                    line_total = round(p["unit_price"] * qty, 2)
                    line_totals.append(line_total)
                    items_for_order.append((pid, qty, p["unit_price"], line_total))

                order_total = round(sum(line_totals), 2)

                oid = uuid4()
                await session.execute(
                    text(
                        "INSERT INTO orders (id, tenant_id, customer_id, order_date, total, status) "
                        "VALUES (:id, :tid, :cid, :dt, :total, 'paid')"
                    ),
                    {"id": str(oid), "tid": TENANT_ID, "cid": str(cid),
                     "dt": order_date, "total": order_total},
                )
                total_orders += 1

                if month_label == "oct":
                    oct_total += order_total
                else:
                    nov_total += order_total

                for pid, qty, unit_price, line_total in items_for_order:
                    await session.execute(
                        text(
                            "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total) "
                            "VALUES (:id, :oid, :pid, :qty, :up, :lt)"
                        ),
                        {"id": str(uuid4()), "oid": str(oid), "pid": str(pid),
                         "qty": qty, "up": unit_price, "lt": line_total},
                    )
                    total_items += 1

    print(f"+ inserted {total_orders} orders ({len(oct_dates)} Oct, {len(nov_dates)} Nov)")
    print(f"+ inserted {total_items} order_items")
    print()
    print("=== Verification ===")
    print(f"October total   : ${oct_total:,.2f}")
    print(f"November total  : ${nov_total:,.2f}")
    pct = (nov_total - oct_total) / oct_total * 100 if oct_total else 0
    print(f"MoM change      : {pct:+.1f}%")
    print()
    print(f"Tenant ID       : {TENANT_ID}")
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
