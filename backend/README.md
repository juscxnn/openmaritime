# OpenMaritime Backend

## Tech Stack
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 with async support
- **Task Queue**: Celery + Redis
- **Database**: PostgreSQL (default), SQLite for dev
- **Authentication**: JWT with refresh tokens

## Getting Started

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Start Celery worker
celery -A app.workers.celery worker --loglevel=info
```

## Environment Variables

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/openmaritime
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Plugin API Keys (set via UI or env)
RIGHTSHIP_API_KEY=
MARINETRAFFIC_API_KEY=
VESON_API_TOKEN=
SIGNAL_OCEAN_API_KEY=
IDWAL_API_KEY=
ZERONORTH_API_KEY=

# Local LLM
OLLAMA_BASE_URL=http://localhost:11434
LLAMA_MODEL=llama3.1:70b
```

## Project Structure

```
backend/
├── app/
│   ├── api/           # API routes
│   ├── models/        # SQLAlchemy models
│   ├── services/     # Business logic
│   ├── plugins/      # Plugin loaders
│   ├── workers/      # Celery tasks
│   └── main.py       # FastAPI app
├── alembic/           # Database migrations
└── tests/            # Test suite
```
