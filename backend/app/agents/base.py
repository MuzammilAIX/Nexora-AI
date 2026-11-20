from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    task_description: str
    context: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    async def run(self, payload: AgentInput) -> AgentOutput:
        ...
