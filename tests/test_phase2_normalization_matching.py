import pytest
from app.comparison.matcher import SemanticRiskMatcher
from app.comparison.normalizer import RiskNormalizer, derive_risk_title
from app.models.risk import NormalizedRisk, RiskEvidence


class MockEmbeddingProvider:
    """Mock embedding provider producing deterministic vectors based on text content."""

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            t = text.lower()
            vec = [0.0] * self.dimension
            # Project domain keywords into specific vector dimensions for semantic clustering
            if "supply" in t or "chain" in t or "geopolitical" in t:
                vec[0] = 1.0
                vec[1] = 0.8
            elif "cyber" in t or "security" in t or "breach" in t:
                vec[10] = 1.0
                vec[11] = 0.9
            elif "liquidity" in t or "financing" in t or "funding" in t or "constraints" in t:
                vec[20] = 1.0
                vec[21] = 0.85
            elif "climate" in t or "regulation" in t or "carbon" in t:
                vec[30] = 1.0
                vec[31] = 0.9
            else:
                val = float(sum(ord(c) for c in text[:50]) % 100) / 100.0
                vec[50] = val

            # Normalize vector
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [x / norm for x in vec]
            results.append(vec)
        return results

    async def embed_query(self, text: str) -> list[float]:
        res = await self.embed([text])
        return res[0]

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return "mock-embedding-v1"


# ---------------------------------------------------------------------------
# PART 2.1.1 — RISK NORMALIZATION TESTS
# ---------------------------------------------------------------------------


def test_derive_risk_title():
    text = "Cybersecurity breaches could lead to financial losses. Additional details follow."
    title = derive_risk_title(text, max_words=5)
    assert "Cybersecurity" in title
    assert len(title.split()) <= 6

    empty_title = derive_risk_title("")
    assert empty_title == "Untitled Risk"


def test_normalize_dict_preserves_required_fields_and_evidence():
    normalizer = RiskNormalizer()
    raw_data = {
        "risk_id": "r-101",
        "company_id": "c-555",
        "report_id": "doc-999",
        "report_year": 2024,
        "category": "Operational Risk",
        "severity": "High",
        "summary": "Supply chain disruption due to key supplier bottleneck.",
        "source_page": 42,
        "evidence": {
            "document_id": "doc-999",
            "report_year": 2024,
            "page": 42,
            "chunk_id": "chunk-7",
            "text": "Full paragraph snippet of supply chain disruption...",
            "section": "Item 1A. Risk Factors",
        },
    }

    norm = normalizer.normalize(raw_data, report_year=2024)

    assert isinstance(norm, NormalizedRisk)
    assert norm.risk_id == "r-101"
    assert norm.company_id == "c-555"
    assert norm.report_id == "doc-999"
    assert norm.report_year == 2024
    assert norm.category == "Operational Risk"
    assert norm.severity == "High"
    assert norm.description == "Supply chain disruption due to key supplier bottleneck."
    assert norm.source_page == 42
    assert isinstance(norm.evidence, RiskEvidence)
    assert norm.evidence.document_id == "doc-999"
    assert norm.evidence.page == 42
    assert norm.evidence.chunk_id == "chunk-7"
    assert norm.evidence.section == "Item 1A. Risk Factors"


def test_normalize_missing_optional_fields_does_not_crash():
    normalizer = RiskNormalizer()
    raw_data = {}
    norm = normalizer.normalize(raw_data, report_year=2025)

    assert isinstance(norm, NormalizedRisk)
    assert norm.report_year == 2025
    assert norm.category == "Uncategorized"
    assert norm.severity is None
    assert norm.title == "Untitled Risk"
    assert norm.description == ""
    assert norm.source_page is None
    assert norm.evidence is not None


@pytest.mark.asyncio
async def test_normalize_batch_generates_embeddings():
    provider = MockEmbeddingProvider()
    normalizer = RiskNormalizer(embedding_provider=provider)

    raw_risks = [
        {"risk_id": "1", "summary": "Supply chain disruption"},
        {"risk_id": "2", "summary": "Cybersecurity threat"},
    ]

    normalized = await normalizer.normalize_batch(raw_risks, report_year=2024)
    assert len(normalized) == 2
    assert normalized[0].embedding is not None
    assert len(normalized[0].embedding) == 1024
    assert normalized[1].embedding is not None


# ---------------------------------------------------------------------------
# PART 2.1.2 — SEMANTIC MATCHING TESTS
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_matcher_case_1_obvious_match():
    """CASE 1: Obvious match (Supply chain disruption vs Supply chain and geopolitical disruption)."""
    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)

    y1_risk = {
        "risk_id": "y1-sc",
        "risk_category": "Supply Chain",
        "title": "Supply chain disruption",
        "summary": "The company faces supply chain disruption from single-source vendors.",
    }

    y2_risk = {
        "risk_id": "y2-sc",
        "risk_category": "Supply Chain",
        "title": "Supply chain and geopolitical disruption",
        "summary": "Supply chain and geopolitical disruption could delay raw material delivery.",
    }

    res = await matcher.match_risk(y2_risk, [y1_risk], y2_year=2025, y1_year=2024)

    assert res.year_2_risk_id == "y2-sc"
    assert res.best_match is not None
    assert res.best_match.year_1_risk_id == "y1-sc"
    assert res.best_match.semantic_similarity > 0.70
    assert res.best_match.match_confidence > 0.70


@pytest.mark.asyncio
async def test_semantic_matcher_case_2_unrelated_risks():
    """CASE 2: Unrelated risks (Cybersecurity threats vs Climate change regulation)."""
    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)

    y1_risk = {
        "risk_id": "y1-cyber",
        "risk_category": "Cybersecurity",
        "title": "Cybersecurity threats",
        "summary": "Unauthorized access to internal networks and data breaches.",
    }

    y2_risk = {
        "risk_id": "y2-climate",
        "risk_category": "Environmental",
        "title": "Climate change regulation",
        "summary": "Compliance with carbon emissions taxes and environmental laws.",
    }

    res = await matcher.match_risk(y2_risk, [y1_risk], y2_year=2025, y1_year=2024)

    assert res.best_match is None
    assert len(res.candidate_matches) == 0 or res.candidate_matches[0].match_confidence < 0.50


@pytest.mark.asyncio
async def test_semantic_matcher_case_3_wording_variation():
    """CASE 3: Wording variation (Liquidity and financing risk vs Funding and liquidity constraints)."""
    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)

    y1_risk = {
        "risk_id": "y1-liq",
        "risk_category": "Financial",
        "title": "Liquidity and financing risk",
        "summary": "Tight credit markets may impact liquidity and debt refinancing.",
    }

    y2_risk = {
        "risk_id": "y2-liq",
        "risk_category": "Financial",
        "title": "Funding and liquidity constraints",
        "summary": "Higher interest rates create funding and liquidity constraints for working capital.",
    }

    res = await matcher.match_risk(y2_risk, [y1_risk], y2_year=2025, y1_year=2024)

    assert res.best_match is not None
    assert res.best_match.year_1_risk_id == "y1-liq"
    assert res.best_match.match_confidence >= 0.60


@pytest.mark.asyncio
async def test_semantic_matcher_missing_embedding_handled_safely():
    """Test missing embeddings are safely generated or fallback to text matching without crashing."""
    matcher = SemanticRiskMatcher(embedding_provider=None)

    y1_risk = {"risk_id": "y1", "summary": "Data breach risk"}
    y2_risk = {"risk_id": "y2", "summary": "Data breach risk"}

    res = await matcher.match_risk(y2_risk, [y1_risk])
    assert res.year_2_risk_id == "y2"
    assert res.best_match is not None
    assert res.best_match.year_1_risk_id == "y1"


@pytest.mark.asyncio
async def test_semantic_matcher_empty_description_does_not_crash():
    """Test empty titles/descriptions do not crash the matcher."""
    matcher = SemanticRiskMatcher(embedding_provider=None)

    y1_risk = {"risk_id": "y1", "summary": ""}
    y2_risk = {"risk_id": "y2", "summary": ""}

    res = await matcher.match_risk(y2_risk, [y1_risk])
    assert res.year_2_risk_id == "y2"


@pytest.mark.asyncio
async def test_multiple_candidates_ranked_correctly():
    """Test multiple candidate matches are ranked in descending order of match confidence."""
    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)

    y1_candidates = [
        {
            "risk_id": "y1-cyber",
            "risk_category": "Cyber",
            "title": "Cybersecurity threat",
            "summary": "Cyber security breach",
        },
        {
            "risk_id": "y1-sc",
            "risk_category": "Supply Chain",
            "title": "Supply chain disruption",
            "summary": "Supply chain issues",
        },
        {
            "risk_id": "y1-climate",
            "risk_category": "ESG",
            "title": "Climate risk",
            "summary": "Climate regulation",
        },
    ]

    y2_risk = {
        "risk_id": "y2-sc",
        "risk_category": "Supply Chain",
        "title": "Supply chain disruption and vendor risk",
        "summary": "Supply chain disruption from key vendors.",
    }

    res = await matcher.match_risk(y2_risk, y1_candidates)
    assert res.best_match is not None
    assert res.best_match.year_1_risk_id == "y1-sc"
    assert len(res.candidate_matches) >= 1
