import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.database import engine
from app.database.schedule_models import ScheduleEntry


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: ScheduleEntry.__table__.create(c, checkfirst=True))
    print("schedule_entries ready")

asyncio.run(main())