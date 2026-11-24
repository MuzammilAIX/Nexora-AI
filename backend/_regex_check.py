import sys
from app.workflows.orchestrator import BRIEFING_PATTERNS

tests = [
    "next 7 days schedule",
    "this week schedule",
    "what do i have this month",
    "provide the schedule of next days until 30 Nov 2026",
    "Whats my tommor schedule",
    "show me my calendar",
    "send an email",
    "show sales report",
]
for t in tests:
    m = BRIEFING_PATTERNS.search(t)
    if m:
        print("MATCH  |", t, "| captured:", repr(m.group(0)))
    else:
        print("NO     |", t)
