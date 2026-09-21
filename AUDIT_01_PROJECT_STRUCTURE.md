# AUDIT_01_PROJECT_STRUCTURE.md

## Project Structure Audit

| Area | Location | Technology | Status | Notes |
|------|----------|------------|--------|-------|
| **Backend Root** | `app/` | FastAPI + Python 3.11+ | IMPLEMENTED | Well-organized modular structure |
| **API Routes** | `app/api/routes/` | FastAPI | IMPLEMENTED | 7 route modules: health, documents, analysis, companies, comparison, reports, risks |
| **API Main** | `app/api/main.py` | FastAPI | IMPLEMENTED | Proper lifespan, CORS, middleware |
| **Configuration** | `app/config/settings.py` | Pydantic Settings | IMPLEMENTED | Comprehensive env-based config |
| **Database Models** | `app/db/base.py` | SQLAlchemy 2.0 Async | IMPLEMENTED | 7 models: Company, Report, RiskItem, EvolutionEntry, FinancialSnapshot, Workspace, SavedScan |
| **Database Session** | `app/db/session.py` | SQLAlchemy Async | IMPLEMENTED | Connection pooling, lifecycle management |
| **Database Migrations** | `app/db/migrations/` | Alembic | NOT IMPLEMENTED | Directory exists but empty (only __init__.py) |
| **Repositories** | `app/db/repositories/` | Custom | PARTIALLY IMPLEMENTED | 4 repository files exist but mostly empty/not used |
| **Document Ingestion** | `app/ingestion/` | PyMuPDF, pdfplumber | IMPLEMENTED | Loaders, extractors, OCR fallback |
| **Text Processing** | `app/processing/` | Custom | IMPLEMENTED | Chunking, cleaning, normalization, section detection |
| **Risk Engine** | `app/risk_engine/` | Custom + Rule-based | IMPLEMENTED | Pipeline with detector, extractor, classifier, severity, confidence, deduplicator, evidence |
| **LLM Abstraction** | `app/llm/` | Multi-provider | IMPLEMENTED | Base + Groq, Ollama, Claude providers |
| **LLM Prompts** | `app/llm/prompts/` | Custom | IMPLEMENTED | Risk extraction, classification, comparison prompts |
| **Retrieval/Vector** | `app/retrieval/` | Hybrid (BM25 + Dense) | IMPLEMENTED | Embeddings, vector stores (memory, pgvector, Pinecone), RAG chain |
| **Comparison** | `app/comparison/` | Custom | PLACEHOLDER | 7 modules but all empty (0 bytes each) |
| **Intelligence** | `app/intelligence/` | Custom | PARTIALLY IMPLEMENTED | 7 modules, some empty, some with basic structure |
| **Taxonomy** | `app/taxonomy/` | JSON + Rules | IMPLEMENTED | 18 risk categories, severity levels, keyword matching |
| **Models/Schemas** | `app/models/` | Pydantic | IMPLEMENTED | Request/response models for all APIs |
| **Utilities** | `app/utils/` | Custom | IMPLEMENTED | Hashing, IDs, timing |
| **Frontend Root** | `frontend/src/` | React + TanStack Router | IMPLEMENTED | Modern React with TypeScript |
| **Frontend Routes** | `frontend/src/routes/` | TanStack Router | IMPLEMENTED | 14 route components |
| **UI Components** | `frontend/src/components/ui/` | Shadcn/UI + Tailwind | IMPLEMENTED | 30+ UI components |
| **Mock Data** | `frontend/src/lib/mock-data.ts` | TypeScript | IMPLEMENTED | Extensive hardcoded demo data |
| **Tests** | `tests/` | pytest + httpx | PARTIALLY IMPLEMENTED | Conftest with SQLite, fixtures but no actual test files |
| **Scripts** | `scripts/` | Python CLI | IMPLEMENTED | seed_demo_data, ingest_reports, run_pipeline, evaluate_pipeline |
| **Configuration Files** | Root | pyproject.toml, .env.example | IMPLEMENTED | Complete dependency and config management |
| **Documentation** | `docs/`, `documentation/`, README.md | Markdown | IMPLEMENTED | Comprehensive README |
| **Docker** | `docker/` | Docker Compose | NOT IMPLEMENTED | Empty docker-compose.yml and Dockerfile |
| **Sample Data** | `Phase1_2/annual_reports/` | PDF | IMPLEMENTED | 14 sample PDF reports |
| **Vector Store** | Code only | pgvector, Pinecone, Memory | IMPLEMENTED | Abstract interface with 3 implementations |
| **Embeddings** | `app/retrieval/embeddings.py` | Sentence Transformers | IMPLEMENTED | BGE-large-en-v1.5 (1024 dim) |
| **OCR** | `app/ingestion/ocr/` | Tesseract | IMPLEMENTED | Fallback router with OCR engine |

---

## Summary

**Overall Architecture**: Well-structured monorepo with clear separation of concerns. Backend follows clean architecture principles with distinct layers (API, domain, infrastructure). Frontend uses modern React patterns.

**Critical Gaps**:
1. **No database migrations** - Tables defined in code but no Alembic migrations
2. **Database not running** - PostgreSQL connection fails (password auth failed)
3. **Comparison modules empty** - 7 comparison modules are 0-byte placeholders
4. **No .env file** - Using defaults, no GROQ_API_KEY configured
5. **Tests incomplete** - Only conftest.py exists, no actual test files
6. **Docker not configured** - Empty docker-compose.yml
7. **Frontend uses mock data** - All dashboard data hardcoded in mock-data.ts
8. **LLM integration not tested** - GROQ_API_KEY not set
9. **Intelligence modules partially empty** - Several 0-byte files