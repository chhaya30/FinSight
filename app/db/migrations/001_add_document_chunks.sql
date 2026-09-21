-- =============================================================================
-- Migration 001: Add document_chunks table + pgvector extension
-- Run this against the Supabase PostgreSQL database once it is resumed.
-- =============================================================================

-- 1. Enable pgvector extension (requires superuser or rds_superuser on Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add FK constraint to reports.company_id that was previously missing
--    (Only run if the FK does not already exist.)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'reports_company_id_fkey'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_company_id_fkey
            FOREIGN KEY (company_id)
            REFERENCES companies(id)
            ON DELETE CASCADE;
    END IF;
END$$;

-- 3. Create document_chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    report_id      UUID        NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    company_id     UUID        NOT NULL,          -- denormalised for fast filtered search
    fiscal_year    INTEGER     NOT NULL,           -- denormalised for fast filtered search

    chunk_index    INTEGER     NOT NULL,
    chunk_hash     VARCHAR(16),                   -- first 16 hex chars of SHA-256(text)

    start_page     INTEGER,
    end_page       INTEGER,
    section_title  VARCHAR(500),

    text           TEXT        NOT NULL,
    char_count     INTEGER     NOT NULL DEFAULT 0,

    -- pgvector column: 1024-dim to match BAAI/bge-large-en-v1.5
    embedding      vector(1024),
    embedding_model VARCHAR(200),

    extra_metadata JSONB,

    CONSTRAINT uq_chunk_report_index UNIQUE (report_id, chunk_index)
);

-- 4. Indexes
CREATE INDEX IF NOT EXISTS idx_doc_chunks_report_id    ON document_chunks (report_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_company_id   ON document_chunks (company_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_fiscal_year  ON document_chunks (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_chunk_hash   ON document_chunks (chunk_hash);

-- 5. IVFFlat index for ANN similarity search (cosine distance)
--    Requires at least a few thousand rows before it becomes beneficial.
--    lists=100 is a reasonable default for <1M rows; tune as needed.
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding
    ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 6. Auto-update updated_at trigger  
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_document_chunks_updated_at ON document_chunks;
CREATE TRIGGER update_document_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
