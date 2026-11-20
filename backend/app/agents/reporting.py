from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field
import json as _json

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings


class ReportSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(description="Section heading, e.g. 'Executive Summary'")
    content: str = Field(description="Section body text, professional prose")


class BusinessReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Report title")
    executive_summary: str = Field(description="1-3 sentence high-level summary")
    sections: list[ReportSection] = Field(
        description="Ordered sections of the report"
    )
    findings: list[str] = Field(
        description="Key findings or insights highlighted from the source material"
    )
    next_steps: list[str] = Field(
        description="Recommended actions or follow-ups"
    )
    sources: list[str] = Field(
        description="References to source material used, e.g. 'task1', 'task2'"
    )


def _build_report_prompt(payload: AgentInput) -> str:
    context = payload.context or {}
    deps = context.get("dependency_outputs") or {}
    if deps:
        dep_summary = _json.dumps(deps, indent=2, default=str)[:3000]
        return (
            f"Task: {payload.task_description}\n\n"
            f"SOURCE MATERIAL (prior agent outputs — use these, do not invent):\n"
            f"{dep_summary}\n\n"
            f"Write a professional report grounded ONLY in the source material above."
        )
    return (
        f"Task: {payload.task_description}\n\n"
        f"No prior context available. If you cannot produce a report without "
        f"source material, populate 'next_steps' with what data is needed."
    )


class ReportingAgent(BaseAgent):
    name = "reporting"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(BusinessReport)

            result = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's reporting specialist. "
                    "Given a task and context (which may include research findings, "
                    "email drafts, or other agent outputs), produce a structured "
                    "professional business report. "
                    "Be factual: do not invent data, metrics, or names not present "
                    "in the context. If information is missing, note it in next_steps "
                    "or findings rather than fabricating. "
                    "Cite source material by referencing the task that produced it. "
                    "Use the ACTUAL names, facts, and numbers from the source "
                    "material. Do not substitute generic placeholders when real "
                    "company names are available."
                )),
                HumanMessage(content=_build_report_prompt(payload)),
            ])

            return AgentOutput(success=True, result=result.model_dump())

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
