import os

import pytest


@pytest.mark.asyncio
async def test_bge_large_local_smoke():
    """Optional local smoke test; run with RUN_BGE_SMOKE=1."""
    if os.getenv("RUN_BGE_SMOKE") != "1":
        pytest.skip("Set RUN_BGE_SMOKE=1 to load the local BGE model")

    from app.retrieval.embeddings import SentenceTransformersEmbedding

    provider = SentenceTransformersEmbedding(model_name="BAAI/bge-large-en-v1.5")
    embedding = await provider.embed_query("test")

    assert len(embedding) == 1024