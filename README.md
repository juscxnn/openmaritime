# OpenMaritime

<div align="center">

**The Open-Source Alternative to Commercial Chartering Platforms**

*Wake AI-powered maritime chartering. Self-hosted. Privacy-first. ~$50-300/mo.*

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Discord](https://img.shields.io/discord/123456789)](https://discord.gg/openmaritime)
[![Docker](https://img.shields.io/docker/pulls/openmaritime/backend)](https://github.com/juscxnn/openmaritime)

</div>

---

## What Is OpenMaritime?

OpenMaritime is an **open-source, self-hosted maritime chartering platform** that replaces expensive commercial fixtures platforms with a modern, AI-powered alternative.

### Who Is It For?

- **Chartering Brokers** – Manage fixtures, track market opportunities, automate ranking
- **Ship Owners/Operators** – Monitor fixture demand, optimize vessel positioning
- ** Charterers** – Source vessels, compare rates, track market differentials
- ** commodity Traders** – Integrate shipping into trade flows, predict costs
- ** Maritime Startups** – Build on open infrastructure without licensing fees

### What Can It Do?

| Feature | Description |
|---------|-------------|
| **Wake AI Dashboard** | Single ranked fixture table with AI-scored opportunities |
| **Email → Fixture Extraction** | Auto-parse fixtures from Gmail/IMAP emails |
| **Multi-Agent AI Pipeline** | LangGraph agents: extract → enrich → rank → predict → decide |
| **RAG Market Brain** | Local Llama + pgvector for semantic market queries |
| **Plugin Ecosystem** | RightShip, MarineTraffic, Veson, Signal Ocean, Idwal, ZeroNorth |
| **Laytime Engine** | Built-in NOR/SOF/demurrage calculation |
| **Offline PWA** | Full offline capability with Yjs CRDT sync |
| **Cost Efficient** | ~$50-300/mo (your API keys + infrastructure) |

---

## Quick Start

### One-Click Deployment

```bash
# Clone and run
git clone https://github.com/juscxnn/openmaritime.git
cd openmaritime
docker compose up -d
```

Access at `http://localhost:3000`

### Manual Setup

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure your API keys
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Prerequisites

- **Ollama** (for local Llama 3.1): `ollama serve && ollama pull llama3.1:70b`
- **PostgreSQL** (or use Docker)
- **Redis** (for Celery tasks)

---

## The Wake AI Dashboard

The heart of OpenMaritime – a **single ranked fixture table** that replaces inbox chaos:

```
Rank | Vessel/IMO      | Cargo    | Laycan      | Rate    | RightShip | Position    | Market Diff | Wake Score
-----|-----------------|----------|-------------|---------|-----------|-------------|-------------|------------
  1  | MT Ever Given   | 50k MT   | Mar 15-20   | $28.50  | A (4.2★)  | 22.3N/+12%  | +12% TCE    | 88%
     | 9753161         | Soy      | (4d left)   | /mt     | GHG A     | 114.1E/~3d  |             | [FIX NOW]
```

### Key Columns

- **Wake Score** – AI score (0-100) based on TCE delta, vessel age, laycan urgency, risk factors
- **Market Diff** – Implied TCE vs Baltic Index (color-coded)
- **RightShip** – Safety ★ and GHG rating
- **Position** – Live AIS from MarineTraffic
- **Actions** – FIX NOW (creates Veson voyage + Slack alert)

---

## How It Works

### 1. Email Sync & Extraction

Connect your Gmail → OpenMaritime automatically:
1. Fetches emails with "fixture", "charter", "cargo" subjects
2. Parses vessel name, IMO, cargo, laycan, rate, ports
3. Creates fixture records in database

### 2. Wake AI Pipeline (LangGraph)

Each fixture runs through 5 AI agents:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ EXTRACTION  │───▶│ ENRICHMENT  │───▶│   RANKING   │───▶│  PREDICTION │───▶│  DECISION   │
│ Agent       │    │ Agent       │    │ Agent       │    │ Agent       │    │ Agent       │
├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤
│ Parse raw   │    │ RightShip,  │    │ TCE delta,  │    │ Demurrage   │    │ FIX NOW /   │
│ email data  │    │ MT, Idwal   │    │ urgency,    │    │ prediction  │    │ EXPLORE /   │
│             │    │ enrichment  │    │ risk score  │    │             │    │ WAIT        │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

All powered by **local Llama 3.1** (quantized 8B/70B) – no cloud AI dependencies.

### 3. Real-Time Enrichment

Parallel enrichment from:
- **RightShip** – Safety score, GHG rating, inspections
- **MarineTraffic** – AIS position, ETA, destination
- **Idwal** – Vessel grading (0-100)
- **Signal Ocean** – Market voyages
- **ZeroNorth** – Bunker optimization

### 4. RAG Market Brain

Semantic search over:
- Baltic Indices (BDI, BCTI)
- News headlines
- Weather alerts
- Historical fixtures

Query in natural language: *"Show me VLCCs loading in Middle East to China with laycan next week"*

---

## Plugin System

Plugins live in `backend/app/plugins/`:

| Plugin | Description | API Key Required |
|--------|-------------|------------------|
| `rightship` | Safety scores, GHG ratings | Yes |
| `marinetraffic` | AIS positions, ETA | Yes |
| `veson` | IMOS voyage sync | Yes |
| `signalocean` | Market data | Yes |
| `idwal` | Vessel grading | Yes |
| `zeronorth` | Bunker optimization | Yes |
| `laytime` | Demurrage calculation | Built-in |
| `whisper` | Voice-to-fixture | Local Ollama |

### Adding a Plugin

1. Create `backend/app/plugins/<name>/__init__.py`
2. Export `hooks` dict with plugin functions
3. Add API key to `.env`

```python
hooks = {
    "on_fixture_enrich": your_enrich_function,
    "on_rank": your_ranking_function,
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  Next.js 15 + TanStack Table + Leaflet + Yjs (CRDT)       │
│  PWA with offline support                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                        BACKEND                               │
│  FastAPI + SQLAlchemy async + Celery + Redis               │
└────────────────────────┬────────────────────────────────────┘
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    ▼                    ▼                    ▼
┌──────────┐      ┌──────────┐        ┌──────────┐
│ Ollama   │      │ PostgreSQL│        │  Redis  │
│ (Llama)  │      │ +pgvector│        │ +Kafka  │
└──────────┘      └──────────┘        └──────────┘
```

### Multi-Agent System

Internal development agents:
- **Systems Architect** – Architecture decisions
- **FE/BE/DevOps** – Implementation
- **ML Architect** – AI/ML integration
- **Optimization Specialist** – Performance
- **Senior Expert UI/UX** – Design

---

## Configuration

Copy `.env.example` to `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/openmaritime

# AI
OLLAMA_BASE_URL=http://localhost:11434
LLAMA_MODEL=llama3.1:70b
USE_LOCAL_LLAMA=true

# Plugin API Keys
RIGHTSHIP_API_KEY=your_key
MARINETRAFFIC_API_KEY=your_key
VESON_API_TOKEN=your_token
```

---

## Roadmap

- [ ] Production-ready PostgreSQL schema with RLS
- [ ] Veson IMOS bi-directional sync
- [ ] Voice notes with Whisper
- [ ] Laytime visual builder
- [ ] Multi-tenant support
- [ ] Enterprise SSO (SAML/OIDC)
- [ ] Grafana dashboards for cost tracking

---

## License

**MIT** – OpenMaritime is free to use, modify, and distribute.

---

## Contributing

1. Fork the repo
2. Create a feature branch
3. Submit a PR

See `docs/` for detailed API specs and architecture decisions.

---

## Support

- **Discord**: [Join our community](https://discord.gg/openmaritime)
- **Issues**: [GitHub Issues](https://github.com/juscxnn/openmaritime/issues)
- **Email**: hello@openmaritime.io
