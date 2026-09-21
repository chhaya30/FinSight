-- Change only the existing document_chunks embedding column to match BAAI/bge-large-en-v1.5.
-- Preconditions verified before execution: public.document_chunks exists and contains zero rows.
-- The existing HNSW index is dropped and recreated with the same name and operator class.

DROP INDEX IF EXISTS public.idx_document_chunks_embedding;

ALTER TABLE public.document_chunks
    ALTER COLUMN embedding TYPE vector(1024)
    USING NULL;

CREATE INDEX idx_document_chunks_embedding
    ON public.document_chunks
    USING hnsw (embedding vector_cosine_ops);