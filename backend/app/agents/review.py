from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(
        description="One of: 'blocker', 'warning', 'nit'"
    )
    category: str = Field(
        description="e.g. 'accuracy', 'missing_info', 'hallucination_risk', 'tone', 'structure'"
    )
    detail: str = Field(description="What is wrong and why it matters")
    suggested_fix: str = Field(description="Concrete recommended change")


class ReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool = Field(
        description="True only if there are no blockers"
    )
    summary: str = Field(description="One or two sentences summarizing the review")
    issues: list[ReviewIssue] = Field(
        description="Issues found, ordered by severity"
    )
    strengths: list[str] = Field(
        description="What the reviewed output does well"
    )
    confidence: float = Field(
        description="Reviewer confidence in this assessment, 0.0 to 1.0"
    )


class ReviewAgent(BaseAgent):
    name = "review"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(ReviewReport)

            result = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's review specialist. "
                    "Your job is to critique the outputs of other agents and flag "
                    "problems before they reach a human. "
                    "You will receive prior agent outputs under 'dependency_outputs' "
                    "and/or 'other_task_outputs'. Review them carefully. "
                    "Look for: hallucinations (specific claims, facts, or companies that "
                    "seem invented or unlikely), missing information, structural problems, "
                    "and quality issues. "
                    "Set approved=false if you find any 'blocker' issues. "
                    "Be rigorous but not pedantic: 'nit' issues should not block approval. "
                    "Confidence should reflect how sure you are of the assessment."
                )),
                HumanMessage(content=str(payload.model_dump())),
            ])

            return AgentOutput(success=True, result=result.model_dump())

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
