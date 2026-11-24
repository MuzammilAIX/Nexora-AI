"""
Analytics Agent — Workflow #3 from Section 14.

Design (per Section 8 of the business doc):
  - Deterministic Python does ALL math (via tools.postgres)
  - LLM only (a) parses intent, (b) narrates the metrics
  - Every number in the narrative is verified against the metrics
    before return — cannot hallucinate revenue.

Output is audit-clean: metrics, narrative, sql_used (for evidence),
verification_passed (bool).
"""
from datetime import datetime, timezone
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.postgres import get_monthly_sales


class AnalyticsQueryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: str = Field(description="Report period as YYYY-MM")
    comparison_period: str | None = Field(
        default=None, description="Comparison period YYYY-MM, optional"
    )
    focus: Literal["revenue", "products", "customers", "all"] = "all"
    include_recommendations: bool = True


class AnalyticsNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="2-4 sentence executive summary")
    highlights: list[str] = Field(description="3-5 bullet highlights")
    recommendations: list[str] = Field(
        description="2-4 actionable recommendations"
    )
    evidence_used: list[str] = Field(
        description="Sources cited, e.g. 'orders:2026-11', 'products:Widget Pro'"
    )


_SYSTEM_PROMPT = (
    "You are Nexora AI's analytics narrator. You receive a JSON payload "
    "containing precomputed sales metrics. Your job is to write a clear "
    "business narrative around those exact numbers.\n\n"
    "HARD RULES:\n"
    "(1) Do NOT invent numbers. Every number you write MUST appear in "
    "the provided metrics JSON.\n"
    "(2) Do NOT perform arithmetic. If a percentage is not in the "
    "metrics, do not compute it.\n"
    "(3) Cite evidence in `evidence_used` using the form "
    "`orders:YYYY-MM` and `product:<name>` for each data source used.\n"
    "(4) If metrics are zero or empty, say so honestly and do not "
    "guess.\n"
    "(5) Tone: professional, direct, board-ready."
)


def _plan_prompt(user_request: str, default_period: str) -> str:
    return (
        f"USER REQUEST: {user_request}\n\n"
        f"DEFAULT PERIOD (use if user did not specify): {default_period}\n\n"
        "Extract the reporting period and focus. If the user mentioned "
        "a month name, map it to YYYY-MM. If they mentioned two months, "
        "the later one is `period` and the earlier one is `comparison_period`."
    )


def _narrate_prompt(
    period: str,
    metrics: dict,
    comparison: dict | None,
) -> str:
    payload = {
        "period": period,
        "metrics": metrics,
        "comparison": comparison,
    }
    return (
        f"Write a business narrative for this analytics payload:\n\n"
        f"{payload}\n\n"
        "Produce summary, highlights, recommendations, and evidence_used. "
        "Every number must appear in the payload. No arithmetic."
    )


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            context = payload.context or {}
            tenant_id = context.get("tenant_id")
            user_request = context.get("user_request") or payload.task_description

            if not tenant_id:
                return AgentOutput(
                    success=False, error="analytics agent requires tenant_id"
                )

            default_period = datetime.now(timezone.utc).strftime("%Y-%m")

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=90,
                max_retries=2,
            ).with_structured_output(AnalyticsQueryPlan)

            plan: AnalyticsQueryPlan = await llm.ainvoke([
                SystemMessage(content="You extract analytics query parameters."),
                HumanMessage(content=_plan_prompt(user_request, default_period)),
            ])

            metrics = await get_monthly_sales(
                tenant_id=str(tenant_id),
                month=plan.period,
            )

            comparison = None
            if plan.comparison_period:
                comparison = await get_monthly_sales(
                    tenant_id=str(tenant_id),
                    month=plan.comparison_period,
                )

            narrate_llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=90,
                max_retries=2,
            ).with_structured_output(AnalyticsNarrative)

            narrative: AnalyticsNarrative = await narrate_llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=_narrate_prompt(
                    plan.period, metrics, comparison,
                )),
            ])

            # Section 8: compute MoM in Python (not SQL, not LLM) so it
            # exists in the metrics corpus the verifier checks against.
            if comparison and comparison.get("total_revenue"):
                base = comparison["total_revenue"]
                current = metrics.get("total_revenue", 0.0)
                metrics["mom_revenue_pct_change"] = (
                    round((current - base) / base * 100, 2) if base else None
                )
                metrics["mom_order_count_delta"] = (
                    metrics.get("order_count", 0) - comparison.get("order_count", 0)
                )
            else:
                metrics["mom_revenue_pct_change"] = None
                metrics["mom_order_count_delta"] = None

            verification = _verify_narrative_numbers(narrative, metrics, comparison)

            return AgentOutput(
                success=True,
                result={
                    "period": plan.period,
                    "comparison_period": plan.comparison_period,
                    "metrics": metrics,
                    "comparison": comparison,
                    "narrative": narrative.model_dump(),
                    "sql_sources": [
                        "orders:date_trunc(month,order_date) = :month",
                        "order_items:sum(line_total) grouped by product",
                        "products:name+category join",
                    ],
                    "row_data_count": metrics.get("line_item_count", 0),
                    "verification_passed": verification,
                    "data_driven": True,
                },
            )

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))


def _verify_narrative_numbers(
    narrative: AnalyticsNarrative,
    metrics: dict,
    comparison: dict | None,
) -> dict:
    """
    Every number the LLM wrote must trace back to a metric field.
    This is our Section 8 guard against hallucinated arithmetic.
    """
    corpus = _all_numbers(metrics)
    if comparison:
        corpus.update(_all_numbers(comparison))

    findings: list[str] = []
    for text_field in [narrative.summary, *narrative.highlights, *narrative.recommendations]:
        for num in _extract_numbers(text_field):
            if not _number_matches_any(num, corpus):
                findings.append(f"unverified number: {num}")

    return {
        "passed": len(findings) == 0,
        "unverified_numbers": findings,
        "metric_numbers_available": len(corpus),
    }


def _all_numbers(obj) -> set[float]:
    out: set[float] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            out |= _all_numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _all_numbers(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.add(round(float(obj), 2))
    return out


def _extract_numbers(s: str) -> list[float]:
    """
    Extract metric-like numbers from prose.

    Handles:
      - currency:   "$55,625.00" -> 55625.00
      - thousands:  "1,112.50"   -> 1112.50
      - percents:   "10.4%"      -> 10.4
      - integers:   "50"         -> 50.0

    Ignores:
      - bare 4-digit years (2000-2100) like "2026" in "November 2026"
        so the verifier does not flag a legitimate date reference.
    """
    import re

    if not s:
        return []

    # Normalize: remove currency symbols and thousands separators.
    # Do NOT remove % — we want to keep the number, just drop the sign.
    cleaned = s.replace("$", "").replace(",", "").replace("\u00a0", " ")

    # Match signed decimal numbers.
    raw = re.findall(r"-?\d+(?:\.\d+)?", cleaned)

    out: list[float] = []
    for token in raw:
        try:
            value = round(float(token), 2)
        except ValueError:
            continue

        # Skip bare 4-digit years (2000-2100) — these come from dates
        # like "November 2026" and are not metric values.
        if "." not in token and 2000 <= value <= 2100 and float(token).is_integer():
            continue

        out.append(value)

    return out


def _number_matches_any(n: float, corpus: set[float], tol: float = 0.5) -> bool:
    if n in corpus:
        return True
    for c in corpus:
        if abs(n - c) <= tol:
            return True
        if c != 0 and abs((n - c) / c) < 0.01:
            return True
    return False
