-- Ensure the company metadata column exists for the Company ORM and Phase 3 APIs.
-- Safe to apply where the column was already added manually.
ALTER TABLE public.companies
    ADD COLUMN IF NOT EXISTS extra_metadata JSONB;

ALTER TABLE public.companies
    ALTER COLUMN extra_metadata SET DEFAULT '{}'::jsonb;
