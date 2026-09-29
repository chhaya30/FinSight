from datetime import date

import pytest
from app.api.routes.industry_intelligence import get_industry_intelligence
from app.intelligence.industry import IndustryIntelligenceService, NullIndustryProvider
from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.industry_intelligence import IndustryRiskCategory


class FakeIndustryProvider:
    name = "test-industry-provider"

    def __init__(self, data):
        self.data = data

    def is_available(self):
        return True

    async def fetch_industry_data(self, company_name, industry):
        return self.data


def risk_record(category: str = "Cybersecurity") -> RiskEvolutionRecord:
    return RiskEvolutionRecord(
        year_2_risk_id="risk-y2",
        change_type=EvolutionChangeType.MODIFIED,
        metadata={"title_y2": "Cybersecurity vendor exposure", "category": category},
    )


def provider_data():
    return {
        "themes": [
            {
                "name": "Cybersecurity vendor exposure",
                "source": "Banking Risk Review",
                "source_url": "https://example.com/banking-risk",
                "publication_date": "2025-02-01",
                "excerpt": "Cybersecurity risk is common across banking peers.",
                "relevance_score": 0.9,
            }
        ],
        "peers": [
            {
                "company_id": "peer-1",
                "name": "Peer Bank",
                "industry": "Banking",
                "risk_categories": ["Cybersecurity", "Liquidity"],
                "evidence": [{"source": "Peer Risk Review", "publication_date": "2025-01-01"}],
            }
        ],
    }


def test_industry_data_preserves_theme_peer_and_evidence():
    service = IndustryIntelligenceService(FakeIndustryProvider(provider_data()))

    normalized = service.normalize_data(provider_data(), "company-1", "Banking")

    assert normalized["themes"][0].industry == "Banking"
    assert normalized["themes"][0].category == IndustryRiskCategory.CYBER
    assert normalized["themes"][0].evidence.source == "Banking Risk Review"
    assert normalized["themes"][0].evidence.publication_date == date(2025, 2, 1)
    assert normalized["peers"][0].name == "Peer Bank"
    assert normalized["peers"][0].evidence[0].source == "Peer Risk Review"


def test_malformed_themes_and_peers_are_ignored():
    service = IndustryIntelligenceService(FakeIndustryProvider({}))

    normalized = service.normalize_data(
        {
            "themes": [None, {"name": "No source"}, {"source": "No name"}],
            "peers": [
                None,
                {"name": "No id"},
                {"company_id": "p", "name": "Valid", "risk_categories": [3]},
            ],
        },
        "company-1",
        "Banking",
    )

    assert normalized["themes"] == []
    assert len(normalized["peers"]) == 1
    assert normalized["peers"][0].risk_categories == []


def test_missing_industry_is_safe_and_unavailable_provider_is_explicit():
    service = IndustryIntelligenceService(NullIndustryProvider())
    assert service.provider.is_available() is False


@pytest.mark.asyncio
async def test_missing_industry_returns_limited_response():
    result = await IndustryIntelligenceService(NullIndustryProvider()).analyze_company(
        "company-1", "JPMorgan", None
    )

    assert result.industry is None
    assert result.themes == []
    assert result.provider_available is False
    assert result.error == "Company industry is unavailable"


@pytest.mark.asyncio
async def test_unavailable_provider_returns_safe_empty_result():
    result = await IndustryIntelligenceService(NullIndustryProvider()).analyze_company(
        "company-1", "JPMorgan", "Banking"
    )

    assert result.themes == []
    assert result.peers == []
    assert result.assessments == []
    assert result.provider_available is False


def test_industry_wide_requires_supported_external_theme():
    service = IndustryIntelligenceService(FakeIndustryProvider(provider_data()))
    normalized = service.normalize_data(provider_data(), "company-1", "Banking")

    assessments = service.assess_risks([risk_record()], normalized["themes"])

    assert assessments[0].classification == "INDUSTRY_WIDE"
    assert assessments[0].supporting_themes
    assert assessments[0].evidence[0].source == "Banking Risk Review"
    assert "not a causal conclusion" in assessments[0].explanation.lower()


def test_unmatched_risk_is_company_specific_only_when_themes_exist():
    service = IndustryIntelligenceService(FakeIndustryProvider(provider_data()))
    normalized = service.normalize_data(provider_data(), "company-1", "Banking")

    assessments = service.assess_risks([risk_record("Legal")], normalized["themes"])

    assert assessments[0].classification == "COMPANY_SPECIFIC"
    assert assessments[0].supporting_themes == []
    assert assessments[0].relevance_score == 0


def test_peer_comparison_uses_only_sourced_peer_categories():
    service = IndustryIntelligenceService(FakeIndustryProvider(provider_data()))
    normalized = service.normalize_data(provider_data(), "company-1", "Banking")

    comparisons = service.compare_peers([risk_record()], normalized["peers"])

    assert {item.category for item in comparisons} == {"CYBERSECURITY", "LIQUIDITY"}
    cyber = next(item for item in comparisons if item.category == "CYBERSECURITY")
    assert cyber.company_present is True
    assert cyber.peer_names == ["Peer Bank"]
    assert cyber.evidence[0].source == "Peer Risk Review"
    assert "no causation is inferred" in cyber.explanation.lower()


@pytest.mark.asyncio
async def test_industry_api_returns_safe_provider_contract(db_session):
    from app.db.base import Company

    company = Company(name="JPMorgan Industry Test", sector="Banking")
    db_session.add(company)
    await db_session.flush()

    result = await get_industry_intelligence(
        company.id, None, None, None, db_session, NullIndustryProvider()
    )

    assert result.company_id == company.id
    assert result.company_name == "JPMorgan Industry Test"
    assert result.industry == "Banking"
    assert result.provider_available is False
    assert result.themes == []