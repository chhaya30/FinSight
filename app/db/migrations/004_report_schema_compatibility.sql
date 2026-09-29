-- Align the report metadata field with the Report ORM while preserving existing rows.
ALTER TABLE public.reports
    ADD COLUMN IF NOT EXISTS extra_metadata JSONB;

ALTER TABLE public.reports
    ALTER COLUMN extra_metadata SET DEFAULT '{}'::jsonb;
