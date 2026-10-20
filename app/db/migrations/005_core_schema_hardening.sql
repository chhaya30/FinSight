-- =============================================================================
-- Migration 005: Core schema hardening - CHECK constraints, FKs, indexes, financial snapshots
-- Run this against the PostgreSQL database.
-- =============================================================================

-- 1. Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Helper function for updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =============================================================================
-- COMPANIES TABLE
-- =============================================================================

-- Add CHECK constraint for listed_exchange
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'companies_listed_exchange_check'
    ) THEN
        ALTER TABLE companies
            ADD CONSTRAINT companies_listed_exchange_check
            CHECK (listed_exchange IS NULL OR listed_exchange IN ('NSE','BSE','NYSE','NASDAQ','LSE','OTHER'));
    END IF;
END$$;

-- Ensure extra_metadata has default
ALTER TABLE companies
    ALTER COLUMN extra_metadata SET DEFAULT '{}'::jsonb;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_companies_updated_at ON companies;
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Index on workspace_id (already exists in ORM, ensure in DB)
CREATE INDEX IF NOT EXISTS idx_companies_workspace_id ON companies (workspace_id);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies (sector);
CREATE INDEX IF NOT EXISTS idx_companies_ticker_symbol ON companies (ticker_symbol);

-- =============================================================================
-- REPORTS TABLE
-- =============================================================================

-- Add CHECK constraint for report_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'reports_report_type_check'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_report_type_check
            CHECK (report_type IN ('annual_report','10-K','20-F','10-Q','SEBI_FILING','BSE_FILING','NSE_FILING','OTHER'));
    END IF;
END$$;

-- Add CHECK constraint for processing_status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'reports_processing_status_check'
    ) THEN
        ALTER TABLE reports
            ADD CONSTRAINT reports_processing_status_check
            CHECK (processing_status IN ('uploaded','queued','processing','ocr_required','processed','failed','cancelled'));
    END IF;
END$$;

-- Ensure extra_metadata has default
ALTER TABLE reports
    ALTER COLUMN extra_metadata SET DEFAULT '{}'::jsonb;

-- Add uploaded_by FK to profiles (when profiles table exists)
-- For now, just ensure the column exists (it does in ORM)
-- FK will be added in auth migration

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_reports_updated_at ON reports;
CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reports_company_id ON reports (company_id);
CREATE INDEX IF NOT EXISTS idx_reports_workspace_id ON reports (workspace_id);
CREATE INDEX IF NOT EXISTS idx_reports_fiscal_year ON reports (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_reports_processing_status ON reports (processing_status);
CREATE INDEX IF NOT EXISTS idx_reports_file_hash ON reports (file_hash);
CREATE INDEX IF NOT EXISTS idx_reports_uploaded_by ON reports (uploaded_by);

-- =============================================================================
-- REPORT_PAGES TABLE
-- =============================================================================

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_report_pages_updated_at ON report_pages;
CREATE TRIGGER update_report_pages_updated_at
    BEFORE UPDATE ON report_pages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_report_pages_report_id ON report_pages (report_id);
CREATE INDEX IF NOT EXISTS idx_report_pages_page_number ON report_pages (report_id, page_number);

-- =============================================================================
-- DOCUMENT_CHUNKS TABLE
-- =============================================================================

-- Ensure embedding column is vector(1024)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'embedding'
        AND udt_name != 'vector'
    ) THEN
        ALTER TABLE document_chunks
            ALTER COLUMN embedding TYPE vector(1024) USING NULL;
    END IF;
END$$;

-- Add company_id and fiscal_year columns for denormalized search (if missing)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'company_id'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN company_id UUID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'document_chunks' AND column_name = 'fiscal_year'
    ) THEN
        ALTER TABLE document_chunks ADD COLUMN fiscal_year INTEGER;
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_document_chunks_updated_at ON document_chunks;
CREATE TRIGGER update_document_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_doc_chunks_report_id ON document_chunks (report_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_company_id ON document_chunks (company_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_fiscal_year ON document_chunks (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_page_id ON document_chunks (page_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_chunk_index ON document_chunks (report_id, chunk_index);
CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_chunks_report_chunk ON document_chunks (report_id, chunk_index);

-- HNSW index for ANN similarity search (cosine distance)
DROP INDEX IF EXISTS idx_doc_chunks_embedding;
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- =============================================================================
-- RISK_CATEGORIES TABLE
-- =============================================================================

-- Add CHECK constraint for default_severity
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_categories_default_severity_check'
    ) THEN
        ALTER TABLE risk_categories
            ADD CONSTRAINT risk_categories_default_severity_check
            CHECK (default_severity IS NULL OR (default_severity >= 1 AND default_severity <= 5));
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_risk_categories_updated_at ON risk_categories;
CREATE TRIGGER update_risk_categories_updated_at
    BEFORE UPDATE ON risk_categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_risk_categories_name ON risk_categories (name);
CREATE INDEX IF NOT EXISTS idx_risk_categories_is_active ON risk_categories (is_active);

-- =============================================================================
-- RISK_ITEMS TABLE (mapped to 'risks' in Supabase, but we use 'risk_items')
-- =============================================================================

-- Add CHECK constraint for severity (1-5)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_severity_check'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_severity_check
            CHECK (severity >= 1 AND severity <= 5);
    END IF;
END$$;

-- Add CHECK constraint for severity_label
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_severity_label_check'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_severity_label_check
            CHECK (severity_label IS NULL OR severity_label = ANY (ARRAY['LOW','MEDIUM','HIGH','CRITICAL']));
    END IF;
END$$;

-- Add CHECK constraint for confidence_score (0-1)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_confidence_score_check'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_confidence_score_check
            CHECK (confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1));
    END IF;
END$$;

-- Add CHECK constraint for extraction_method
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_extraction_method_check'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_extraction_method_check
            CHECK (extraction_method IS NULL OR extraction_method = ANY (ARRAY['LLM','RULE','HYBRID','HUMAN']));
    END IF;
END$$;

-- Add CHECK constraint for review_status
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_review_status_check'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_review_status_check
            CHECK (review_status = ANY (ARRAY['pending','reviewed','approved','rejected']));
    END IF;
END$$;

-- Add FK to risk_categories (category_id)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_items_category_id_fkey'
    ) THEN
        ALTER TABLE risk_items
            ADD CONSTRAINT risk_items_category_id_fkey
            FOREIGN KEY (category_id)
            REFERENCES risk_categories(id)
            ON DELETE SET NULL;
    END IF;
END$$;

-- Ensure embedding column is vector(1024)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'risk_items' AND column_name = 'embedding'
        AND udt_name != 'vector'
    ) THEN
        ALTER TABLE risk_items
            ALTER COLUMN embedding TYPE vector(1024) USING NULL;
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_risk_items_updated_at ON risk_items;
CREATE TRIGGER update_risk_items_updated_at
    BEFORE UPDATE ON risk_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_risk_items_report_id ON risk_items (report_id);
CREATE INDEX IF NOT EXISTS idx_risk_items_company_id ON risk_items (company_id);
CREATE INDEX IF NOT EXISTS idx_risk_items_category_id ON risk_items (category_id);
CREATE INDEX IF NOT EXISTS idx_risk_items_category ON risk_items (category);
CREATE INDEX IF NOT EXISTS idx_risk_items_severity ON risk_items (severity);
CREATE INDEX IF NOT EXISTS idx_risk_items_review_status ON risk_items (review_status);

-- =============================================================================
-- RISK_CITATIONS TABLE
-- =============================================================================

-- Add CHECK constraint for citation_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'risk_citations_citation_type_check'
    ) THEN
        ALTER TABLE risk_citations
            ADD CONSTRAINT risk_citations_citation_type_check
            CHECK (citation_type = ANY (ARRAY['primary','supporting','contradicting']));
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_risk_citations_updated_at ON risk_citations;
CREATE TRIGGER update_risk_citations_updated_at
    BEFORE UPDATE ON risk_citations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_risk_citations_risk_id ON risk_citations (risk_id);
CREATE INDEX IF NOT EXISTS idx_risk_citations_chunk_id ON risk_citations (chunk_id);
CREATE INDEX IF NOT EXISTS idx_risk_citations_page_id ON risk_citations (page_id);

-- =============================================================================
-- RISK_ENTITIES TABLE
-- =============================================================================

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_risk_entities_updated_at ON risk_entities;
CREATE TRIGGER update_risk_entities_updated_at
    BEFORE UPDATE ON risk_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_risk_entities_risk_id ON risk_entities (risk_id);
CREATE INDEX IF NOT EXISTS idx_risk_entities_entity_type ON risk_entities (entity_type);
CREATE INDEX IF NOT EXISTS idx_risk_entities_normalized_name ON risk_entities (normalized_name);

-- =============================================================================
-- EVOLUTION_ENTRIES TABLE (keep our naming, align with Supabase risk_evolution concept)
-- =============================================================================

-- Add CHECK constraint for change_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evolution_entries_change_type_check'
    ) THEN
        ALTER TABLE evolution_entries
            ADD CONSTRAINT evolution_entries_change_type_check
            CHECK (change_type IN ('NEW','REMOVED','ESCALATED','DE-ESCALATED','MODIFIED','UNCHANGED'));
    END IF;
END$$;

-- Add FK to risk_items for risk_item_id_prev
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evolution_entries_risk_item_id_prev_fkey'
    ) THEN
        ALTER TABLE evolution_entries
            ADD CONSTRAINT evolution_entries_risk_item_id_prev_fkey
            FOREIGN KEY (risk_item_id_prev)
            REFERENCES risk_items(id)
            ON DELETE SET NULL;
    END IF;
END$$;

-- Add FK to risk_items for risk_item_id_current
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'evolution_entries_risk_item_id_current_fkey'
    ) THEN
        ALTER TABLE evolution_entries
            ADD CONSTRAINT evolution_entries_risk_item_id_current_fkey
            FOREIGN KEY (risk_item_id_current)
            REFERENCES risk_items(id)
            ON DELETE SET NULL;
    END IF;
END$$;

-- Add company_id column for easier querying (denormalized)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evolution_entries' AND column_name = 'company_id'
    ) THEN
        ALTER TABLE evolution_entries ADD COLUMN company_id UUID;
    END IF;
END$$;

-- Add previous_report_id and current_report_id for Supabase alignment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evolution_entries' AND column_name = 'previous_report_id'
    ) THEN
        ALTER TABLE evolution_entries ADD COLUMN previous_report_id UUID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evolution_entries' AND column_name = 'current_report_id'
    ) THEN
        ALTER TABLE evolution_entries ADD COLUMN current_report_id UUID;
    END IF;
END$$;

-- Add confidence_score column (from Supabase schema)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evolution_entries' AND column_name = 'confidence_score'
    ) THEN
        ALTER TABLE evolution_entries ADD COLUMN confidence_score NUMERIC;
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_evolution_entries_updated_at ON evolution_entries;
CREATE TRIGGER update_evolution_entries_updated_at
    BEFORE UPDATE ON evolution_entries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_evolution_entries_risk_item_id_prev ON evolution_entries (risk_item_id_prev);
CREATE INDEX IF NOT EXISTS idx_evolution_entries_risk_item_id_current ON evolution_entries (risk_item_id_current);
CREATE INDEX IF NOT EXISTS idx_evolution_entries_change_type ON evolution_entries (change_type);
CREATE INDEX IF NOT EXISTS idx_evolution_entries_company_id ON evolution_entries (company_id);
CREATE INDEX IF NOT EXISTS idx_evolution_entries_previous_report_id ON evolution_entries (previous_report_id);
CREATE INDEX IF NOT EXISTS idx_evolution_entries_current_report_id ON evolution_entries (current_report_id);

-- =============================================================================
-- FINANCIAL_SNAPSHOTS TABLE
-- =============================================================================

-- Add missing fields from Supabase schema
DO $$
BEGIN
    -- operating_cash_flow
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'operating_cash_flow'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN operating_cash_flow NUMERIC;
    END IF;

    -- free_cash_flow
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'free_cash_flow'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN free_cash_flow NUMERIC;
    END IF;

    -- total_debt
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'total_debt'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN total_debt NUMERIC;
    END IF;

    -- total_assets
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'total_assets'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN total_assets NUMERIC;
    END IF;

    -- total_liabilities
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'total_liabilities'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN total_liabilities NUMERIC;
    END IF;

    -- data_source
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'data_source'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN data_source VARCHAR(100);
    END IF;

    -- as_of_date (DATE, not TIMESTAMPTZ)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'as_of_date'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN as_of_date DATE;
    END IF;

    -- metadata (jsonb, NOT NULL default '{}')
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'financial_snapshots' AND column_name = 'metadata'
    ) THEN
        ALTER TABLE financial_snapshots ADD COLUMN metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
    ELSE
        ALTER TABLE financial_snapshots ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;
        ALTER TABLE financial_snapshots ALTER COLUMN metadata SET NOT NULL;
    END IF;
END$$;

-- Ensure extra_metadata has default
ALTER TABLE financial_snapshots
    ALTER COLUMN extra_metadata SET DEFAULT '{}'::jsonb;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_financial_snapshots_updated_at ON financial_snapshots;
CREATE TRIGGER update_financial_snapshots_updated_at
    BEFORE UPDATE ON financial_snapshots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_company_id ON financial_snapshots (company_id);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_fiscal_year ON financial_snapshots (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_company_year ON financial_snapshots (company_id, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_financial_snapshots_data_source ON financial_snapshots (data_source);

-- =============================================================================
-- FINANCIAL_METRICS TABLE
-- =============================================================================

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_financial_metrics_updated_at ON financial_metrics;
CREATE TRIGGER update_financial_metrics_updated_at
    BEFORE UPDATE ON financial_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_financial_metrics_company_id ON financial_metrics (company_id);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_fiscal_year ON financial_metrics (fiscal_year);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_metric_name ON financial_metrics (metric_name);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_company_year ON financial_metrics (company_id, fiscal_year);

-- =============================================================================
-- WORKSPACES TABLE
-- =============================================================================

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
CREATE TRIGGER update_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workspaces_created_by ON workspaces (created_by);

-- =============================================================================
-- SAVED_SCANS TABLE
-- =============================================================================

-- Add CHECK constraint for logic
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'saved_scans_logic_check'
    ) THEN
        ALTER TABLE saved_scans
            ADD CONSTRAINT saved_scans_logic_check
            CHECK (logic = ANY (ARRAY['AND','OR']));
    END IF;
END$$;

-- Add updated_at trigger if missing
DROP TRIGGER IF EXISTS update_saved_scans_updated_at ON saved_scans;
CREATE TRIGGER update_saved_scans_updated_at
    BEFORE UPDATE ON saved_scans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_saved_scans_workspace_id ON saved_scans (workspace_id);
CREATE INDEX IF NOT EXISTS idx_saved_scans_created_by ON saved_scans (created_by);

-- =============================================================================
-- DATA BACKFILL: Populate denormalized columns
-- =============================================================================

-- Populate document_chunks.company_id and fiscal_year from reports
UPDATE document_chunks dc
SET company_id = r.company_id,
    fiscal_year = r.fiscal_year
FROM reports r
WHERE dc.report_id = r.id
  AND (dc.company_id IS NULL OR dc.fiscal_year IS NULL);

-- Populate evolution_entries.company_id, previous_report_id, current_report_id
UPDATE evolution_entries ee
SET company_id = ri.company_id,
    previous_report_id = ri.report_id
FROM risk_items ri
WHERE ee.risk_item_id_prev = ri.id
  AND (ee.company_id IS NULL OR ee.previous_report_id IS NULL);

UPDATE evolution_entries ee
SET company_id = ri.company_id,
    current_report_id = ri.report_id
FROM risk_items ri
WHERE ee.risk_item_id_current = ri.id
  AND (ee.company_id IS NULL OR ee.current_report_id IS NULL);

-- =============================================================================
-- FINAL VERIFICATION
-- =============================================================================

-- Verify all tables have the expected columns
SELECT 'companies' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'companies'
ORDER BY ordinal_position;

SELECT 'reports' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'reports'
ORDER BY ordinal_position;

SELECT 'risk_items' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'risk_items'
ORDER BY ordinal_position;

SELECT 'evolution_entries' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'evolution_entries'
ORDER BY ordinal_position;

SELECT 'financial_snapshots' as table_name, column_name, data_type
FROM information_schema.columns
WHERE table_name = 'financial_snapshots'
ORDER BY ordinal_position;