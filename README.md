# Nexora AI - Multi-Agent Business Automation Platform

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

- `backend/app/` - FastAPI application
- `backend/app/agents/` - Specialized AI agents
- `backend/app/routes/` - HTTP endpoints
- `backend/app/workflows/` - LangGraph orchestration
- `backend/app/static/` - Frontend (HTML + CSS + JS)
- `backend/alembic/` - Database migrations

## Current status

- Overview dashboard: live (KPI cards, recent activity)
- Approvals: live (list, detail, approve/reject)
- Integrations: live (connect HubSpot, disconnect)
- Activity: live (audit trail)
- Assistant chat: placeholder (next slice)

## Notes

- Never commit `.env` - it contains secrets
- `.env.example` shows which variables are required
