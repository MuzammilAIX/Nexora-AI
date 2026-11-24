import sys
sys.path.insert(0, r"C:\Users\IBS TRADER\Nexora-AI\backend")
from app.workflows.orchestrator import _is_briefing_request
tests = [
    "whats my upcomg 7 days schedule",
    "whats my upcoming 7 days schedule",
    "provide schedule for next 7 days",
    "7 days schedule",
    "schedule for 7 days",
    "whats my today schedule",
    "whats my nx 3 days calendar",
]
all_ok = True
for t in tests:
    ok = _is_briefing_request(t)
    all_ok = all_ok and ok
    print(f"{ok!s:6}  {t}")
print("ALL PASS" if all_ok else "SOME FAILED")
