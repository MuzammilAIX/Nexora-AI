from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.orchestrator import router as orchestrator_router
from app.routes.auth import router as auth_router
from app.routes.approvals import router as approvals_router
from app.routes.audit import router as audit_router
from app.routes.integrations import router as integrations_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "application": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(orchestrator_router, prefix=settings.API_PREFIX)
app.include_router(approvals_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(integrations_router, prefix=settings.API_PREFIX)

# Serve the static command-center frontend at /app
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(STATIC_DIR), html=True), name="app-static")

from fastapi.responses import RedirectResponse
@app.get("/", include_in_schema=False)
async def _root_redirect():
    return RedirectResponse(url="/app/login.html")
