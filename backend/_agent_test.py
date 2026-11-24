import asyncio, sys, json
from app.agents.briefing import BriefingAgent
from app.agents.base import AgentInput

TENANT = "e587e037-a729-4f91-9b09-08600cb62f91"

async def main():
    agent = BriefingAgent()

    # Test 1: user asks "what is my tomorrow schedule"
    print("=== Test 1: tomorrow schedule ===")
    out = await agent.run(AgentInput(
        task_description="what is my tomorrow schedule",
        context={"tenant_id": TENANT, "user_request": "what is my tomorrow schedule"},
    ))
    print("success:", out.success)
    print("error:", out.error)
    print("result keys:", list((out.result or {}).keys()))
    print("items_count:", len(((out.result or {}).get("items") or [])))
    print("items:", json.dumps(((out.result or {}).get("items") or []), default=str, indent=2)[:500])
    print("formatted:", ((out.result or {}).get("formatted") or "")[:300])

    print()
    print("=== Test 2: today schedule ===")
    out2 = await agent.run(AgentInput(
        task_description="what is my today schedule",
        context={"tenant_id": TENANT, "user_request": "what is my today schedule"},
    ))
    print("items_count:", len(((out2.result or {}).get("items") or [])))
    print("formatted:", ((out2.result or {}).get("formatted") or "")[:300])

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
