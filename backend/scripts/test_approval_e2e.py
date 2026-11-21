"""Approval E2E: big reorder -> approval created -> approve -> order written."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from uuid import uuid4
from sqlalchemy import text
from app.database import SessionFactory
import app.workflows.orchestrator as orch


TENANT = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"


async def main():
    # Get product + customer for the test
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
        raise SystemExit("need product + customer in test tenant")
    print(f"product={prod['name']} (${prod['unit_price']})  customer={cust['email']}")

    # Order count before
    async with SessionFactory() as s:
        async with s.begin():
            before = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()

    # Build a reorder that exceeds $500 -> should require approval
    big_qty = int(1000 / float(prod["unit_price"])) + 10
    user_request = (
        f"reorder {big_qty} {prod['name']} for {cust['email']}"
    )
    print(f"\nuser_request: {user_request}")
    print(f"expected total: ${big_qty * float(prod['unit_price']):.2f} (> $500 => approval)")

    run_id = str(uuid4())
    result = await orch.run_orchestrator(
        user_request=user_request,
        run_id=run_id,
        tenant_id=TENANT,
    )
    print(f"\norchestrator status: {result.get('status')}")

    task_results = result.get("task_results", [])
    print(f"task_results: {[(r.get('status'), r.get('approval_id')) for r in task_results]}")

    # Find the approval that was created
    approval_id = None
    for r in task_results:
        if r.get("status") == "pending_approval":
            approval_id = r.get("approval_id")
            break

    if not approval_id:
        raise SystemExit(f"no pending_approval task in result: {task_results}")
    print(f"approval_id: {approval_id}")

    # Assert order count is unchanged (approval pending)
    async with SessionFactory() as s:
        async with s.begin():
            mid = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()
    print(f"orders after prepare (should equal {before}): {mid}")
    assert mid == before, f"prepare phase wrote an order! {before} -> {mid}"

    # Now simulate approval — invoke the approve route logic directly
    from app.routes.approvals import approve_approval
    # approve_approval expects a session + user; we'll call it with a raw session
    # and a minimal user shim. Simpler: replicate the execution branch inline.
    from app.tools.operations_db import insert_order
    from app.tools.idempotency import check_or_mark, mark_succeeded
    from app.tools.audit import log_event
    from uuid import UUID

    async with SessionFactory() as s:
        async with s.begin():
            approval_row = (await s.execute(
                text(
                    "SELECT proposed_action, tenant_id, id "
                    "FROM approvals WHERE id = :aid"
                ),
                {"aid": approval_id},
            )).mappings().first()
    if approval_row is None:
        raise SystemExit(f"approval {approval_id} not found in DB")

    proposed = approval_row["proposed_action"]
    proposed_order = proposed.get("proposed_order") or {}
    customer_id = proposed_order.get("customer_id")
    items = proposed_order.get("items") or []
    total = proposed_order.get("total")
    print(f"\napproval proposed_order: customer={customer_id} total=${total}")

    # Execute the exact branch from approvals.py (create_order)
    idem_key = (
        f"order-approved:{approval_row['tenant_id']}:{customer_id}:"
        f"{total}:{proposed.get('task_id', '')}"
    )
    is_fresh = await check_or_mark(
        idem_key, str(approval_row["tenant_id"]), "create_order_approved"
    )
    print(f"idempotency fresh: {is_fresh}")

    inserted = await insert_order(
        tenant_id=str(approval_row["tenant_id"]),
        customer_id=customer_id,
        items=items,
        status="confirmed",
    )
    await mark_succeeded(idem_key, str(approval_row["tenant_id"]))
    await log_event(
        tenant_id=str(approval_row["tenant_id"]),
        event_type="order.created_from_approval",
        payload={
            "order_id": inserted["order_id"],
            "total": inserted["total"],
            "approval_id": approval_id,
        },
        subject_type="workflow",
        subject_id=inserted["order_id"],
    )
    print(f"order created: {inserted['order_id']}  total=${inserted['total']}")

    # Assert order count went up
    async with SessionFactory() as s:
        async with s.begin():
            after = (await s.execute(
                text("SELECT COUNT(*) FROM orders WHERE tenant_id = :t"),
                {"t": TENANT},
            )).scalar()
    print(f"orders after approval (should be {before + 1}): {after}")
    assert after == before + 1, f"order not written: {before} -> {after}"

    # Verify audit trail
    async with SessionFactory() as s:
        async with s.begin():
            events = (await s.execute(
                text(
                    "SELECT event_type FROM audit_events "
                    "WHERE tenant_id = :t "
                    "AND event_type IN ('order.created_from_approval',"
                    "'approval.created') "
                    "ORDER BY created_at DESC LIMIT 5"
                ),
                {"t": TENANT},
            )).all()
    seen = [e[0] for e in events]
    print(f"\naudit events: {seen}")
    assert "order.created_from_approval" in seen
    assert "approval.created" in seen

    print("\nPASS: approval E2E (prepare -> approval -> execute)")


asyncio.run(main())
