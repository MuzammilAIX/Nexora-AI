"""Schedule routes. Always tenant-scoped via the logged-in user."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..database.auth_models import User
from ..database.schedule_models import ScheduleEntry
from ..auth_deps import get_current_user
from ..tools.briefing import build_briefing
from ..tools.schedule import (
    RECURRENCES, ensure_aware, list_occurrences, local_tz, local_tz_name, month_bounds,
)

router = APIRouter(prefix="/schedule", tags=["Schedule"])

ENTRY_TYPES = {"meeting", "shift", "task", "deadline"}


class EntryIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    entry_type: str = "meeting"
    start_at: datetime
    end_at: datetime | None = None
    all_day: bool = False
    recurrence: str | None = None
    recurrence_until: datetime | None = None
    assignee_id: UUID | None = None
    notes: str | None = None

    @field_validator("entry_type")
    @classmethod
    def _type(cls, v: str) -> str:
        if v not in ENTRY_TYPES:
            raise ValueError(f"entry_type must be one of {sorted(ENTRY_TYPES)}")
        return v

    @field_validator("recurrence")
    @classmethod
    def _rec(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.upper()
        if v not in RECURRENCES:
            raise ValueError(f"recurrence must be one of {sorted(RECURRENCES)}")
        return v


class EntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    entry_type: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    all_day: bool | None = None
    recurrence: str | None = None
    recurrence_until: datetime | None = None
    assignee_id: UUID | None = None
    notes: str | None = None


def _check_range(start: datetime, end: datetime | None) -> None:
    if end is not None and ensure_aware(end) <= ensure_aware(start):
        raise HTTPException(status_code=422, detail="end_at must be after start_at")


@router.get("")
async def list_month(
    month: str | None = None,
    user: User = Depends(get_current_user),
):
    now = datetime.now(local_tz())
    try:
        y, m = (int(p) for p in month.split("-")) if month else (now.year, now.month)
        start, end = month_bounds(y, m)
    except Exception:
        raise HTTPException(status_code=422, detail="month must look like 2026-12")
    return await list_occurrences(str(user.tenant_id), start, end)


@router.get("/briefing")
async def briefing(
    day: date | None = None,
    user: User = Depends(get_current_user),
):
    return await build_briefing(str(user.tenant_id), day)


@router.post("", status_code=201)
async def create_entry(
    body: EntryIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _check_range(body.start_at, body.end_at)
    row = ScheduleEntry(
        tenant_id=user.tenant_id,
        title=body.title.strip(),
        entry_type=body.entry_type,
        start_at=ensure_aware(body.start_at),
        end_at=ensure_aware(body.end_at),
        all_day=body.all_day,
        recurrence=body.recurrence,
        recurrence_until=ensure_aware(body.recurrence_until),
        assignee_id=body.assignee_id,
        notes=body.notes,
        created_by=user.id,
    )
    session.add(row)
    await session.commit()
    return {"id": str(row.id)}


async def _get_owned(session: AsyncSession, entry_id: UUID, user: User) -> ScheduleEntry:
    row = (await session.execute(
        select(ScheduleEntry).where(
            ScheduleEntry.id == entry_id, ScheduleEntry.tenant_id == user.tenant_id
        )
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return row


@router.patch("/{entry_id}")
async def update_entry(
    entry_id: UUID,
    body: EntryUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = await _get_owned(session, entry_id, user)
    data = body.model_dump(exclude_unset=True)
    if "entry_type" in data and data["entry_type"] not in ENTRY_TYPES:
        raise HTTPException(status_code=422, detail="invalid entry_type")
    if "recurrence" in data:
        rec = (data["recurrence"] or "").upper() or None
        if rec and rec not in RECURRENCES:
            raise HTTPException(status_code=422, detail="invalid recurrence")
        data["recurrence"] = rec
    for k in ("start_at", "end_at", "recurrence_until"):
        if k in data:
            data[k] = ensure_aware(data[k])
    for k, v in data.items():
        setattr(row, k, v)
    _check_range(row.start_at, row.end_at)
    await session.commit()
    return {"id": str(row.id), "updated": True}


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = await _get_owned(session, entry_id, user)
    await session.delete(row)
    await session.commit()
    return {"deleted": True}


@router.get("/timezone")
async def current_timezone():
    now = datetime.now(local_tz())
    return {"timezone": local_tz_name(), "local_time": now.isoformat(timespec="seconds")}
