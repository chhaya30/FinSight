from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.llm.base import BaseLLMProvider, LLMMessage
from app.llm.provider_factory import get_default_llm
from app.retrieval.embeddings import EmbeddingProvider, create_embedding_provider
from app.retrieval.reranker import BaseReranker, create_reranker
from app.retrieval.vector_store import VectorDocument, VectorStore, create_vector_store

logger = get_logger(__name__)


@dataclass
class RAGResult:
    answer: str
    sources: list[dict[str, Any]]
    query: str
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RAGChain:
    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: BaseLLMProvider | None = None,
        reranker: BaseReranker | None = None,
        top_k: int = 5,
        rerank_top_k: int = 20,
    ):
        self.vector_store = vector_store or create_vector_store("memory")
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.llm_provider = llm_provider or get_default_llm()
        self.reranker = reranker or create_reranker("heuristic")
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k

    async def add_documents(self, documents: list[VectorDocument]) -> None:
        await self.vector_store.add_documents(documents)

    async def query(
        self,
        question: str,
        filter: dict[str, Any] | None = None,
        use_reranker: bool = True,
    ) -> RAGResult:
        query_embedding = await self.embedding_provider.embed_query(question)

        results = await self.vector_store.search(
            query_embedding,
            top_k=self.rerank_top_k if use_reranker else self.top_k,
            filter=filter,
        )

        if use_reranker and results:
            results = await self.reranker.rerank(question, results, top_k=self.top_k)
        else:
            results = results[: self.top_k]

        context = self._build_context(results)
        answer = await self._generate_answer(question, context)

        return RAGResult(
            answer=answer,
            sources=results,
            query=question,
            metadata={
                "num_sources": len(results),
                "used_reranker": use_reranker,
            },
        )

    async def query_stream(
        self,
        question: str,
        filter: dict[str, Any] | None = None,
        use_reranker: bool = True,
    ) -> AsyncGenerator[str, None]:
        query_embedding = await self.embedding_provider.embed_query(question)

        results = await self.vector_store.search(
            query_embedding,
            top_k=self.rerank_top_k if use_reranker else self.top_k,
            filter=filter,
        )

        if use_reranker and results:
            results = await self.reranker.rerank(question, results, top_k=self.top_k)
        else:
            results = results[: self.top_k]

        context = self._build_context(results)

        async for chunk in self._generate_answer_stream(question, context):
            yield chunk

    def _build_context(self, results: list[dict[str, Any]]) -> str:
        context_parts = []
        for i, result in enumerate(results):
            source_info = f"[Source {i + 1}]"
            if "metadata" in result:
                meta = result["metadata"]
                if "source_page" in meta:
                    source_info += f" (Page {meta['source_page']})"
                if "company" in meta:
                    source_info += f" ({meta['company']})"

            context_parts.append(f"{source_info}\n{result['text']}")

        return "\n\n---\n\n".join(context_parts)

    async def _generate_answer(self, question: str, context: str) -> str:
        system_prompt = (
            "You are an expert risk analyst. Answer the question based ONLY "
            "on the provided context. If the context doesn't contain enough "
            "information, say so. Always cite your sources using [Source X] format."
        )

        user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm_provider.generate(messages)
        return response.content

    async def _generate_answer_stream(
        self,
        question: str,
        context: str,
    ) -> AsyncGenerator[str, None]:
        system_prompt = (
            "You are an expert risk analyst. Answer the question based ONLY "
            "on the provided context. If the context doesn't contain enough "
            "information, say so. Always cite your sources using [Source X] format."
        )

        user_prompt = f"""Context:
{context}

Question: {question}

Answer:"""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        async for chunk in self.llm_provider.generate_stream(messages):
            yield chunk


class RiskRAGChain(RAGChain):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def query_risk_evolution(
        self,
        company_id: str,
        year_current: int,
        year_previous: int,
    ) -> RAGResult:
        question = (
            f"Compare risk disclosures for company {company_id} between "
            f"FY{year_previous} and FY{year_current}. "
            "What are the new risks, removed risks, and severity changes?"
        )

        filter = {
            "company_id": company_id,
            "year": [year_previous, year_current],
        }

        return await self.query(question, filter=filter, use_reranker=True)

    async def query_risk_explorer(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> RAGResult:
        return await self.query(query, filter=filters, use_reranker=True)


def create_rag_chain(**kwargs) -> RAGChain:
    return RAGChain(**kwargs)


def create_risk_rag_chain(**kwargs) -> RiskRAGChain:
    return RiskRAGChain(**kwargs)
