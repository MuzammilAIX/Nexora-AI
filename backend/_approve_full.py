import asyncio, sys, traceback
from sqlalchemy import text
from app.database import SessionFactory
from app.routes.approvals import approve_approval, DecisionBody
from app.database.auth_models import User
from uuid import UUID

async def main():
    async with SessionFactory() as db:
        uid = (await db.execute(text(
            "SELECT id FROM users WHERE email = 'newnexora.systems+success@gmail.com'"
        ))).scalar_one()
        user_row = await db.get(User, uid)
    print("USER:", user_row.email)
    try:
        async with SessionFactory() as db:
            res = await approve_approval(
                approval_id=UUID("12cb60c0-7743-4d72-b44a-440965141839"),
                body=DecisionBody(note="probe"),
                session=db,
                user=user_row,
            )
            print("APPROVE_OK:", res)
    except Exception as e:
        print("APPROVE_EXCEPTION:", type(e).__name__, str(e))
        traceback.print_exc()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
