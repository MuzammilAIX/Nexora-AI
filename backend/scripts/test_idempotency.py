"""Test 1: idempotency. First call True, second False, third (new key) True."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import text
from app.database import SessionFactory
from app.tools.idempotency import check_or_mark, mark_succeeded, mark_failed

TENANT = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"
KEY = "test:send_email:block7-1"
KEY_OTHER = "test:send_email:block7-1-other"


async def cleanup(*keys: str) -> None:
    """Remove leftover rows from previous runs so the test is re-runnable."""
    if not keys:
        return
    async with SessionFactory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM idempotency_keys WHERE key = ANY(:keys)"),
                {"keys": list(keys)},
            )


async def main():
    await cleanup(KEY, KEY_OTHER)

    r1 = await check_or_mark(KEY, TENANT, "send_email")
    print(f"1st call (should be True) : {r1}")
    assert r1 is True, f"expected True, got {r1}"

    await mark_succeeded(KEY, TENANT)

    r2 = await check_or_mark(KEY, TENANT, "send_email")
    print(f"2nd call (should be False): {r2}")
    assert r2 is False, f"expected False, got {r2}"

    r3 = await check_or_mark(KEY_OTHER, TENANT, "send_email")
    print(f"new key (should be True)  : {r3}")
    assert r3 is True, f"expected True, got {r3}"

    await mark_succeeded(KEY_OTHER, TENANT)

    print("\nPASS: idempotency")


asyncio.run(main())
