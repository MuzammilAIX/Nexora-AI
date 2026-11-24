from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ..config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncSession:
    """FastAPI dependency: yield a session, auto-close on request end."""
    async with SessionFactory() as session:
        yield session

# ---------------------------------------------------------------
# Model registration (deferred to avoid circular import with Base)
# ---------------------------------------------------------------
# SQLAlchemy resolves string FKs like ForeignKey("runs.id") against the
# metadata registry. That requires every referenced model to have been
# imported at least once before the mapper is configured. Without these
# imports, writes to audit_events / approvals fail with:
#   "Foreign key associated with column 'X.run_id' could not find table
#    'runs' with which to generate a foreign key to target column 'id'"
from .models import Run  # noqa: F401,E402
from .audit_models import AuditEvent  # noqa: F401,E402
from .approval_models import Approval  # noqa: F401,E402
from .auth_models import User, Tenant  # noqa: F401,E402
from .integration_models import Integration, IntegrationCredential  # noqa: F401,E402
from .document_models import Document  # noqa: F401,E402

from .team_models import Role, Invitation  # noqa: F401,E402
from .agent_models import Agent  # noqa: F401,E402

from .schedule_models import ScheduleEntry  # noqa: F401,E402