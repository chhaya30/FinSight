# Architecture

## System Overview

GlobalRisk AI follows a modular, layered architecture designed for scalability, maintainability, and testability.

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│  Health │ Documents │ Analysis │ Companies │ Risks │ Comparison │
├─────────────────────────────────────────────────────────────────┤
│                      Service / Business Logic                   │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│Ingestion │Processing│ Taxonomy │Risk Engine│   LLM    │Retrieval │
├──────────┴──────────┴──────────┴──────────┴──────────┴──────────┤
│                        Data Access Layer                        │
│                   (SQLAlchemy + PostgreSQL)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Ingestion Layer (`app/ingestion/`)
- **PDF Loader**: Uses PyMuPDF (primary) and pdfplumber (fallback)
- **Extractors**: Modular extractor interface with factory pattern
- **OCR**: Tesseract-based OCR with adaptive fallback routing

### 2. Processing Layer (`app/processing/`)
- **Cleaner**: Header/footer removal, whitespace normalization
- **Normalizer**: Currency, number, date, and sector-term normalization
- **Section Detector**: Hierarchical document section detection
- **Risk Section Detector**: Specialized risk factor section finder
- **Metadata Extractor**: Company, year, financial highlights extraction
- **Chunker**: Fixed-size and semantic chunking strategies

### 3. Taxonomy Layer (`app/taxonomy/`)
- **Loader**: JSON-based risk taxonomy with 18 categories
- **Validator**: Consistency validation and risk item validation
- **Classifier Rules**: Rule-based category and severity classification

### 4. Risk Engine (`app/risk_engine/`)
- **Detector**: Identifies risk-bearing text segments
- **Extractor**: Extracts structured risk information
- **Classifier**: Refines category and severity assignments
- **Severity Assessor**: Determines risk severity levels
- **Confidence Calculator**: Computes calibrated confidence scores
- **Deduplicator**: Removes duplicate/near-duplicate risks
- **Evidence Builder**: Links risks to source text with citations
- **Pipeline**: Orchestrates the full extraction workflow

### 5. LLM Abstraction (`app/llm/`)
- **Base Provider**: Common interface for all LLM providers
- **Providers**: Groq, Ollama, Claude implementations
- **Prompt Templates**: Risk extraction, classification, comparison

### 6. Retrieval Layer (`app/retrieval/`)
- **Embeddings**: Sentence Transformers and OpenAI embeddings
- **BM25**: Lexical search with configurable parameters
- **Dense Retriever**: Vector similarity search
- **Hybrid Retriever**: Weighted combination of BM25 + dense
- **RRF**: Reciprocal Rank Fusion for result merging
- **Reranker**: Cross-encoder and LLM-based reranking
- **Vector Store**: In-memory, pgvector, and Pinecone backends
- **RAG Chain**: End-to-end retrieval-augmented generation

### 6. Comparison (`app/comparison/`)
- **Matcher**: Semantic risk matching across years
- **Similarity**: Cosine similarity with configurable thresholds
- **Delta**: NEW/REMOVED/SEVERITY_UP/SEVERITY_DOWN/MODIFIED detection
- **Evolution**: Risk evolution tracking and narrative generation

### 7. Intelligence (`app/intelligence/`)
- **Company Profile**: Business description, key products, executives
- **Financial Analysis**: Metrics, trends, risk-financial correlation
- **Peer Comparison**: Sector benchmarking and ranking
- **Industry Analysis**: Sector heatmaps and emerging risks
- **Risk Explorer**: Multi-factor semantic screening
- **News Analysis**: Sentiment and event correlation

## Data Flow

### Document Ingestion
```
PDF Upload → OCR/Extraction → Cleaning → Normalization → Section Detection → Chunking
```

### Risk Extraction
```
Chunks → Risk Detector → Risk Extractor → Classifier → Severity → Confidence → Deduplication → Evidence
```

### Year-over-Year Comparison
```
Year N Risks ↔ Year N-1 Risks → Semantic Matching → Delta Detection → Evolution Summary
```

## Database Schema

### Core Tables
- **companies**: Company metadata (name, sector, market cap, exchange)
- **reports**: Annual report metadata (company, year, status, file info)
- **risk_items**: Extracted risks (category, severity, confidence, summary, source)
- **evolution_entries**: Year-over-year risk changes (type, similarity, severity change)
- **financial_snapshots**: Financial metrics per company per year
- **workspaces**: Multi-user workspace isolation
- **saved_scans**: User-defined risk screening queries

## Configuration

All configuration via Pydantic Settings (`app/config/settings.py`) with environment variable support.

Key settings:
- `LLM_PROVIDER`: groq, ollama, claude
- `EMBEDDING_PROVIDER`: sentence-transformers, openai
- `VECTOR_STORE_PROVIDER`: pgvector, pinecone
- `CHUNK_SIZE` / `CHUNK_OVERLAP`: Text chunking parameters
- `OCR_ENABLED`: Tesseract OCR toggle

## Deployment

Docker Compose for local development and production:
- API service (FastAPI + Uvicorn)
- PostgreSQL with pgvector
- Redis (caching)
- Optional: Ollama for local LLM inference

## Testing Strategy

- Unit tests for each module (`tests/`)
- Integration tests for API endpoints
- Pipeline evaluation scripts (`scripts/evaluate_pipeline.py`)
- Experiment tracking (`experiments/`)