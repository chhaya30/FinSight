from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.db.session import Database
from app.ingestion import create_adaptive_fallback_router
from app.llm import get_default_llm
from app.processing import create_chunker
from app.retrieval import create_rag_chain, create_risk_rag_chain
from app.risk_engine import create_pipeline
from app.taxonomy import get_taxonomy


@lru_cache
def get_settings_cached() -> Settings:
    return get_settings()


def get_database() -> Database:
    from app.db.session import db

    return db


def get_fallback_router():
    return create_adaptive_fallback_router()


def get_chunker():
    return create_chunker()


def get_risk_pipeline():
    return create_pipeline()


def get_llm():
    return get_default_llm()


def get_taxonomy_cached():
    return get_taxonomy()


def get_rag_chain():
    return create_rag_chain()


def get_risk_rag_chain():
    return create_risk_rag_chain()
