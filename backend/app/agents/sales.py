from .base import BaseAgent, AgentInput, AgentOutput


class SalesAgent(BaseAgent):
    name = "sales"

    async def run(self, payload: AgentInput) -> AgentOutput:
        try:
            context = payload.context or {}
            return AgentOutput(
                success=True,
                result={
                    "summary": f"Sales agent processed task: {payload.task_description}",
                    "task_description": payload.task_description,
                    "context_keys": list(context.keys()),
                },
            )
        except Exception as exc:
            return AgentOutput(success=False, error=str(exc))
