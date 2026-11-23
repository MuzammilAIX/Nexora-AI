"""Reset a user password for local testing."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import engine
from app.security import hash_password, verify_password

TARGET_EMAIL = "test@nexora-test.com"
NEW_PASSWORD = "TestPass123!"


async def main():
    new_hash = hash_password(NEW_PASSWORD)
    print(f"new hash len: {len(new_hash)}")
    print(f"verify pre-write: {verify_password(NEW_PASSWORD, new_hash)}")

    async with engine.connect() as conn:
        async with conn.begin():
            result = await conn.execute(
                text("UPDATE users SET password_hash = :h WHERE email = :e"),
                {"h": new_hash, "e": TARGET_EMAIL},
            )
            print(f"rows updated: {result.rowcount}")

    async with engine.connect() as conn:
        row = (await conn.execute(
            text("SELECT email, password_hash FROM users WHERE email = :e"),
            {"e": TARGET_EMAIL},
        )).first()
        if row is None:
            print("FAIL: user not found after update")
            return
        print(f"DB email: {row[0]}")
        print(f"DB verify: {verify_password(NEW_PASSWORD, row[1])}")


asyncio.run(main())
