import ast
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PATTERN_BLOCK = r"""BRIEFING_PATTERNS = _re.compile(
    r"\b(daily\s+briefing|morning\s+briefing|my\s+briefing|briefing|agenda|"
    r"today'?s?\s+schedule|schedule\s+(?:for\s+)?today|schedule\s+today|"
    r"(?:our|my)\s+(?:today'?s?\s+)?schedule|tomorrow'?s?\s+schedule|"
    r"what'?s\s+(?:on\s+)?(?:for\s+)?today)\b",
    _re.IGNORECASE,
)


def _is_briefing_request(user_request: str) -> bool:
    return bool(BRIEFING_PATTERNS.search(user_request or ""))

"""

OVERRIDE_BLOCK = """# Deterministic override: schedule/briefing questions go to the read-only briefing agent.
if _is_briefing_request(state.get("user_request", "")) and tasks:
    del tasks[1:]
    tasks[0]["agent_type"] = "briefing"
    tasks[0]["description"] = (
        "Compile the daily schedule briefing for: " + state.get("user_request", "")
    )
    tasks[0]["requires_approval"] = False
"""


def load(rel):
    raw = (ROOT / rel).read_bytes().decode("utf-8-sig")
    eol = "\r\n" if "\r\n" in raw else "\n"
    return raw.split(eol), eol


def find(lines, needle, startswith=False):
    for i, ln in enumerate(lines):
        if (ln.lstrip().startswith(needle) if startswith else needle in ln):
            return i
    raise SystemExit("[ABORT] anchor not found: " + repr(needle))


def indent(line):
    return line[: len(line) - len(line.lstrip())]


def patch_db_init(lines):
    if any("schedule_models" in l for l in lines):
        return False
    lines.append("from .schedule_models import ScheduleEntry  # noqa: F401,E402")
    return True


def patch_main(lines):
    if any("schedule_router" in l for l in lines):
        return False
    i = find(lines, "app.include_router(audit_router")
    ind = indent(lines[i])
    lines[i:i] = [
        ind + "from .routes.schedule import router as schedule_router",
        ind + "app.include_router(schedule_router, prefix=settings.API_PREFIX)",
    ]
    return True


def patch_workflow(lines):
    changed = False
    if not any("BriefingAgent" in l for l in lines):
        i = find(lines, "from app.agents.bulk_email import BulkEmailAgent")
        lines.insert(i + 1, "from app.agents.briefing import BriefingAgent")
        i = find(lines, '"bulk_email": BulkEmailAgent(),')
        lines.insert(i + 1, indent(lines[i]) + '"briefing": BriefingAgent(),')
        changed = True
    if not any("_is_briefing_request" in l for l in lines):
        i = find(lines, "_AGENTS = {", startswith=True)
        lines[i:i] = PATTERN_BLOCK.split("\n")
        j = find(lines, "# Deterministic override: bulk email requests")
        ind = indent(lines[j])
        block = [(ind + l) if l else l for l in OVERRIDE_BLOCK.rstrip("\n").split("\n")]
        lines[j:j] = block + [""]
        changed = True
    return changed


def patch_route_desc(lines):
    if any('"briefing"' in l for l in lines):
        return False
    start = find(lines, "AGENT_DESCRIPTIONS", startswith=True)
    end = None
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "}":
            end = j
            break
    if end is None:
        raise SystemExit("[ABORT] closing brace of AGENT_DESCRIPTIONS not found")
    ind = indent(lines[start + 1])
    if not lines[end - 1].rstrip().endswith(","):
        lines[end - 1] = lines[end - 1].rstrip() + ","
    lines.insert(end, ind + '"briefing":   "Compile the daily schedule: internal plan, Google Calendar and pending approvals (read-only).",')
    return True


PATCHES = [
    ("app/database/__init__.py", patch_db_init),
    ("app/main.py", patch_main),
    ("app/workflows/orchestrator.py", patch_workflow),
]

staged = []
for rel, fn in PATCHES:
    lines, eol = load(rel)
    if fn(lines):
        text = eol.join(lines)
        ast.parse(text)
        staged.append((rel, text))
        print("[patched]", rel)
    else:
        print("[skip]   ", rel, "(already patched)")

for rel, text in staged:
    p = ROOT / rel
    shutil.copy(p, str(p) + ".bak_schedule")
    p.write_bytes(text.encode("utf-8"))

for rel in ("app/database/schedule_models.py", "app/tools/schedule.py", "app/tools/briefing.py",
            "app/agents/briefing.py", "app/routes/schedule.py"):
    ast.parse((ROOT / rel).read_bytes().decode("utf-8-sig"))
print("ALL OK: patches applied, new files parse")