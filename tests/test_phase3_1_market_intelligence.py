from datetime import date

import pytest
from app.api.routes.market_intelligence import get_market_intelligence
from app.intelligence.market import MarketIntelligenceService, NullMarketProvider
from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.models.market_intelligence import MarketRiskCategory
from app.models.risk import RiskEvidence


class FakeProvider:
    name = "test-provider"

    def __init__(self, events):
        self.events = events

    def is_available(self):
        return True

    async def fetch_events(self, company_name, company_id):
        return self.events


def risk_record() -> RiskEvolutionRecord:
    return RiskEvolutionRecord(
        year_1_risk_id="risk-y1",
        year_2_risk_id="risk-y2",
        change_type=EvolutionChangeType.MODIFIED,
        metadata={"title_y2": "Debt refinancing pressure"},
        evidence_current=RiskEvidence(
            document_id="report-2025", report_year=2025, page=40, text="Debt risk disclosure"
        ),
    )


def test_market_event_schema_preserves_source_and_date():
    service = MarketIntelligenceService(FakeProvider([]))
    events = service.normalize_events(
        [
            {
                "title": "Regulator opens review",
                "source": "Example Wire",
                "source_url": "https://example.com/event",
                "publication_date": "2025-03-04T12:00:00Z",
                "summary": "A regulatory compliance review was announced.",
                "company_name": "JPMorgan",
            }
        ],
        "company-1",
    )

    assert len(events) == 1
    assert events[0].company_id == "company-1"
    assert events[0].publication_date == date(2025, 3, 4)
    assert events[0].category == MarketRiskCategory.REGULATORY
    assert events[0].evidence.source == "Example Wire"
    assert str(events[0].source_url) == "https://example.com/event"
    assert events[0].relevance_score > 0


def test_invalid_or_incomplete_events_are_skipped():
    service = MarketIntelligenceService(FakeProvider([]))

    events = service.normalize_events(
        [
            None,
            {"title": "Missing source"},
            {"source": "Source only"},
            {"title": "Bad date", "source": "Source", "publication_date": "not-a-date"},
        ],
        "company-1",
    )

    assert len(events) == 1
    assert events[0].publication_date is None


def test_empty_provider_is_safe_and_distinguishes_unavailable_data():
    assert NullMarketProvider().is_available() is False


@pytest.mark.asyncio
async def test_empty_provider_response_is_explicitly_unavailable():
    response = await MarketIntelligenceService(NullMarketProvider()).fetch_for_company(
        "company-1", "JPMorgan"
    )

    assert response.events == []
    assert response.related_risks == []
    assert response.provider == "unconfigured"
    assert response.provider_available is False
    assert response.error is None


def test_risk_correlation_is_term_based_and_non_causal():
    service = MarketIntelligenceService(FakeProvider([]))
    event = service.normalize_events(
        [
            {
                "title": "Debt refinancing review",
                "source": "Wire",
                "summary": "Credit funding update",
            }
        ],
        "company-1",
    )[0]

    related = service.correlate_risks([event], [risk_record()])

    assert len(related) == 1
    assert related[0].risk_item_id_current == "risk-y2"
    assert related[0].relationship == "SUPPORTED_TERM_OVERLAP"
    assert "not causation" in related[0].explanation
    assert related[0].evidence[0].source == "Wire"


def test_unrelated_event_does_not_correlate():
    service = MarketIntelligenceService(FakeProvider([]))
    event = service.normalize_events(
        [{"title": "Community arts program", "source": "Wire", "summary": "Local event"}],
        "company-1",
    )[0]

    assert service.correlate_risks([event], [risk_record()]) == []


@pytest.mark.asyncio
async def test_market_api_returns_provider_safe_contract(db_session):
    from app.db.base import Company

    company = Company(name="JPMorgan Test", sector="Banking")
    db_session.add(company)
    await db_session.flush()

    response = await get_market_intelligence(
        company.id, None, None, db_session, NullMarketProvider()
    )

    assert response.company_id == company.id
    assert response.company_name == "JPMorgan Test"
    assert response.events == []
    assert response.provider_available is False