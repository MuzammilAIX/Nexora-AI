import sys
from datetime import date
sys.path.insert(0, r"C:\Users\IBS TRADER\Nexora-AI\backend")
from app.agents.briefing import _parse_range
today = date.today()
for t in ["send email in 3 days", "follow up in 2 weeks", "approve 5 days ago"]:
    s, e = _parse_range(t, today)
    print(f"span={(e-s).days:3d}d  {t}")
