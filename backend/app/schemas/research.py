"""
Schemas for the Research Agent.
Contract between ResearchAgent (producer) and EmailAgent / ReportingAgent (consumers).
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    """What the orchestrator sends into the Research Agent."""
    query: str = Field(..., description="What we want researched, e.g. 'Find SaaS startups in Pakistan hiring sales reps'")
    max_prospects: int = Field(5, ge=1, le=50)
    industries: list[str] = Field(default_factory=list)


class Prospect(BaseModel):
    """One company / contact found by research."""
    company_name: str
    website: str | None = None
    industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    pain_points: list[str] = Field(default_factory=list)
    notes: str | None = None
    sources: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    """What the Research Agent returns."""
    query: str
    prospects: list[Prospect]
    confidence: float = Field(..., ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    warnings: list[str] = Field(default_factory=list)