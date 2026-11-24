import asyncio, sys, json, httpx
from app.security import create_access_token
from app.database import SessionFactory
from sqlalchemy import text

async def main():
    async with SessionFactory() as db:
        user = (await db.execute(text(
            "SELECT id::text FROM users WHERE email = 'newnexora.systems+success@gmail.com'"
        ))).scalar_one()
    token = create_access_token(subject=user)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://127.0.0.1:8001/api/v1/orchestrator/run",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            json={"user_request": "Whats my tommor schedule"},
            timeout=30.0,
        )
    print("STATUS:", resp.status_code)
    if resp.status_code != 200:
        print("BODY:", resp.text[:500])
        return
    data = resp.json()
    print("TOP_KEYS:", list(data.keys()))
    print("TASKS:", [(t.get("agent_type"), t.get("task_id")) for t in (data.get("tasks") or [])])
    for r in (data.get("task_results") or []):
        res = r.get("result") or {}
        print("--- result ---")
        print("  agent:", r.get("agent_type"))
        print("  status:", r.get("status"))
        print("  action:", res.get("action"))
        print("  items_count:", len(res.get("items") or []))
        print("  events_count:", len(res.get("events") or []))
        print("  formatted:", (res.get("formatted") or "")[:200])

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
