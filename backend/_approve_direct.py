import asyncio, sys, json, traceback
from sqlalchemy import text
from app.database import SessionFactory

async def main():
    async with SessionFactory() as db:
        row = (await db.execute(text(
            "SELECT id::text, agent_type, proposed_action, tenant_id::text, task_id "
            "FROM approvals WHERE id = '12cb60c0-7743-4d72-b44a-440965141839'"
        ))).fetchone()
    if not row:
        print("NOT FOUND"); return
    aid, agent, proposed, tenant, tid = row
    proposed = proposed or {}
    print("AGENT:", agent)
    print("TENANT:", tenant)
    action_kind = proposed.get("action_kind") or "execute_agent"
    print("ACTION_KIND:", action_kind)
    prepared = proposed.get("proposed_action") or proposed.get("prepared_result") or {}
    draft = prepared.get("draft") or proposed.get("draft") or {}
    to_addr = draft.get("to")
    subject = draft.get("subject")
    body = draft.get("body")
    print("TO:", to_addr)
    print("SUBJECT:", subject)
    print("BODY_LEN:", len(body or ""))
    print()
    from app.tools.gmail import draft_reply, send_approved_draft
    print("=== attempting draft_reply ===")
    try:
        nl = chr(10)
        formatted = "To: " + (to_addr or "") + nl + "Subject: " + (subject or "") + nl + nl + (body or "")
        dr = await draft_reply(tenant_id=tenant, thread_id="", body=formatted)
        print("DRAFT_REPLY_OK:", json.dumps(dr, default=str)[:400])
        did = (dr or {}).get("id") or (dr or {}).get("draft_id")
        print("DRAFT_ID:", did)
        if did:
            print("=== attempting send_approved_draft ===")
            sr = await send_approved_draft(tenant_id=tenant, draft_id=did)
            print("SEND_OK:", json.dumps(sr, default=str)[:400])
    except Exception as e:
        print("EXCEPTION:", type(e).__name__, str(e))
        traceback.print_exc()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
