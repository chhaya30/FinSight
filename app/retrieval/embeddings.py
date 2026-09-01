from abc import ABC, abstractmethod

import numpy as np

from app.config.logging import get_logger
from app.config.settings import get_settings

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        pass


class SentenceTransformersEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                logger.info("embedding_model_loaded", model=self.model_name)
            except ImportError:
                logger.error("sentence_transformers_not_installed")
                raise
            except Exception as e:
                logger.error("embedding_model_load_failed", error=str(e))
                raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._load_model()
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    async def embed_query(self, text: str) -> list[float]:
        self._load_model()
        embedding = self._model.encode([text], convert_to_numpy=True, show_progress_bar=False)
        return embedding[0].tolist()

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model_name


class OpenAIEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str = "text-embedding-3-large", api_key: str | None = None):
        settings = get_settings()
        self.model_name = model_name
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.dimension = 3072 if "3-large" in model_name else 1536
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                logger.error("openai_not_installed")
                raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._get_client()
        try:
            response = await self._client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            logger.error("openai_embedding_error", error=str(e))
            raise

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model_name


def create_embedding_provider(provider: str | None = None, **kwargs) -> EmbeddingProvider:
    settings = get_settings()
    provider_name = provider or settings.EMBEDDING_PROVIDER

    if provider_name == "sentence-transformers":
        return SentenceTransformersEmbedding(**kwargs)
    elif provider_name == "openai":
        return OpenAIEmbedding(**kwargs)
    else:
        raise ValueError(f"Unknown embedding provider: {provider_name}")


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def batch_cosine_similarity(query: list[float], candidates: list[list[float]]) -> list[float]:
    query_arr = np.array(query)
    candidates_arr = np.array(candidates)

    query_norm = np.linalg.norm(query_arr)
    candidate_norms = np.linalg.norm(candidates_arr, axis=1)

    similarities = np.dot(candidates_arr, query_arr) / (candidate_norms * query_norm + 1e-8)
    return similarities.tolist()
