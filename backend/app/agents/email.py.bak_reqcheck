from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings


class EmailDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(description="Recipient email address or 'unknown'")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Full email body, professional tone")
    personalization_notes: list[str] = Field(
        description="What was personalized and why"
    )
    tone: str = Field(description="e.g. professional, friendly, formal")


class EmailBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drafts: list[EmailDraft] = Field(description="One draft per prospect")
    send_ready: bool = Field(
        description="False if any required info is missing (e.g. recipient email)"
    )
    warnings: list[str] = Field(
        description="Missing info, unclear context, or risks"
    )


class EmailAgent(BaseAgent):
    name = "email"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(EmailBundle)

            result = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's email specialist. "
                    "Given a task and context (which may include research findings), "
                    "produce personalized, professional email drafts. "
                    "Do not invent recipient email addresses; use 'unknown' if not provided. "
                    "Do not claim emails were sent. Do not add unsubscribe links you don't have. "
                    "If key info is missing (recipient, company details), set send_ready=false "
                    "and list the missing info in warnings."
                )),
                HumanMessage(content=str(payload.model_dump())),
            ])

            return AgentOutput(success=True, result=result.model_dump())

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
