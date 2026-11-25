# StockLens MVP — Indian equity research platform (prototype)

All data is **synthetic** (fictional companies). Architecture follows the StockLens blueprint: modular FastAPI monolith,
SQLAlchemy models, deterministic financial engine, JSON-query screener, sector momentum engine, rule-based earnings quality.

## Run (no Docker needed)
    cd backend
    pip install -r requirements.txt
    python -m app.seed.generate          # creates stocklens.db with 40 fictional companies
    uvicorn app.main:app --port 8000     # open http://localhost:8000  (API docs: /docs)

## Test and benchmark
    cd backend && python -m pytest tests -q --junitxml=/tmp/junit.xml
    python ../scripts/benchmark.py       # writes docs/results.json

## PostgreSQL / TimescaleDB
    docker compose up -d db
    export DATABASE_URL=postgresql+psycopg://stocklens:change_this_password@localhost:5432/stocklens

## Not yet implemented (roadmap)
Authentication, Next.js frontend, live feeds (needs exchange licence), Redis/Celery, Qdrant RAG, LLM concall summaries.
