import asyncio, sys, uuid, random
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import SessionFactory

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"
random.seed(42)

async def main():
    async with SessionFactory() as db:
        existing = (await db.execute(text(
            "SELECT COUNT(*) FROM orders WHERE tenant_id = :t"
        ), {"t": TENANT})).scalar()
        if existing and existing > 0:
            print(f"SKIP: tenant already has {existing} orders")
            return

        product_rows = (await db.execute(text(
            "SELECT id::text, name, 100.0 + random()*2400 AS price FROM products LIMIT 8"
        ))).fetchall()
        if not product_rows:
            print("ABORT: no products in DB"); return
        print(f"Using {len(product_rows)} products")

        now = datetime.now(timezone.utc)
        inserted_orders = 0
        inserted_items = 0
        for day_offset in range(30):
            d = now - timedelta(days=day_offset)
            for _ in range(random.randint(0, 4)):
                cust = f"cust-{random.randint(1, 25):03d}"
                oid = str(uuid.uuid4())
                order_dt = d.replace(hour=random.randint(9,20), minute=random.randint(0,59), second=0, microsecond=0)
                chosen = random.sample(product_rows, k=random.randint(1, 3))
                total = 0.0
                for pid, pname, price in chosen:
                    qty = random.randint(1, 3)
                    line = round(float(price) * qty, 2)
                    total += line
                    await db.execute(text(
                        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total) "
                        "VALUES (gen_random_uuid(), :oid, :pid, :q, :up, :lt)"
                    ), {"oid": oid, "pid": pid, "q": qty, "up": float(price), "lt": line})
                    inserted_items += 1
                await db.execute(text(
                    "INSERT INTO orders (id, tenant_id, customer_id, total, order_date, status) "
                    "VALUES (:oid, :t, :cust, :total, :dt, 'confirmed')"
                ), {"oid": oid, "t": TENANT, "cust": cust, "total": total, "dt": order_dt})
                inserted_orders += 1
        await db.commit()
        print(f"INSERTED {inserted_orders} orders, {inserted_items} order_items")
        confirm = (await db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total),0) FROM orders WHERE tenant_id = :t"
        ), {"t": TENANT})).fetchone()
        print(f"CONFIRM: {confirm[0]} orders, total revenue ${confirm[1]}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
