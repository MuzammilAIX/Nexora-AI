"""Windows-safe uvicorn launcher.

Uvicorn 0.36+ forcibly reinstalls the Proactor policy during startup
regardless of what we set before uvicorn.run(). Setting loop="none" tells
uvicorn to skip its own event-loop setup entirely, so the Selector policy
we set here is what psycopg sees.
"""
import sys, asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn
uvicorn.run(
    "app.main:app",
    host="127.0.0.1",
    port=8001,
    log_level="info",
    loop="none",
)
