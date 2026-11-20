from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ConfigDict, Field
import json as _json

from .base import BaseAgent, AgentInput, AgentOutput
from ..config import settings
from ..tools.crm import (
    search_contacts,
    get_contact,
    create_task,
    format_contacts,
)


class ScoredLead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: str = Field(description="CRM contact id, exactly as given")
    name: str = Field(description="Full name from CRM data")
    email: str = Field(description="Email from CRM data, or empty string")
    company: str = Field(description="Company from CRM data, or empty string")
    score: int = Field(description="Fit score 0-100, based on CRM data only")
    score_rationale: str = Field(description="Why this score, grounded in CRM fields")
    follow_up_subject: str = Field(description="Email subject line draft")
    follow_up_body: str = Field(description="Email body draft, grounded in CRM data")


class LeadFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="What was done for this lead task")
    scored_leads: list[ScoredLead] = Field(description="Leads, highest score first")
    tasks_created: list[str] = Field(description="CRM task ids created, if any")
    gaps: list[str] = Field(description="What could not be determined from CRM data")


def _build_prompt(payload: AgentInput, contact_block: str, create_tasks: bool) -> str:
    context = payload.context or {}
    deps = context.get("dependency_outputs") or {}
    prior = ""
    if deps:
        prior = (
            "\n\nPRIOR TASK OUTPUTS (build on these, do NOT restate):\n"
            f"{_json.dumps(deps, indent=2, default=str)[:2000]}"
        )
    write_instruction = (
        "Also create one CRM follow-up task per lead with score >= 70 "
        "by calling the task tool. Return the created task ids in tasks_created."
        if create_tasks
        else
        "Do NOT create any CRM tasks. Drafts only. Leave tasks_created empty."
    )
    return (
        f"Task: {payload.task_description}\n\n"
        f"REAL CRM CONTACTS (the only allowed source of truth):\n{contact_block}\n\n"
        f"{write_instruction}"
        f"{prior}"
    )


class LeadAgent(BaseAgent):
    name = "lead"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            context = payload.context or {}
            create_tasks = bool(context.get("create_tasks", False))
            tenant_id = context.get("tenant_id")

            # 1. Pull real leads from HubSpot
            contacts = await search_contacts(
                tenant_id=tenant_id, query="", limit=20
            )
            contact_block = format_contacts(contacts)

            # 2. Score + draft via LLM, structured output
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                timeout=60,
                max_retries=2,
            ).with_structured_output(LeadFindings)

            findings = await llm.ainvoke([
                SystemMessage(content=(
                    "You are Nexora AI's lead qualification specialist. "
                    "You will be given a task and a block of REAL CRM contacts. "
                    "Score and draft follow-ups FROM THE CRM DATA ONLY. "
                    "Rules: "
                    "(1) Do not invent names, emails, companies, or facts not "
                    "present in the CRM data. "
                    "(2) Score 0-100 based only on visible CRM fields "
                    "(lifecycle stage, job title, company, recency, completeness). "
                    "(3) For each lead, write a short personalized follow-up "
                    "grounded in that contact's actual company/title/lifecycle. "
                    "(4) If CRM data is sparse, say so in gaps and score lower. "
                    "(5) Return leads sorted by score, highest first. "
                    "(6) Every contact_id must match a contact id from the input."
                )),
                HumanMessage(content=_build_prompt(payload, contact_block, create_tasks)),
            ])

            # 3. Optionally create real CRM tasks for top leads
            tasks_created: list[str] = []
            if create_tasks:
                for lead in findings.scored_leads:
                    if lead.score < 70:
                        continue
                    try:
                        task = await create_task(
                            tenant_id=tenant_id,
                            subject=lead.follow_up_subject or f"Follow up with {lead.name}",
                            body=lead.follow_up_body or "Draft follow-up from Nexora AI.",
                            contact_id=lead.contact_id,
                        )
                        tid = str(task.get("id") or "")
                        if tid:
                            tasks_created.append(tid)
                    except Exception as exc:
                        # A single task failure must not kill the whole run.
                        findings.gaps.append(f"task create failed for {lead.contact_id}: {exc}")

            result = findings.model_dump()
            result["tasks_created"] = tasks_created
            return AgentOutput(success=True, result=result)

        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
