# Nexora AI — Multi-Agent Business Automation Platform

Turn everyday business instructions into coordinated, controlled, and measurable automated workflows.

## Quick start

1. Copy `.env.example` to `.env` and fill in values
2. Install dependencies: `uv sync`
3. Run database migrations: `cd backend; alembic upgrade head`
4. Start the server: `cd backend; uvicorn app.main:app --reload`

## Login

- Default test user: `test@nexora-test.com` / `TestPass123!`
- Frontend: http://127.0.0.1:8000/app/login.html

## API documentation

- Interactive Swagger docs: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Project structure

- `backend/app/` — FastAPI application
- `backend/app/agents/` — Specialized AI agents
- `backend/app/routes/` — HTTP endpoints
- `backend/app/workflows/` — LangGraph orchestration
- `backend/app/static/` — Frontend (HTML + CSS + JS)
- `backend/alembic/` — Database migrations

## Current status — MVP frontend complete

All 5 pages are fully functional and wired to real backend endpoints:

- **Overview** — live (4 KPI cards, recent runs, pending approvals, recent activity)
- **Assistant** — live (SSE streaming, plan rendering, approval prompts, raw state debug)
- **Approvals** — live (list, detail, approve/reject with task execution)
- **Integrations** — live (list, connect HubSpot, disconnect)
- **Activity** — live (read-only audit trail of all events)

### Verified end-to-end

- Authentication (JWT login, token persistence, route guard)
- Approvals flow (create via orchestrator, approve → execute, reject)
- Integrations flow (connect HubSpot with real token, disconnect)
- Assistant flow (chat message → SSE stream → structured plan rendering)
- Overview dashboard (parallel fetches from 4 endpoints)
- Audit trail (all business events logged and displayed)

### Git checkpoints

- `25bf350` — Slice 1.8: shell + approvals + integrations + activity pages
- `6aa63ff` — Slice 1.10: overview dashboard
- `0771c90` — Slice 1.9: assistant chat with SSE streaming

Each commit is verified working. `git reset --hard 0771c90` restores a fully functional app.

## Notes

- Never commit `.env` — it contains secrets
- `.env.example` shows which variables are required
- Debug JSON dumps and restore-test clones are ignored by `.gitignore`
- Collision check is part of the standard pre-flight (no duplicate top-level `const` across JS files)
