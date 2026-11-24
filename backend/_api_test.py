import asyncio, sys, httpx
from app.security import create_access_token
from app.database import SessionFactory
from sqlalchemy import text

async def main():
    async with SessionFactory() as db:
        user = (await db.execute(text(
            "SELECT id::text, tenant_id::text FROM users WHERE email = 'newnexora.systems+success@gmail.com'"
        ))).fetchone()
    print(f"USER: id={user[0]} tenant={user[1]}")
    token = create_access_token(subject=user[0])
    print(f"TOKEN: {token[:40]}...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "http://127.0.0.1:8001/api/v1/schedule?month=2026-11",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    print(f"STATUS: {resp.status_code}")
    print(f"BODY: {resp.text[:800]}")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
