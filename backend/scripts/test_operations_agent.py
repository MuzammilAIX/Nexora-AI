"""End-to-end test for OperationsAgent — read, prepare, execute, replay."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import SessionFactory
from app.agents.base import AgentInput
from app.agents.operations import OperationsAgent


TENANT = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"


async def main():
    agent = OperationsAgent()

    # --- 1. Query products (read) ---
    out = await agent.run(AgentInput(
        task_description="show me products",
        context={"tenant_id": TENANT, "user_request": "show me products"},
    ))
    count = len((out.result or {}).get("products", []))
    print(f"[1] query_products: success={out.success} count={count}")
    assert out.success, f"query_products failed: {out.error}"
    assert "products" in out.result

    # --- 2. Fetch one product + one customer to use in tests ---
    async with SessionFactory() as s:
        async with s.begin():
            prod = (await s.execute(
                text(
                    "SELECT id, name, unit_price FROM products "
                    "WHERE tenant_id = :t ORDER BY name LIMIT 1"
                ),
                {"t": TENANT},
            )).mappings().first()
            cust = (await s.execute(
                text(
                    "SELECT id, email FROM customers "
                    "WHERE tenant_id = :t ORDER BY email LIMIT 1"
                ),
                {"t": TENANT},
            )).mappings().first()
    if prod is None or cust is None:
        raise SystemExit("need at least one product and one customer in test tenant")
    print(f"[2] product={prod['name']} (${prod['unit_price']})  customer={cust['email']}")

    # --- 3. Prepare-phase reorder with large qty (should NOT write) ---
    big_qty = int(1000 / float(prod["unit_price"])) + 10  # total > $500
    prep = await agent.run(AgentInput(
        task_description=f"reorder {big_qty} {prod['name']} for {cust['email']}",
        context={
            "tenant_id": TENANT,
            "user_request": f"reorder {big_qty} {prod['name']} for {cust['email']}",
            "prepare_only": True,
        },
    ))
    print(f"[3] prepare reorder: success={prep.success}")
    assert prep.success, f"prepare failed: {prep.error}"
    proposed = (prep.result or {}).get("proposed_order") or {}
    print(f"    proposed total=${proposed.get('total')}  "
          f"requires_approval={prep.result.get('requires_approval')}")
    assert proposed.get("total", 0) > 500
    assert prep.result.get("action_kind") == "create_order"

    # Confirm no order was written
    async with SessionFactory() as s:
        async with s.begin():
            before = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()
    print(f"    orders before execute: {before}")

    # --- 4. Execute-phase with small qty (should write + idempotency) ---
    small_qty = 1
    exec_out = await agent.run(AgentInput(
        task_description=f"reorder {small_qty} {prod['name']} for {cust['email']}",
        context={
            "tenant_id": TENANT,
            "user_request": f"reorder {small_qty} {prod['name']} for {cust['email']}",
        },
    ))
    print(f"[4] execute reorder: success={exec_out.success}")
    assert exec_out.success, f"execute failed: {exec_out.error}"
    assert "order_id" in exec_out.result
    print(f"    order_id={exec_out.result['order_id']}  "
          f"total=${exec_out.result['total']}")

    async with SessionFactory() as s:
        async with s.begin():
            after = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()
    print(f"    orders after execute: {after}")
    assert after == before + 1, f"expected +1 order, got {before}->{after}"

    # --- 5. Replay: same reorder should hit idempotency, not write again ---
    replay = await agent.run(AgentInput(
        task_description=f"reorder {small_qty} {prod['name']} for {cust['email']}",
        context={
            "tenant_id": TENANT,
            "user_request": f"reorder {small_qty} {prod['name']} for {cust['email']}",
        },
    ))
    print(f"[5] replay reorder: success={replay.success}  "
          f"replayed={replay.result.get('replayed')}")
    assert replay.success
    assert replay.result.get("replayed") is True, "idempotency did not trigger"

    async with SessionFactory() as s:
        async with s.begin():
            final = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()
    print(f"    orders after replay: {final}  (should equal {after})")
    assert final == after

    # --- 6. Flag customer (idempotent write) ---
    flag = await agent.run(AgentInput(
        task_description=f"flag {cust['email']} as vip",
        context={
            "tenant_id": TENANT,
            "user_request": f"flag {cust['email']} as vip",
        },
    ))
    print(f"[6] flag_customer: success={flag.success}  "
          f"new_segment={(flag.result or {}).get('new_segment')}")
    assert flag.success, f"flag failed: {flag.error}"

    # --- 7. Verify audit trail ---
    async with SessionFactory() as s:
        async with s.begin():
            events = (await s.execute(
                text(
                    "SELECT event_type FROM audit_events "
                    "WHERE tenant_id = :t "
                    "AND event_type IN ('order.created','customer.flagged',"
                    "'operations.query_products') "
                    "ORDER BY created_at DESC LIMIT 10"
                ),
                {"t": TENANT},
            )).all()
    seen = [e[0] for e in events]
    print(f"[7] audit events: {seen}")
    assert "order.created" in seen
    assert "customer.flagged" in seen

    print("\nPASS: operations agent (read + prepare + execute + replay + flag + audit)")


asyncio.run(main())
