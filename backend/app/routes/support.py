from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.database.support_models import SupportTicket
from app.database.auth_models import User
from app.routes.auth import get_current_user
from pydantic import BaseModel
import uuid

router = APIRouter()

class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "normal"

@router.post("/ticket")
async def create_ticket(
    ticket: TicketCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    new_ticket = SupportTicket(
        user_id=user.id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority
    )
    session.add(new_ticket)
    await session.commit()
    return {"status": "success", "ticket_id": str(new_ticket.id)}

@router.get("/tickets")
async def list_tickets(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # In a real app, check if user is an admin. For now, return their tickets.
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.user_id == user.id).order_by(SupportTicket.created_at.desc())
    )
    tickets = result.scalars().all()
    return [{
        "id": str(t.id),
        "subject": t.subject,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "created_at": t.created_at.isoformat()
    } for t in tickets]
@router.patch("/tickets/{ticket_id}/resolve")
async def resolve_ticket(
    ticket_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    # Fetch ticket
    result = await session.execute(
        select(SupportTicket).where(SupportTicket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
        
    ticket.status = "resolved"
    await session.commit()
    
    return {"status": "success", "message": "Ticket resolved"}