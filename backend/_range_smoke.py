import sys
from datetime import date
sys.path.insert(0, r"C:\Users\IBS TRADER\Nexora-AI\backend")
from app.agents.briefing import _parse_range

today = date.today()
tests = [
    "whats my upcomg 7 days schedule",
    "whats my upcoming 7 days schedule",
    "provide schedule for next 7 days",
    "7 days schedule",
    "schedule for 7 days",
    "whats my today schedule",
    "whats my nx 3 days calendar",
    "next 3 weeks",
    "7 weeks schedule",
]

for t in tests:
    try:
        s, e = _parse_range(t, today)
        span = (e - s).days
        print(f"span={span:3d}d  [{s} to {e}]  {t}")
    except Exception as ex:
        print(f"ERROR: {ex}  |  {t}")
