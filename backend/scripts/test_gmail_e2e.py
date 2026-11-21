"""Gmail E2E: connect check -> send_message -> search by subject."""
import asyncio, sys
from pathlib import Path as _P
from datetime import datetime, timezone
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.integrations.gmail import GmailConnector, GmailNotConnected
from app.integrations.oauth_tokens import load_tokens


TENANT = sys.argv[1] if len(sys.argv) > 1 else "de2b2f2b-1348-4ba3-bbc8-8eaf2b09face"
TO = sys.argv[2] if len(sys.argv) > 2 else "engmuzammil.ai.dev@gmail.com"


async def main():
    tokens = await load_tokens(tenant_id=TENANT, provider="gmail")
    if not tokens:
        raise SystemExit(f"Gmail not connected for tenant {TENANT}. Run /gmail/connect first.")
    print(f"token loaded: email={tokens.get('email')} scopes={len(tokens.get('scopes') or [])}")

    gmail = GmailConnector(TENANT)

    # Unique subject so search proves delivery
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    subject = f"Nexora Gmail E2E {stamp}"
    body = (
        f"This is an automated E2E test from Nexora AI.\n"
        f"Sent at {datetime.now(timezone.utc).isoformat()}\n"
        f"Tenant: {TENANT}\n"
    )

    print(f"sending to: {TO}")
    print(f"subject:    {subject}")
    sent = await gmail.send_message(to=TO, subject=subject, body=body)
    print(f"sent id:    {sent['id']}")
    print(f"thread id:  {sent.get('threadId')}")

    # Give Gmail a moment to index the message
    await asyncio.sleep(3)

    results = await gmail.search_messages(query=f"subject:\"{subject}\"", max_results=5)
    print(f"search hits: {len(results)}")
    for r in results:
        print(f"  {r['id']}  {r['subject']}  from={r['from']}")

    assert any(r["id"] == sent["id"] for r in results), (
        f"sent message not found in search: sent={sent['id']} "
        f"results={[r['id'] for r in results]}"
    )
    print("\nPASS: gmail E2E (send + search)")


asyncio.run(main())
