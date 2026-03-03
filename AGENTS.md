# AGENTS.md - OpenMaritime Developer Guide

OpenMaritime is an open-source maritime chartering platform. Monorepo: `/backend` (FastAPI + SQLAlchemy async + Celery), `/frontend` (Next.js 15 + TanStack Table + Yjs), `/agents` (Multi-agent orchestration).

---

## Build, Lint & Test Commands

### Backend (Python)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Linting & formatting
pip install ruff black isort
ruff check app/ --fix
black app/
isort app/

# Type checking
pip install mypy
mypy app/ --ignore-missing-imports

# Testing
pip install pytest pytest-asyncio httpx
pytest                           # All tests
pytest tests/test_file.py        # Single file
pytest tests/test_file.py::test_function_name  # Single test
pytest -k "test_name"            # Pattern match
pytest -v -x                     # Verbose, stop on first failure
pytest --cov=app --cov-report=html  # Coverage

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "message"
```

### Docker

```bash
docker compose up -d
docker compose logs -f backend
docker compose exec backend alembic upgrade head
```

### Frontend (TypeScript)

```bash
cd frontend
npm install
npm run dev
npm run build
npm run lint
npx tsc --noEmit
```

---

## Code Style Guidelines

### Python (Backend)

**Imports**: Standard lib → third-party → local. Use absolute imports.
```python
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Fixture
```

**Formatting**: 100 char max line. Use `black app/` and `isort app/`.

**Types**: Always use type hints. Use `Optional[X]` not `X | None`. Use `List`, `Dict`, `Any` from typing.

**Naming**: Classes `PascalCase`, functions/variables `snake_case`, constants `UPPER_SNAKE_CASE`, private methods `_prefix`.

**Error Handling**: Use `HTTPException` with proper status codes.

**Async**: Always use `async def` and `await`. Never block with sync libs.

**Pydantic**: Use `BaseModel`, `Optional` for nullable fields.

### TypeScript/React (Frontend)

**Imports**: React first, then third-party, then local. Use `@/` absolute paths. Add `"use client"` for client components.

```typescript
"use client";
import { useState } from "react";
import { useAppStore } from "@/lib/store";
```

**Types**: Define `interface` for objects, `type` for unions.

**Naming**: Components `PascalCase`, files `kebab-case.ts` or `PascalCase.tsx`, vars `camelCase`, constants `UPPER_SNAKE_CASE`.

**State**: Use Zustand for client state, TanStack Query for server state.

**Hooks**: Always prefix with `use`.

---

## Project Structure

```
backend/app/
├── api/          # FastAPI routes
├── models/       # SQLAlchemy models
├── services/     # Business logic
├── plugins/      # Plugin hooks
├── workers/      # Celery tasks
└── main.py       # Entry point

frontend/
├── app/          # Next.js pages
├── components/   # React components
└── lib/          # Stores, hooks, utils
```

---

## Key Patterns

**Plugin System**: `backend/app/plugins/<name>/__init__.py` exports `hooks` dict with async functions.

**Offline Sync**: Use Zustand with Yjs for CRDT sync.

---

## Common Tasks

**Add API Endpoint**: Create router in `backend/app/api/<feature>.py`, include in `main.py` with prefix.

**Add Frontend Component**: Create in `frontend/components/<category>/<Name>.tsx`.

---

## Testing Guidelines

- Test files: `tests/test_<module>.py`
- Use pytest fixtures
- Mock external services (Ollama, APIs)
- Mark async tests: `@pytest.mark.asyncio`

---

## Security

- Never commit secrets or API keys
- Validate and sanitize inputs
- Use parameterized SQL queries (no f-strings)
- Store secrets in `.env`, never in code
