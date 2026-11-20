from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field
import json as _json

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.web_search import search, format_results


class ResearchFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="What was found for this research task")
    prospects: list[str] = Field(description="Prospect companies or contacts")
    key_insights: list[str] = Field(description="Important observations")
    gaps: list[str] = Field(description="What could not be determined")


def _build_research_prompt(payload: AgentInput, web_block: str) -> str:
    context = payload.context or {}
    deps = context.get("dependency_outputs") or {}
    if deps:
        dep_summary = _json.dumps(deps, indent=2, default=str)[:2000]
        return (
            f"Task: {payload.task_description}\n\n"
            f"PRIOR RESEARCH (build on this, do NOT restate it):\n{dep_summary}\n\n"
            f"NEW web search results:\n{web_block}\n\n"
            f"Your job: extend or deepen the prior findings. Do not repeat "
            f"the same companies or insights unless you have NEW information."
        )
    return (
        f"Task: {payload.task_description}\n\n"
        f"Web search results:\n{web_block}"
    )


class ResearchAgent(BaseAgent):
    name = "research"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            query = payload.task_description
            context = payload.context or {}
            user_request = context.get("user_request", "")
            if user_request and user_request not in query:
                query = f"{user_request} — {query}"

            results = search(query, max_results=5)
            web_block = format_results(results)

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(ResearchFindings)

            result = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's research specialist. "
                    "You will be given a task description and a block of REAL "
                    "web search results. Your job is to synthesize findings "
                    "FROM THE WEB RESULTS ONLY. "
                    "Rules: "
                    "(1) Do not invent companies, emails, people, or facts not "
                    "present in the web results. "
                    "(2) If the web results do not contain the requested "
                    "information, say so in 'gaps' — do not fabricate. "
                    "(3) When you list a prospect, include the source URL if "
                    "available. "
                    "(4) If web results are empty, return empty prospects and "
                    "explain the gap. "
                    "(5) If PRIOR RESEARCH is provided in the user message, "
                    "build on it — do not simply restate the same findings."
                )),
                HumanMessage(content=_build_research_prompt(payload, web_block)),
            ])

            return AgentOutput(success=True, result=result.model_dump())

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
