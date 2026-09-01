# GlobalRisk AI

AI-powered corporate risk intelligence platform that extracts material risks from annual reports and tracks year-over-year risk evolution with full evidence traceability.

## Features

- **Document Ingestion**: PDF parsing with OCR fallback for scanned documents
- **Risk Extraction**: LLM-powered semantic risk extraction with classification
- **Risk Taxonomy**: 18 risk categories with severity levels (Critical/High/Medium/Low/Informational)
- **Year-over-Year Comparison**: Detect new, removed, modified, and severity-changed risks
- **Evidence & Explainability**: Every risk linked to source paragraph with citations
- **REST API**: FastAPI-based API with async PostgreSQL backend
- **Vector Search**: Hybrid BM25 + dense retrieval for risk matching

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ with pgvector extension
- Redis (optional, for caching)
- Tesseract OCR (for scanned PDFs)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd globalrisk-ai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup

```bash
# Run migrations
alembic upgrade head
```

### Running the API

```bash
# Development
uvicorn app.api.main:app --reload

# Production
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Ingesting Reports

```bash
# Single report
python scripts/ingest_reports.py ./data/raw/annual_reports "Company Name" 2024 --sector "Technology"

# Run pipeline on existing report
python scripts/run_pipeline.py <report-uuid>
```

## API Endpoints

### Health
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/db` - Database connectivity
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

### Companies
- `POST /api/v1/companies` - Create company
- `GET /api/v1/companies` - List companies
- `GET /api/v1/companies/{id}` - Get company details
- `PATCH /api/v1/companies/{id}` - Update company
- `DELETE /api/v1/companies/{id}` - Delete company
- `GET /api/v1/companies/{id}/reports` - Get company reports

### Documents
- `POST /api/v1/documents/upload` - Upload annual report
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document
- `GET /api/v1/documents/{id}/status` - Get processing status
- `POST /api/v1/documents/{id}/reprocess` - Reprocess document

### Risk Analysis
- `POST /api/v1/analysis/extract` - Extract risks from report
- `GET /api/v1/analysis/{report_id}/risks` - Get report risks
- `GET /api/v1/analysis/risks/{risk_id}` - Get risk details
- `GET /api/v1/analysis/company/{company_id}/risks` - Get company risks
- `GET /api/v1/analysis/categories/stats` - Category statistics
- `GET /api/v1/analysis/severity/stats` - Severity statistics

### Risk Management
- `GET /api/v1/risks` - List all risks
- `GET /api/v1/risks/{risk_id}` - Get risk
- `GET /api/v1/risks/{risk_id}/evolution` - Get risk evolution
- `GET /api/v1/risks/stats/summary` - Risk summary
- `GET /api/v1/risks/stats/trends` - Risk trends

### Comparison
- `POST /api/v1/comparison/compare` - Compare two years
- `GET /api/v1/comparison/{company_id}/evolution` - Get evolution
- `GET /api/v1/comparison/{company_id}/summary` - Evolution summary
- `GET /api/v1/comparison/{company_id}/timeline` - Risk timeline

### Reports & Intelligence
- `POST /api/v1/reports/executive-summary` - Generate executive summary
- `GET /api/v1/reports/{company_id}/financial-health` - Financial health
- `POST /api/v1/reports/peer-comparison` - Peer comparison
- `GET /api/v1/reports/{company_id}/risk-explorer` - Risk explorer

## Project Structure

```
globalrisk-ai/
├── app/
│   ├── api/              # FastAPI routes and middleware
│   ├── config/           # Configuration and constants
│   ├── db/               # Database models and session
│   ├── ingestion/        # PDF loading, extraction, OCR
│   ├── processing/       # Text cleaning, normalization, chunking
│   ├── taxonomy/         # Risk taxonomy and classification
│   ├── risk_engine/      # Core risk detection and classification
│   ├── llm/              # LLM abstraction and providers
│   ├── retrieval/        # Embeddings, retrievers, RAG
│   ├── comparison/       # Year-over-year risk comparison
│   ├── intelligence/     # Executive summaries, peer analysis
│   ├── models/           # Pydantic schemas
│   └── utils/            # Utility functions
├── data/                 # Data directories
├── experiments/          # Experiment tracking
├── tests/                # Test suite
├── reports/              # Generated reports
├── scripts/              # CLI scripts
├── docs/                 # Documentation
└── docker/               # Docker configuration
```

## Configuration

Key environment variables (see `.env.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `LLM_PROVIDER` - `groq`, `ollama`, or `claude`
- `GROQ_API_KEY` - Groq API key
- `EMBEDDING_PROVIDER` - `sentence-transformers` or `openai`
- `VECTOR_STORE_PROVIDER` - `pgvector` or `pinecone`

## Development

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy app/
```

## Docker

```bash
# Build
docker-compose -f docker/docker-compose.yml build

# Run
docker-compose -f docker/docker-compose.yml up -d
```

## License

MIT License - see LICENSE file for details.