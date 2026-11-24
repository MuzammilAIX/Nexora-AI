import asyncio, sys
from app.workflows.orchestrator import run_orchestrator
async def main():
    b = await run_orchestrator(
        user_request="Show me the last 30 days sales report as a table",
        tenant_id="e587e037-a729-4f91-9b09-08600cb62f91",
        run_id="seed-verify-001"
    )
    for r in (b.get("task_results") or []):
        if r.get("agent_type") == "analytics":
            res = r.get("result") or {}
            m = res.get("metrics") or {}
            print("ROW_DATA_COUNT:", res.get("row_data_count"))
            print("TOTAL_REVENUE:", m.get("total_revenue"))
            print("ORDER_COUNT:", m.get("order_count"))
            print("DISTINCT_CUSTOMERS:", m.get("distinct_customers"))
            tbl = res.get("table") or {}
            print("TABLE_ROWS:", len(tbl.get("rows") or []))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
