-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Optional: Set up any additional configuration
-- ALTER SYSTEM SET shared_preload_libraries = 'vector';