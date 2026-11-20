import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..workflows.orchestrator import run_orchestrator
from ..services.event_bus import bus
from ..database import get_session, SessionFactory
from ..database.auth_models import User
from ..auth_deps import get_current_user
from ..services.run_store import (
    create_run,
    complete_run,
    get_run,
    list_runs,
)


router = APIRouter(
    prefix="/orchestrator",
    tags=["Orchestrator"],
)


class OrchestratorRequest(BaseModel):
    user_request: str = Field(
        min_length=1,
        max_length=10000,
        description="Business instruction for Nexora AI",
    )


# ── Non-streaming endpoint (saves to DB) ─────────────────────────

@router.post("/run")
async def execute_orchestrator(
    request: OrchestratorRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    db_run = await create_run(
        session, request.user_request, user.tenant_id, user.id
    )

    try:
        result = await run_orchestrator(
            request.user_request,
            run_id=str(db_run.id),
            tenant_id=str(user.tenant_id),
        )
        result["run_id"] = str(db_run.id)
        await complete_run(
            session,
            db_run.id,
            result,
            result.get("status", "unknown"),
        )

        if result.get("status") == "failed":
            raise HTTPException(
                status_code=502,
                detail=result.get("error", "Orchestration failed"),
            )

        # pending_approval is a valid 200 — the run succeeded but is
        # paused for human review. Only 'failed' is a 5xx.
        return result

    except HTTPException:
        raise

    except Exception as exc:
        import traceback, logging
        logging.getLogger(__name__).error(
            "orchestrator run failed: %s\n%s",
            exc, traceback.format_exc(),
        )
        await complete_run(
            session,
            db_run.id,
            {"error": str(exc)},
            "failed",
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected orchestration error occurred.",
        )


# ── Streaming endpoint (SSE) ─────────────────────────────────────

@router.post("/stream")
async def execute_orchestrator_stream(
    request: OrchestratorRequest,
    user: User = Depends(get_current_user),
):
    run_id = bus.new_run()

    async def event_stream():
        async def do_run():
            # New session — request-scoped session is closed once
            # StreamingResponse begins.
            async with SessionFactory() as db:
                db_run = await create_run(
                    db, request.user_request, user.tenant_id, user.id
                )
                try:
                    state = await run_orchestrator(
                        request.user_request,
                        run_id=str(db_run.id),
                        tenant_id=str(user.tenant_id),
                    )
                    status = state.get("status", "completed")
                    await complete_run(db, db_run.id, state, status)
                    bus.emit(
                        run_id,
                        "final",
                        state=state,
                        db_run_id=str(db_run.id),
                    )
                except Exception as exc:
                    try:
                        await complete_run(
                            db, db_run.id, {"error": str(exc)}, "failed"
                        )
                    except Exception:
                        pass
                    bus.emit(run_id, "error", error=str(exc))
                finally:
                    bus.close(run_id)

        runner = asyncio.create_task(do_run())

        try:
            while True:
                event = await bus.next(run_id)
                if event is None:
                    break
                yield f"data: {json.dumps(event, default=str)}\n\n"
                if event.get("type") == "end":
                    break
        finally:
            if not runner.done():
                runner.cancel()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── History endpoints ────────────────────────────────────────────

@router.get("/runs")
async def get_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    runs = await list_runs(session, user.tenant_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "user_request": r.user_request,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]


@router.get("/runs/{run_id}")
async def get_run_by_id(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    from uuid import UUID
    try:
        uid = UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run id")

    run = await get_run(session, uid, user.tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    state = None
    if run.state_json:
        try:
            state = json.loads(run.state_json)
        except Exception:
            state = None

    return {
        "id": str(run.id),
        "user_request": run.user_request,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "state": state,
    }
