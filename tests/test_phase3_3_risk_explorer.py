import pytest
from httpx import ASGITransport, AsyncClient

from app.comparison.explainability import ExplainabilityService
from app.api.main import app
from app.api.routes.industry_intelligence import get_industry_provider
from app.api.routes.market_intelligence import get_market_provider
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.models.comparison import (
    AttributeChange,
    EvolutionChangeType,
    RiskEvolutionRecord,
)
from app.models.risk import RiskEvidence


@pytest.mark.asyncio
async def test_risk_explorer_filters_and_returns_real_db_risk(db_session, monkeypatch):
    company = Company(name="JPMorgan Explorer Test", sector="Financials")
    other_company = Company(name="Other Explorer Company", sector="Technology")
    db_session.add_all([company, other_company])
    await db_session.flush()
    previous = Report(company_id=company.id, fiscal_year=2024, source_file="jpm-2024.pdf")
    current = Report(company_id=company.id, fiscal_year=2025, source_file="jpm-2025.pdf")
    db_session.add_all([previous, current])
    await db_session.flush()
    old_risk = RiskItem(
        report_id=previous.id, company_id=company.id, category="Credit", severity=4, severity_label="MEDIUM", confidence_score=0.78,
        risk_title="Credit exposure tied to commercial real estate",
        risk_summary="Credit exposure tied to commercial real estate", source_page=41,
        source_paragraph="Commercial real estate borrowers may not repay.",
    )
    removed_risk = RiskItem(
        report_id=previous.id, company_id=company.id, category="Operational", severity=2, severity_label="LOW", confidence_score=0.69,
        risk_title="Legacy branch processing exposure",
        risk_summary="Legacy branch processing exposure", source_page=58,
        source_paragraph="Legacy processing systems may cause delays.",
    )
    new_risk = RiskItem(
        report_id=current.id, company_id=company.id, category="Credit", severity=5, severity_label="HIGH", confidence_score=0.91,
        risk_title="Credit losses may rise for commercial real estate borrowers",
        risk_summary="Credit losses may rise for commercial real estate borrowers", source_page=44,
        source_paragraph="Our commercial real estate portfolio remains subject to elevated losses.",
    )
    db_session.add_all([old_risk, removed_risk, new_risk])
    await db_session.flush()
    record = RiskEvolutionRecord(
        year_1_risk_id=old_risk.id, year_2_risk_id=new_risk.id,
        report_id_prev=previous.id, report_id_current=current.id,
        report_year_prev=2024, report_year_current=2025,
        change_type=EvolutionChangeType.ESCALATED,
        match_confidence=0.91, semantic_similarity=0.88,
        severity_prev="MEDIUM", severity_current="HIGH",
        changed_attributes={"severity": AttributeChange(before="MEDIUM", after="HIGH")},
        evidence_prev=RiskEvidence(document_id="jpm-2024.pdf", report_year=2024, page=41,
                                   text=old_risk.source_paragraph),
        evidence_current=RiskEvidence(document_id="jpm-2025.pdf", report_year=2025, page=44,
                                      text=new_risk.source_paragraph),
        metadata={"title_y1": old_risk.risk_summary, "title_y2": new_risk.risk_summary,
                  "category": new_risk.category},
    )
    removed_record = RiskEvolutionRecord(
        year_1_risk_id=removed_risk.id, report_id_prev=previous.id,
        report_year_prev=2024, change_type=EvolutionChangeType.REMOVED,
        severity_prev="LOW",
        evidence_prev=RiskEvidence(document_id="jpm-2024.pdf", report_year=2024, page=58,
                                   text=removed_risk.source_paragraph),
        metadata={"title_y1": removed_risk.risk_summary, "category": removed_risk.category},
    )

    async def compare(*_args, **_kwargs):
        records = [record, removed_record]
        return records, ExplainabilityService().explain_records(records), None

    monkeypatch.setattr("app.api.routes.risk_explorer.compare_report_risks", compare)
    class MarketProvider:
        name = "GDELT deterministic fixture"
        def is_available(self): return True
        async def fetch_events(self, company_name, company_id):
            return [{"title": "JPMorgan third-party cyber incident exposure", "source": "Verified Wire",
                     "source_url": "https://news.example.test/jpm-event", "publication_date": "2025-03-01",
                     "summary": "JPMorgan third-party cyber incident exposure.", "company_name": company_name},
                    {"title": "JPMorgan expands branch network", "source": "Business Daily",
                     "source_url": "https://news.example.test/jpm-branches", "publication_date": "2025-03-02",
                     "summary": "JPMorgan opens an additional branch.", "company_name": company_name}]
    class IndustryProvider:
        name = "SEC deterministic fixture"
        def is_available(self): return True
        async def fetch_industry_data(self, company_name, industry):
            return {"themes": [{"name": "Cybersecurity vendor exposure across banks", "source": "SEC Peer 10-K",
                                "source_url": "https://sec.example.test/peer-10k", "publication_date": "2025-02-01",
                                "excerpt": "Cybersecurity vendor exposure is discussed."}], "peers": []}

    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_market_provider] = lambda: MarketProvider()
    app.dependency_overrides[get_industry_provider] = lambda: IndustryProvider()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/risk-explorer",
            params={"company_id": str(company.id), "year": 2025, "category": "Credit",
                    "severity": "HIGH", "status": "ESCALATED", "search": "commercial real estate"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["risk_id"] == new_risk.id
    assert body["items"][0]["previous_risk_id"] == old_risk.id
    assert body["items"][0]["status"] == "ESCALATED"
    assert body["items"][0]["source_document"] == "jpm-2025.pdf"
    assert {entry["name"] for entry in body["companies"]} == {
        "JPMorgan Explorer Test", "Other Explorer Company"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        removed_response = await client.get(
            f"/api/v1/risk-explorer/{removed_risk.id}", params={"year": current.fiscal_year}
        )
    app.dependency_overrides.clear()
    assert removed_response.status_code == 200
    removed_body = removed_response.json()
    assert removed_body["status"] == "REMOVED"
    assert removed_body["current_risk"] is None
    assert removed_body["previous_risk"]["evidence"]["document"] == "jpm-2024.pdf"


@pytest.mark.asyncio
async def test_risk_explorer_detail_returns_evolution_evidence_and_signals(
    db_session, monkeypatch
):
    company = Company(name="JPMorgan Explorer Detail Test", sector="Financials")
    db_session.add(company)
    await db_session.flush()
    previous = Report(company_id=company.id, fiscal_year=2024, source_file="jpm-2024.pdf")
    current = Report(company_id=company.id, fiscal_year=2025, source_file="jpm-2025.pdf")
    db_session.add_all([previous, current])
    await db_session.flush()
    old_risk = RiskItem(
        report_id=previous.id, company_id=company.id, category="Cybersecurity", severity=4, severity_label="MEDIUM", confidence_score=0.8,
        risk_title="Cybersecurity incident exposure",
        risk_summary="Cybersecurity incident exposure", source_page=19,
        source_paragraph="A cyber incident could affect customer data.",
    )
    new_risk = RiskItem(
        report_id=current.id, company_id=company.id, category="Cybersecurity", severity=5, severity_label="HIGH", confidence_score=0.93,
        risk_title="Third-party cyber incident exposure",
        risk_summary="Third-party cyber incident exposure", source_page=22,
        source_paragraph="Third-party providers may expose customer data to cyber incidents.",
    )
    db_session.add_all([old_risk, new_risk])
    await db_session.flush()
    record = RiskEvolutionRecord(
        year_1_risk_id=old_risk.id, year_2_risk_id=new_risk.id,
        report_id_prev=previous.id, report_id_current=current.id,
        report_year_prev=2024, report_year_current=2025,
        change_type=EvolutionChangeType.MODIFIED, match_confidence=0.89,
        semantic_similarity=0.86,
        changed_attributes={"severity": AttributeChange(before="MEDIUM", after="HIGH")},
        evidence_prev=RiskEvidence(document_id="jpm-2024.pdf", report_year=2024, page=19,
                                   text=old_risk.source_paragraph),
        evidence_current=RiskEvidence(document_id="jpm-2025.pdf", report_year=2025, page=22,
                                      text=new_risk.source_paragraph),
        metadata={"title_y1": old_risk.risk_summary, "title_y2": new_risk.risk_summary,
                  "category": new_risk.category},
    )

    async def compare(*_args, **_kwargs):
        return [record], ExplainabilityService().explain_records([record]), None

    monkeypatch.setattr("app.api.routes.risk_explorer.compare_report_risks", compare)
    class MarketProvider:
        name = "GDELT deterministic fixture"
        def is_available(self): return True
        async def fetch_events(self, company_name, company_id):
            return [{"title": "JPMorgan third-party cyber incident exposure", "source": "Verified Wire",
                     "source_url": "https://news.example.test/jpm-event", "publication_date": "2025-03-01",
                     "summary": "JPMorgan third-party cyber incident exposure.", "company_name": company_name},
                    {"title": "JPMorgan expands branch network", "source": "Business Daily",
                     "source_url": "https://news.example.test/jpm-branches", "publication_date": "2025-03-02",
                     "summary": "JPMorgan opens an additional branch.", "company_name": company_name}]
    class IndustryProvider:
        name = "SEC deterministic fixture"
        def is_available(self): return True
        async def fetch_industry_data(self, company_name, industry):
            return {"themes": [{"name": "Cybersecurity vendor exposure across banks", "source": "SEC Peer 10-K",
                                "source_url": "https://sec.example.test/peer-10k", "publication_date": "2025-02-01",
                                "excerpt": "Cybersecurity vendor exposure is discussed."}], "peers": []}

    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_market_provider] = lambda: MarketProvider()
    app.dependency_overrides[get_industry_provider] = lambda: IndustryProvider()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/risk-explorer/{new_risk.id}", params={"year": current.fiscal_year}
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "MODIFIED"
    assert body["current_risk"]["evidence"]["document"] == "jpm-2025.pdf"
    assert body["current_risk"]["evidence"]["page"] == 22
    assessment = body["current_risk"]["classification_assessment"]
    assert assessment["low_confidence"] is True
    assert assessment["supporting_evidence"][0]["document"] == "jpm-2025.pdf"
    assert assessment["supporting_evidence"][0]["page"] == 22
    assert body["previous_risk"]["evidence"]["year"] == 2024
    assert body["explanation"]["what_changed"][0]["name"] == "severity"
    assert body["explanation"]["business_impact"]["text"]
    assert body["explanation"]["confidence_score"] == 0.86
    assert body["market_signals"]["provider_available"] is True
    assert len(body["market_signals"]["events"]) == 2
    assert body["market_signals"]["events"][0]["source"] == "Verified Wire"
    assert body["market_signals"]["events"][0]["source_url"] == "https://news.example.test/jpm-event"
    assert body["market_signals"]["events"][1]["source_url"] == "https://news.example.test/jpm-branches"
    assert body["market_signals"]["related_risks"]
    assert body["industry_signals"]["provider_available"] is True
    assert body["industry_signals"]["themes"][0]["evidence"]["source"] == "SEC Peer 10-K"
    assert body["industry_signals"]["assessments"][0]["classification"] == "INDUSTRY_WIDE"
