import asyncio, sys, uuid, random
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.database import SessionFactory

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"
random.seed(42)
SEGMENTS = ["smb", "enterprise", "startup", "agency"]

async def main():
    async with SessionFactory() as db:
        existing = (await db.execute(text(
            "SELECT COUNT(*) FROM customers WHERE tenant_id = :t"
        ), {"t": TENANT})).scalar()
        print(f"EXISTING_CUSTOMERS: {existing}")

        customer_ids = []
        if existing and existing > 0:
            rows = (await db.execute(text(
                "SELECT id::text FROM customers WHERE tenant_id = :t"
            ), {"t": TENANT})).fetchall()
            customer_ids = [r[0] for r in rows]
            print(f"Using existing {len(customer_ids)} customers")
        else:
            print("Creating 20 customers...")
            now_ts = datetime.now(timezone.utc)
            for i in range(20):
                cid = str(uuid.uuid4())
                cname = f"Customer {i+1:02d}"
                cemail = f"customer{i+1:02d}@example.com"
                cseg = random.choice(SEGMENTS)
                try:
                    await db.execute(text(
                        "INSERT INTO customers (id, tenant_id, name, email, segment, created_at) "
                        "VALUES (:id, :t, :n, :e, :s, :ca)"
                    ), {"id": cid, "t": TENANT, "n": cname, "e": cemail, "s": cseg, "ca": now_ts})
                except Exception as e:
                    await db.rollback()
                    print(f"CUSTOMER INSERT FAILED: {type(e).__name__}: {e}")
                    return
                customer_ids.append(cid)
            await db.commit()
            print(f"CREATED {len(customer_ids)} customers")

        existing_orders = (await db.execute(text(
            "SELECT COUNT(*) FROM orders WHERE tenant_id = :t"
        ), {"t": TENANT})).scalar()
        if existing_orders and existing_orders > 0:
            print(f"SKIP orders: already {existing_orders}")
            return

        product_rows = (await db.execute(text(
            "SELECT id::text, 100.0 + random()*2400 AS price FROM products LIMIT 8"
        ))).fetchall()
        if not product_rows:
            print("ABORT: no products"); return
        print(f"Using {len(product_rows)} products")

        now = datetime.now(timezone.utc)
        orders_ins = 0; items_ins = 0
        for day_offset in range(30):
            d = now - timedelta(days=day_offset)
            for _ in range(random.randint(1, 4)):
                cust = random.choice(customer_ids)
                oid = str(uuid.uuid4())
                order_dt = d.replace(hour=random.randint(9,20), minute=random.randint(0,59), second=0, microsecond=0)
                chosen = random.sample(product_rows, k=random.randint(1,3))
                total = 0.0
                line_data = []
                for pid, price in chosen:
                    qty = random.randint(1,3)
                    line = round(float(price) * qty, 2)
                    total += line
                    line_data.append((pid, qty, float(price), line))

                await db.execute(text(
                    "INSERT INTO orders (id, tenant_id, customer_id, total, order_date, status) "
                    "VALUES (:oid, :t, :cust, :total, :dt, 'confirmed')"
                ), {"oid": oid, "t": TENANT, "cust": cust, "total": round(total,2), "dt": order_dt})
                await db.flush()
                orders_ins += 1

                for pid, qty, up, lt in line_data:
                    await db.execute(text(
                        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price, line_total) "
                        "VALUES (gen_random_uuid(), :oid, :pid, :q, :up, :lt)"
                    ), {"oid": oid, "pid": pid, "q": qty, "up": up, "lt": lt})
                    items_ins += 1

        await db.commit()
        print(f"INSERTED: {orders_ins} orders, {items_ins} order_items")
        confirm = (await db.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total),0) FROM orders WHERE tenant_id = :t"
        ), {"t": TENANT})).fetchone()
        print(f"CONFIRM: {confirm[0]} orders, total revenue ${confirm[1]}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
