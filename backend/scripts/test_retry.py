"""Test 2: retry policy. Transient retries then succeeds; ValueError raises; exhaust on permanent."""
import asyncio, sys
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx
from app.tools.retry import with_retry

TENANT = "2857d0c5-6669-4d7d-a308-c8726bcc46bc"

async def transient_then_ok():
    transient_then_ok.calls += 1
    if transient_then_ok.calls < 3:
        raise httpx.ConnectError("simulated network failure")
    return "ok"
transient_then_ok.calls = 0

async def always_value_error():
    raise ValueError("validation failed")

async def always_transient():
    raise httpx.ConnectError("permanent network failure")

async def main():
    r = await with_retry(transient_then_ok, max_attempts=3, backoff=(0.1, 0.2, 0.3), tenant_id=TENANT)
    print(f"transient-then-ok    : {r} (calls={transient_then_ok.calls})")
    assert r == "ok" and transient_then_ok.calls == 3

    try:
        await with_retry(always_value_error, max_attempts=3, backoff=(0.1, 0.1, 0.1), tenant_id=TENANT)
        print("ValueError           : FAIL (no exception)")
        raise AssertionError("ValueError should have raised")
    except ValueError:
        print("ValueError           : raised immediately (correct)")

    try:
        await with_retry(always_transient, max_attempts=3, backoff=(0.1, 0.1, 0.1), tenant_id=TENANT)
        print("persistent transient : FAIL (no exception)")
        raise AssertionError("should have exhausted")
    except httpx.ConnectError:
        print("persistent transient : exhausted after 3 attempts (correct)")

    print("\nPASS: retry")

asyncio.run(main())
