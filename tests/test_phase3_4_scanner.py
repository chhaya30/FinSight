import pytest
from httpx import ASGITransport, AsyncClient

from app.api.main import app
from app.api.routes.industry_intelligence import get_industry_provider
from app.api.routes.market_intelligence import get_market_provider
from app.models.comparison import EvolutionChangeType, RiskEvolutionRecord
from app.api.routes.scanner import _financial_direction
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session
from app.intelligence.scanner import aggregate_score, matches_criteria
from app.intelligence.industry import NullIndustryProvider
from app.intelligence.market import NullMarketProvider
from app.models.scanner import ContributingFactor, ScannerCriterion


def test_scanner_aggregation_renormalizes_only_available_risk_dimensions():
    factors = [
        ContributingFactor(
            factor="severity", label="Severity", observed=True, value="HIGH",
            score=0.78, explanation="Stored severity.",
        ),
        ContributingFactor(
            factor="status", label="Evolution", observed=True, value="ESCALATED",
            score=0.9, explanation="Phase 2 status.",
        ),
        ContributingFactor(
            factor="financial_signal", label="Financial", observed=False,
            value="UNAVAILABLE", score=None, explanation="Unavailable.",
        ),
    ]
    score, coverage = aggregate_score(factors)
    assert score == pytest.approx((0.35 * 0.78 + 0.25 * 0.9) / 0.6)
    assert coverage == 0.4
    assert matches_criteria(
        factors,
        [
            ScannerCriterion(factor="severity", operator="gte", value=0.75),
            ScannerCriterion(factor="financial_signal", operator="observed", value=False),
        ],
        "AND",
    )
    assert not matches_criteria(
        factors,
        [ScannerCriterion(factor="financial_signal", operator="eq", value="ADVERSE")],
        "AND",
    )
    assert matches_criteria(
        factors,
        [ScannerCriterion(factor="status", operator="eq", value="ESCALATED")],
        "OR",
    )
    assert _financial_direction("debt", "INCREASED") == "ADVERSE"
    assert _financial_direction("revenue", "DECREASED") == "ADVERSE"
    assert _financial_direction("market_cap", "INCREASED") == "MIXED"


@pytest.mark.asyncio
async def test_scanner_api_evaluates_db_risk_and_reports_missing_signals(db_session):
    company = Company(name="JPMorgan Scanner API Test", sector="Financial Services")
    db_session.add(company)
    await db_session.flush()
    report = Report(company_id=company.id, fiscal_year=2025, source_file="jpm-2025.pdf")
    db_session.add(report)
    await db_session.flush()
    risk = RiskItem(
        report_id=report.id, category="Credit", severity="HIGH", confidence_score=0.88,
        summary="Commercial real estate credit exposure", source_page=44,
        source_paragraph="Commercial real estate borrowers may experience elevated losses.",
    )
    db_session.add(risk)
    await db_session.flush()

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_market_provider] = NullMarketProvider
    app.dependency_overrides[get_industry_provider] = NullIndustryProvider
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        options = await client.get("/api/v1/scanner/options")
        response = await client.post("/api/v1/scanner/run", json={
            "company_ids": [company.id], "year_current": 2025, "logic": "AND",
            "criteria": [
                {"factor": "category", "operator": "eq", "value": "Credit"},
                {"factor": "severity", "operator": "gte", "value": 0.78},
                {"factor": "classification_confidence", "operator": "gte", "value": 0.8},
                {"factor": "market_signal", "operator": "observed", "value": False},
            ],
        })
    app.dependency_overrides.clear()

    assert options.status_code == 200
    assert options.json()["factor_operators"]["financial_signal"] == ["eq", "observed"]
    assert response.status_code == 200
    body = response.json()
    assert body["total_matches"] == 1
    result = body["results"][0]
    assert result["risk_id"] == risk.id
    assert result["status"] == "UNCOMPARED"
    assert result["overall_score"] == 0.78
    assert result["coverage"] == 0.2
    assert "does not establish causation" in result["assessment"]
    by_factor = {item["factor"]: item for item in result["contributing_factors"]}
    assert by_factor["market_signal"]["observed"] is False
    assert by_factor["market_signal"]["score"] is None
    assert by_factor["industry_signal"]["observed"] is False
    assert by_factor["industry_signal"]["value"] == "UNAVAILABLE"
    assert by_factor["severity"]["evidence"][0]["document_id"] == "jpm-2025.pdf"
    assert by_factor["severity"]["evidence"][0]["page"] == 44


@pytest.mark.asyncio
async def test_scanner_consumes_external_market_and_industry_signals(db_session, monkeypatch):
    company = Company(name="JPMorgan Scanner Integration", sector="Banking")
    db_session.add(company)
    await db_session.flush()
    previous = Report(company_id=company.id, fiscal_year=2024, source_file="jpm-2024.pdf")
    current = Report(company_id=company.id, fiscal_year=2025, source_file="jpm-2025.pdf")
    db_session.add_all([previous, current])
    await db_session.flush()
    old_risk = RiskItem(report_id=previous.id, category="Cybersecurity", severity="MEDIUM",
                        confidence_score=0.8, summary="Third-party cybersecurity vendor exposure",
                        source_page=20, source_paragraph="Third-party vendors can expose customer data to cybersecurity incidents.")
    risk = RiskItem(report_id=current.id, category="Cybersecurity", severity="HIGH",
                    confidence_score=0.9, summary="Third-party cybersecurity vendor exposure increased",
                    source_page=22, source_paragraph="Third-party vendors may expose customer data through cybersecurity incidents.")
    db_session.add_all([old_risk, risk])
    await db_session.flush()
    record = RiskEvolutionRecord(
        year_1_risk_id=old_risk.id, year_2_risk_id=risk.id,
        change_type=EvolutionChangeType.MODIFIED,
        severity_prev="MEDIUM", severity_current="HIGH",
        metadata={"title_y1": old_risk.summary, "title_y2": risk.summary, "category": "Cybersecurity"},
    )

    async def compare(*_args, **_kwargs):
        return [record], [], None

    class MarketProvider:
        name = "GDELT fixture"
        def is_available(self): return True
        async def fetch_events(self, company_name, company_id):
            return [{"title": "JPMorgan third-party cybersecurity vendor exposure", "source": "External News",
                     "source_url": "https://news.example.test/jpm", "publication_date": "2025-03-01",
                     "summary": "JPMorgan cybersecurity vendors face incident risk.", "company_name": company_name}]

    class IndustryProvider:
        name = "SEC EDGAR fixture"
        def is_available(self): return True
        async def fetch_industry_data(self, company_name, industry):
            evidence = {"source": "SEC Peer Filing", "source_url": "https://sec.example.test/peer",
                        "publication_date": "2025-02-01", "excerpt": "Third-party cybersecurity vendor exposure."}
            return {"themes": [],
                    "peers": [{"company_id": "peer-cik", "name": "Peer Bank", "industry": "Banking",
                               "risk_categories": ["Cybersecurity"], "evidence": [evidence]}]}

    monkeypatch.setattr("app.api.routes.scanner.compare_report_risks", compare)
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_market_provider] = lambda: MarketProvider()
    app.dependency_overrides[get_industry_provider] = lambda: IndustryProvider()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/scanner/run", json={
            "company_ids": [company.id], "year_current": 2025, "year_previous": 2024,
        })
    app.dependency_overrides.clear()
    assert response.status_code == 200
    factors = {item["factor"]: item for item in response.json()["results"][0]["contributing_factors"]}
    assert factors["market_signal"]["value"] == "RELATED"
    assert factors["market_signal"]["evidence"][0]["source"] == "Phase 3.1 market event"
    assert factors["market_signal"]["evidence"][0]["source_url"] == "https://news.example.test/jpm"
    assert factors["industry_signal"]["value"] == "PEER_OBSERVED"
    assert factors["industry_signal"]["evidence"][0]["source"] == "Phase 3.2 peer filing"
    assert factors["industry_signal"]["evidence"][0]["source_url"] == "https://sec.example.test/peer"


@pytest.mark.asyncio
async def test_scanner_preserves_unmatched_company_news_as_context_only(db_session):
    company = Company(name="JPMorgan Scanner Context", sector="Banking")
    db_session.add(company)
    await db_session.flush()
    report = Report(company_id=company.id, fiscal_year=2025, source_file="jpm-2025.pdf")
    db_session.add(report)
    await db_session.flush()
    db_session.add(RiskItem(
        report_id=report.id, category="Credit", severity="HIGH", confidence_score=0.88,
        summary="Commercial real estate borrower defaults", source_page=44,
        source_paragraph="Commercial real estate borrowers may default.",
    ))

    class MarketProvider:
        name = "Google News RSS fixture"
        def is_available(self): return True
        async def fetch_events(self, company_name, company_id):
            return [{"title": "JPMorgan launches a new deposit product", "source": "Verified News",
                     "source_url": "https://news.example.test/jpm-deposit", "publication_date": "2025-03-01",
                     "summary": "JPMorgan announced a new deposit product.", "company_name": company_name,
                     "provider": self.name}]

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_market_provider] = lambda: MarketProvider()
    app.dependency_overrides[get_industry_provider] = NullIndustryProvider
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/scanner/run", json={
            "company_ids": [company.id], "year_current": 2025,
        })
    app.dependency_overrides.clear()
    assert response.status_code == 200
    factors = {item["factor"]: item for item in response.json()["results"][0]["contributing_factors"]}
    assert factors["market_signal"]["value"] == "CONTEXT_ONLY"
    assert factors["market_signal"]["score"] is None
    assert "none is linked to this risk" in factors["market_signal"]["explanation"]
    assert factors["market_signal"]["evidence"][0]["source_url"] == "https://news.example.test/jpm-deposit"
