import sys
from app.workflows.orchestrator import BRIEFING_PATTERNS

tests = [
    "Whats my tommor schedule",
    "what's my tomorrow schedule",
    "what's my schedule",
    "what my tomorrow schedule",
    "show me my calendar",
    "what do i have today",
    "any meetings tomorrow",
    "what's happening today",
    "what's on today",
    "today schedule",
    "tomorrow events",
    "what events do i have",
    "send an email",
    "show sales report",
    "generate monthly report",
]
print("=== BRIEFING_PATTERNS match test ===")
for t in tests:
    m = BRIEFING_PATTERNS.search(t)
    print(("MATCH" if m else "NO   "), "|", t)
