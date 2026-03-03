# OpenMaritime

Open-source maritime chartering platform with Wake AI - the open-source alternative to commercial fixtures platforms.

## Architecture

### Multi-Agent Orchestration System

OpenMaritime uses a specialized multi-agent system for task delegation:

| Agent | Role | Expertise |
|-------|------|-----------|
| **Systems Architect** | Architectural decisions, system design | system_design, architecture_patterns, tech_stack, scalability |
| **FE/BE/DevOps** | Full-stack implementation | frontend, backend, devops, infrastructure |
| **ML Architect** | AI/ML integration, Wake AI | machine_learning, llama, ranking_algorithms |
| **Optimization Specialist** | Performance, caching | performance, caching, database |
| **Senior Expert UI/UX** | Design, accessibility | ui_design, ux_design, accessibility |

### Usage

```python
from agents.orchestrator import orchestrator, create_ml_task

# Create a task - auto-assigned to appropriate agent
task = orchestrator.create_task(
    title="Implement vessel ranking",
    description="Build Wake AI ranking using local Llama for fixture prioritization"
)

# Get agent configuration for execution
agent_config = orchestrator.execute_task(task.id)
# Returns: {agent_role, execution_prompt, ...}
```

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy (async) + Celery
- **Frontend**: Next.js 15 + TanStack Table + Tailwind CSS
- **Database**: PostgreSQL (production) / SQLite (dev)
- **AI**: Local Llama 3.1 via Ollama

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Plugin System

Plugins are loaded dynamically from `backend/app/plugins/`:

- `rightship` - Safety scores, GHG ratings
- `marinetraffic` - AIS positions, ETA
- `veson` - IMOS voyage sync (stub)
- `signalocean` - Market data (stub)
- `idwal` - Vessel grading (stub)
- `zeronorth` - Bunker optimization (stub)

## Wake AI Ranking

The core feature - AI-powered fixture ranking:

1. Extracts features (laycan urgency, cargo value, completeness)
2. Scores via local Llama 3.1 (or fallback heuristic)
3. Calculates TCE estimate and market differential
4. Renders ranked table with RightShip/MarineTraffic enrichment
