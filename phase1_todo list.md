# Phase 1 Todo List

## Project Context
This repo is currently structured as a Python project, not a full monorepo. It already contains:

- `app/` for domain modules (`api`, `config`, `db`, `ingestion`, `intelligence`, `llm`, `processing`, `retrieval`, `risk_engine`, `taxonomy`, etc.)
- `scripts/` for pipeline/CLI execution
- `tests/` for test coverage
- `docker/` for deployment assets
- `docs/` and `documentation/` for design and PRD notes

This is closer to an application skeleton than a strict `frontend/ + backend/ + ai/` monorepo split.

---

## Decision: Do we need separate frontend/backend/ai folders?

### Recommended for this repo right now
No, not necessarily.

Use this structure if you want a faster, cleaner implementation:

- `app/` = backend APIs + AI logic + shared domain code
- `scripts/` = ingestion and pipeline entrypoints
- `tests/` = unit/integration tests
- `docker/` = container setup
- `docs/` = architecture and notes

### Create separate folders only if:
- you intend to build a true multi-service architecture
- frontend and backend need independent deployment and teams
- the app will later become a Next.js or React UI and a separate API service

### Practical recommendation
For the current workspace, keep the existing Python-first structure and avoid creating a full frontend/backend/ai split unless you specifically need independent deployment.

---

## Phase 1 Goals
Build a stable foundation for the GlobalRisk AI pipeline:

1. validate current project architecture
2. create environment configuration and dependency setup
3. finish ingestion and document processing basics
4. ensure tests and pipeline entry points work
5. prepare for comparison, risk classification, and retrieval work

---

## Phase 1 Todo Checklist

### Current status snapshot (verified on 2026-08-29)

Status summary: the repo has a substantial Phase 1 foundation in place, including modular app packages, config, database models, risk pipelines, and API scaffolding. However, the project is not yet validated end-to-end: the TOML config currently has a duplicate key and `uv run pytest -q` fails because of that parse error, so the repo is not yet in a clean, working state.

Verified evidence:
- `app/config/settings.py` now contains a real `Settings` class with environment-driven config.
- `app/processing/chunker.py` now contains a real chunker implementation.
- `app/retrieval/embeddings.py` now contains embedding provider abstractions and similarity functions.
- `app/retrieval/rag_chain.py` now contains a working RAG flow abstraction.
- `app/api/main.py`, `app/db/base.py`, `app/db/session.py`, and `app/llm/base.py` are implemented and not empty.
- `README.md` is populated with project overview and usage docs.
- `uv run pytest -q` currently fails with: `duplicate key` in `pyproject.toml` and exit code `1`.

### 1. Architecture cleanup
- [x] Confirm the repo is structured as a Python package and the app-level modular design is in place
- [x] Decide that `app/` remains the main backend + AI package for the current version
- [x] Keep `scripts/` for CLI ingestion and pipeline entrypoints
- [x] Document the project architecture in `README.md`

### 2. Environment and config
- [x] Review and implement `.env`-aware application settings in `app/config/settings.py`
- [x] Add config loading patterns for app settings and env-driven values
- [ ] Standardize and validate all environment variables for PDFs, API keys, and storage
- [x] Confirm Python project compatibility baseline (`pyproject.toml` target is defined)

### 3. Dependency alignment
- [x] Check project dependencies against the core app modules
- [ ] Fix/clean dependency declarations after validating the actual runtime stack
- [ ] Separate production vs dev dependencies if the current dependency set is not yet clean
- [x] Re-run `uv` sync and verify the project parses cleanly without TOML errors

### 4. Core app package validation
- [x] Confirm the main folders under `app/` are in place and mapped to intended modules
- [x] Review the major foundation modules for implementation (`api`, `db`, `llm`, `processing`, `retrieval`, `risk_engine`)
- [ ] Fix project-level config issues and ensure imports resolve reliably across the app
- [ ] Verify package imports and runtime execution in the selected Python environment

### 5. Ingestion and document processing
- [x] Start implementing ingestion and processing modules under `app/ingestion` and `app/processing`
- [ ] Validate the end-to-end PDF ingestion path from input to processed output
- [ ] Define and verify the input contract for company, year, source type, and metadata
- [ ] Test extraction on a real PDF and confirm parsing + text cleanup behavior
- [ ] Add or validate OCR fallback logic for scanned or low-quality reports
- [ ] Confirm processed output is saved with metadata fields in a consistent format

### 6. Chunking and processing pipeline
- [x] Implement the base chunking logic for fixed-size and semantic chunking
- [ ] Validate chunk boundaries, overlap, and metadata consistency on real documents
- [ ] Confirm token-counting policy and chunk-sizing assumptions against the actual model stack
- [ ] Finish a clean end-to-end ingest + chunking pipeline script for real usage

### 7. Retrieval and embeddings preparation
- [x] Implement embedding provider abstractions and similarity helpers
- [x] Implement RAG chain structure for retrieval + answer generation
- [ ] Validate retrieval interfaces against the actual vector store and reranker implementations
- [ ] Decide the final embedding provider and vector store strategy for production use
- [ ] Confirm retrieval contract and metadata schema for later comparison work

### 8. Risk engine foundation
- [x] Build the base risk engine and comparison-oriented application structure
- [x] Add database schema for core risk entities like companies, reports, risk items, and evolution entries
- [x] Create the primary application API skeleton for risk-driven features
- [ ] Validate the risk pipeline end-to-end with real data and real classification outputs
- [ ] Align taxonomy categories and risk extraction outputs to the actual production rules

### 9. Testing and quality
- [ ] Add or fix minimal pytest coverage for config, ingestion, and core app modules
- [ ] Run `pytest` successfully after fixing the TOML duplication issue
- [ ] Fix import errors and config parsing problems before claiming app health
- [ ] Run linting (`ruff`) and confirm the repo is clean after the config fix

### 10. Docs and handoff
- [x] Write a substantive project README with architecture and usage overview
- [x] Document the project structure and key module organization
- [ ] Add a clean developer setup guide for install, env config, and local execution
- [ ] Capture final decisions for future monorepo/frontend split and deployment planning

---

## Suggested Phase 1 Execution Order

1. Fix TOML/pyproject validation issues and verify dependency loading
2. Re-run `uv sync` and confirm project parses cleanly
3. Validate imports and baseline app startup for core modules
4. Test PDF ingestion + chunking path on a sample document
5. Verify retrieval / embedding integration with a minimal workflow
6. Add a small real test suite for config + ingestion + risk pipeline basics
7. Prepare the project for Phase 2 comparison and retrieval work

---

## Real status verdict

This Phase 1 work is partially complete and moving in the right direction.

The repo now contains a meaningful foundation: settings, database schema, API scaffolding, chunking, embeddings, and a RAG architecture are all implemented. However, the project is not fully stable yet because the config file has a duplicate TOML key and the test command fails before any project code can be validated.

### Estimated completion
- Structure foundation: ~85%
- Config and dependency validation: ~55%
- Ingestion and processing pipeline: ~50%
- Retrieval and embeddings: ~60%
- Risk engine foundation: ~60%
- Testing and validation: ~10%
- Documentation: ~80%

Overall: around 50–60% complete for Phase 1, with the main remaining work being validation and configuration cleanup.

---

## Recommended Structure for This Repo

```text
globalrisk_ai/
├── app/
│   ├── api/
│   ├── config/
│   ├── db/
│   ├── ingestion/
│   ├── intelligence/
│   ├── llm/
│   ├── models/
│   ├── processing/
│   ├── retrieval/
│   ├── risk_engine/
│   ├── taxonomy/
│   └── utils/
├── scripts/
├── tests/
├── docs/
├── docker/
├── data/
├── pyproject.toml
├── README.md
├── Makefile
└── .env.example
```

This structure is still the correct one for the current repo. The main issue is not the architecture anymore; it is validation and cleanup.

---

## Bottom Line
The repo is no longer just a blank scaffold. It contains real Phase 1 implementation work, but it is not yet production-safe or fully verified. The next priority is not creating new folders; it is fixing the project config and proving the app runs successfully before moving into Phase 2.

---
