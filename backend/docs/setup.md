# Development Setup Guide

## Prerequisites

- **Python 3.10+** — [Download](https://www.python.org/downloads/)
- **MongoDB** — [Atlas](https://www.mongodb.com/cloud/atlas) (recommended) or local installation
- **Ollama** — [Download](https://ollama.ai/) (required for local MedGemma model)
- **Git** — for version control

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/AI_Medical_Multi_Agent.git
cd AI_Medical_Multi_Agent
```

### 2. Create Virtual Environment

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual values:
# - GEMINI_API_KEY: from Google AI Studio (https://aistudio.google.com/)
# - MONGODB_URI: your MongoDB Atlas connection string
# - OLLAMA_BASE_URL: default http://localhost:11434
# - OLLAMA_MODEL: default medgemma:4b
```

### 5. Set Up Ollama (Local LLM)

```bash
# Install Ollama, then pull the model:
ollama pull medgemma:4b

# Verify it's running:
curl http://localhost:11434/api/tags
```

### 6. Run the Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify Health

```bash
# Simple liveness check
curl http://localhost:8000/api/v1/health

# Detailed dependency status
curl http://localhost:8000/api/v1/health/dependencies
```

---

## Running Tests

```bash
cd backend

# Unit tests with coverage
pytest tests/unit -v --cov=app --cov-report=term-missing

# Linting
flake8 app --max-line-length=120

# Type checking
mypy app --ignore-missing-imports

# Code formatting check
black --check app tests
```

---

## Project Structure

```
backend/
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Build and tool configuration
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── api/
│   │   └── v1/
│   │       └── routes_health.py   # Health check endpoints
│   ├── core/
│   │   ├── config.py     # Pydantic settings management
│   │   ├── logging.py    # Structured logging (structlog)
│   │   └── middleware.py  # Request correlation middleware
│   ├── db/
│   │   └── client.py     # Async MongoDB client abstraction
│   ├── models/           # Domain models (Phase 2)
│   └── services/
│       └── health_service.py  # Dependency health checks
├── tests/
│   └── unit/
│       ├── test_config.py
│       ├── test_logging.py
│       └── test_db_client.py
└── docs/
    ├── setup.md           # This file
    └── architecture.md    # Architecture overview
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: app` | Ensure you're running from the `backend/` directory |
| MongoDB connection timeout | Verify `MONGODB_URI` in `.env`; check Atlas network access |
| Ollama not reachable | Ensure Ollama is running: `ollama serve` |
| `ValidationError` on startup | Check all required env vars are set in `.env` |
