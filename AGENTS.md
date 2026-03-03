# AGENTS.md - OpenMaritime Developer Guide

This file provides guidance for AI agents operating in this repository.

---

## Project Overview

OpenMaritime is an open-source maritime chartering platform with Wake AI. The codebase is a monorepo:
- `/backend` - FastAPI + SQLAlchemy async + Celery (Python)
- `/frontend` - Next.js 15 + TanStack Table + Yjs (TypeScript)
- `/agents` - Multi-agent orchestration system

---

## Build, Lint & Test Commands

### Backend (Python)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Run with custom host
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Linting (install ruff first)
pip install ruff
ruff check .
ruff check app/ --fix

# Type checking (install mypy first)
pip install mypy
mypy app/ --ignore-missing-imports

# Testing (install pytest first)
pip install pytest pytest-asyncio httpx
pytest                           # Run all tests
pytest tests/                    # Run tests in directory
pytest tests/test_file.py        # Run specific test file
pytest tests/test_file.py::test_function_name  # Run single test
pytest -k "test_name"           # Run tests matching pattern
pytest --tb=short               # Shorter traceback
pytest -v                       # Verbose output

# Coverage
pip install pytest-cov
pytest --cov=app --cov-report=html
```

### Frontend (TypeScript)

```bash
cd frontend

# Install dependencies
npm install

# Development
npm run dev                      # Dev server with turbopack
npm run dev -- -p 3001          # Custom port

# Build
npm run build                   # Production build
npm run start                   # Start production server

# Linting
npm run lint                    # Run ESLint
npx eslint . --ext .ts,.tsx    # Lint specific files
npx eslint --fix               # Auto-fix issues

# Type checking
npx tsc --noEmit               # Type check without emitting

# Testing (Jest - not configured yet, add to package.json)
# npm test
```

---

## Code Style Guidelines

### Python (Backend)

#### Imports
- Standard library first, then third-party, then local
- Use absolute imports: `from app.models import Fixture`
- Group: `from typing import` → `from fastapi import` → `from sqlalchemy import` → `from app import`
- Example:
  ```python
  from typing import List, Optional, Dict, Any
  from uuid import UUID

  from fastapi import APIRouter, Depends, HTTPException, Query
  from pydantic import BaseModel
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select

  from app.models import Fixture
  from app.main import async_session_maker
  ```

#### Formatting
- Line length: 100 characters max
- Use Black for formatting: `black app/`
- Use isort for imports: `isort app/`

#### Types
- Use type hints for all function signatures
- Use `Optional[X]` instead of `X | None` for Python < 3.10
- Use `List`, `Dict`, `Any` from typing (not builtins in type positions)
- Example:
  ```python
  def get_fixture(fixture_id: str, db: AsyncSession) -> Optional[FixtureResponse]:
      ...
  ```

#### Naming Conventions
- Classes: `PascalCase` (e.g., `FixtureCreate`, `WakeAIService`)
- Functions/variables: `snake_case` (e.g., `get_fixture`, `async_session_maker`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `JWT_ALGORITHM`)
- Private methods: prefix with `_` (e.g., `_extract_features`)

#### Error Handling
- Use custom exceptions with meaningful names
- Return proper HTTP status codes via `HTTPException`
- Example:
  ```python
  if not fixture:
      raise HTTPException(status_code=404, detail="Fixture not found")
  ```

#### Async/Await
- Always use `async def` for async functions
- Use `await` for all async calls
- Never block in async functions (use `asyncpg`, `aiohttp`, etc.)

#### Pydantic Models
- Use `BaseModel` for request/response schemas
- Use `Optional` for nullable fields
- Example:
  ```python
  class FixtureCreate(BaseModel):
      vessel_name: str
      cargo_type: str
      rate: Optional[float] = None
  ```

### TypeScript/React (Frontend)

#### Imports
- React imports first, then third-party, then local
- Use absolute imports from `@/` or relative
- Example:
  ```typescript
  "use client";

  import { useState, useEffect } from "react";
  import { createColumnHelper } from "@tanstack/react-table";

  import { MiniMap } from "@/components/wake/MiniMap";
  import { useAppStore } from "@/lib/store";
  ```

#### Formatting
- Use Prettier (configured in project)
- Run: `npx prettier --write .`

#### Types
- Always define interfaces for props and data
- Use `interface` for objects, `type` for unions/aliases
- Example:
  ```typescript
  interface Fixture {
    id: string;
    vessel_name: string;
    wake_score: number | null;
  }
  ```

#### Naming Conventions
- Components: `PascalCase` (e.g., `WakeTable`, `MiniMap`)
- Files: `kebab-case.ts` or `PascalCase.tsx`
- Functions/variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`

#### React Patterns
- Use `"use client"` directive for client components
- Use Zustand for state management
- Use TanStack Query for server state
- Example:
  ```typescript
  "use client";

  import { useAppStore } from "@/lib/store";

  export function WakeTable() {
    const fixtures = useAppStore((state) => state.getFixturesArray());
    // ...
  }
  ```

#### Hooks
- Always name custom hooks with `use` prefix
- Example: `useFixtureSync`, `useVoiceNote`

---

## Project Structure

```
backend/
├── app/
│   ├── api/          # FastAPI routes (fixtures, plugins, auth, etc.)
│   ├── models/       # SQLAlchemy models
│   ├── services/     # Business logic (wake_ai, email_sync, rag, etc.)
│   ├── plugins/      # Plugin implementations
│   ├── workers/      # Celery tasks
│   └── main.py       # FastAPI app entry
├── tests/            # (Add tests here)
└── requirements.txt

frontend/
├── app/              # Next.js app router pages
├── components/       # React components (wake/, ui/, layout/)
├── lib/              # Utilities, stores, hooks
├── public/           # Static assets
└── package.json
```

---

## Key Patterns

### Plugin System (Backend)

Plugins in `backend/app/plugins/<name>/` export a `hooks` dict:

```python
async def on_fixture_enrich(fixture) -> Dict[str, Any]:
    # Enrich fixture with data
    return {"data": "value"}

hooks = {
    "on_fixture_enrich": on_fixture_enrich,
}
```

### CRDT Offline Sync (Frontend)

Use Zustand with Yjs for offline-first:

```typescript
import { useAppStore } from "@/lib/store";

const fixture = useAppStore((state) => 
  state.fixtures[fixtureId]
);
```

### API Requests

Backend returns Pydantic models, frontend uses fetch:

```typescript
const res = await fetch("http://localhost:8000/api/v1/fixtures");
const fixtures = await res.json();
```

---

## Common Tasks

### Adding a New Plugin

1. Create directory: `backend/app/plugins/<plugin_name>/`
2. Create `__init__.py` with hooks
3. Add API keys to `.env.example`
4. Add to plugin marketplace in `backend/app/api/marketplace.py`

### Adding a New API Endpoint

1. Create router in `backend/app/api/<feature>.py`
2. Import and include in `backend/app/main.py`:
   ```python
   from app.api import myfeature
   app.include_router(myfeature.router, prefix="/api/v1/myfeature", tags=["myfeature"])
   ```

### Adding a Frontend Component

1. Create in `frontend/components/<category>/<ComponentName>.tsx`
2. Export and use in pages

---

## Testing Guidelines

- Test files: `tests/test_<module>.py` for Python
- Use pytest fixtures for common setup
- Mock external services (Ollama, APIs)
- Test async functions with `@pytest.mark.asyncio`

---

## Environment Variables

See `.env.example` for all configuration options. Never commit secrets.
