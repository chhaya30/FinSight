# AUDIT_02_DATABASE_STATUS.md

## Database Status

### Verdict
**NOT PRESENT**

### Database Technology
PostgreSQL 14+ with pgvector extension (configured in code, not running)

### Connection
**FAIL**

**Evidence**: 
- Connection string: `postgresql+asyncpg://postgres:postgres@localhost:5432/globalrisk`
- Error: `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "postgres"`
- No PostgreSQL service detected on localhost:5432

### Schema
**PARTIAL**

**Evidence**:
- SQLAlchemy models defined in `app/db/base.py` (7 tables)
- Models include: Company, Report, RiskItem, EvolutionEntry, FinancialSnapshot, Workspace, SavedScan
- All models use UUID primary keys, timestamps, proper indexes
- No Alembic migrations exist (`app/db/migrations/` only contains `__init__.py`)

### Migrations
**NOT PRESENT**

**Evidence**:
- `app/db/migrations/__init__.py` exists (0 bytes)
- No migration scripts (`versions/` directory missing)
- `alembic.ini` not found in project root
- Models use `Base.metadata.create_all()` in `session.py:56-60` for auto-creation

### Persistent Data
**EMPTY**

**Evidence**:
- Database not accessible, so no persistent data exists
- `scripts/seed_demo_data.py` exists to populate demo data but never run successfully
- Sample PDF reports exist in `Phase1_2/annual_reports/` but not ingested

### Tables Found

| Table | Exists in Code | Exists in DB | Used by Application | Records | Status |
|-------|---------------|--------------|---------------------|---------|--------|
| companies | Yes (app/db/base.py:37) | No (DB down) | Yes (companies.py routes) | 0 | NOT CREATED |
| reports | Yes (app/db/base.py:51) | No (DB down) | Yes (documents.py, analysis.py) | 0 | NOT CREATED |
| risk_items | Yes (app/db/base.py:76) | No (DB down) | Yes (analysis.py, risks.py) | 0 | NOT CREATED |
| evolution_entries | Yes (app/db/base.py:97) | No (DB down) | Yes (comparison.py) | 0 | NOT CREATED |
| financial_snapshots | Yes (app/db/base.py:119) | No (DB down) | Yes (reports.py) | 0 | NOT CREATED |
| workspaces | Yes (app/db/base.py:142) | No (DB down) | Partial (company model) | 0 | NOT CREATED |
| saved_scans | Yes (app/db/base.py:153) | No (DB down) | No (not wired in routes) | 0 | NOT CREATED |

### Environment Variables

| Variable | Referenced | Configured | Status |
|----------|------------|------------|--------|
| DATABASE_URL | Yes (settings.py:24) | Yes (default in .env.example) | FAIL - DB not running |
| DATABASE_POOL_SIZE | Yes (settings.py:28) | Yes (default: 10) | N/A |
| DATABASE_MAX_OVERFLOW | Yes (settings.py:29) | Yes (default: 20) | N/A |
| REDIS_URL | Yes (settings.py:31) | Yes (default) | UNKNOWN - Redis not tested |
| GROQ_API_KEY | Yes (settings.py:40) | No (placeholder in .env.example) | MISSING |
| OPENAI_API_KEY | Yes (settings.py:53) | No (placeholder in .env.example) | MISSING |
| PINECONE_API_KEY | Yes (settings.py:59) | No (placeholder in .env.example) | MISSING |
| SECRET_KEY | Yes (settings.py:82) | Yes (dev default) | WEAK - Default value |

### Evidence

**Files**:
- `app/config/settings.py` - Database configuration (lines 24-29)
- `app/db/session.py` - Connection management (lines 15-30)
- `app/db/base.py` - Schema definitions (lines 37-163)
- `app/db/migrations/__init__.py` - Empty migrations directory
- `scripts/seed_demo_data.py` - Data seeding script (never executed)
- `.env.example` - Environment template (no actual .env file)

**Runtime**:
- Backend startup fails at `init_db()` in `app/api/main.py:22`
- Health check endpoint `/api/v1/health/db` would return "unhealthy" (health.py:28-29)

### Problems

1. **PostgreSQL not running** - No database server accessible at localhost:5432
2. **No .env file** - Using defaults from settings.py, no actual configuration
3. **Missing GROQ_API_KEY** - LLM provider cannot function
4. **No migrations** - Schema changes cannot be tracked or deployed
5. **No pgvector extension** - Even if PG runs, vector search won't work without extension
6. **Default credentials** - Using `postgres:postgres` which is insecure
7. **Redis not verified** - Caching layer untested

### Recommended Action

1. **Immediate**: Install and start PostgreSQL 14+ with pgvector extension
2. **Immediate**: Create `.env` file from `.env.example` with real credentials
3. **Immediate**: Set `GROQ_API_KEY` (or configure Ollama/Claude)
4. **Immediate**: Run `alembic init migrations` and create initial migration
5. **Short-term**: Configure Docker Compose for local development (PostgreSQL + Redis)
6. **Short-term**: Run `seed_demo_data.py` to populate initial data
7. **Short-term**: Test ingestion pipeline with sample PDFs in `Phase1_2/annual_reports/`