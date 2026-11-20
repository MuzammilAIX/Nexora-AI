from tavily import TavilyClient
from ..config import settings


def search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web via Tavily. Returns a list of dicts:
        { "title": str, "url": str, "content": str, "score": float }

    Returns [] on any failure (missing key, network, etc.).
    The caller decides how to handle an empty result.
    """
    if not settings.TAVILY_API_KEY:
        return []

    try:
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        return response.get("results", [])
    except Exception:
        return []


def format_results(results: list[dict]) -> str:
    """Turn raw Tavily results into a compact text block for LLM prompts."""
    if not results:
        return "(no web results found)"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] {r.get('title', 'Untitled')}\n"
            f"    URL: {r.get('url', '')}\n"
            f"    {r.get('content', '')[:400]}"
        )
    return "\n\n".join(lines)
