"""Tests for empty state handling across all API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4
from sqlalchemy import select

from app.api.main import app
from app.db.base import Company, Report, RiskItem, FinancialSnapshot
from app.db.session import get_db_session
from app.models.intelligence import ExecutiveSummaryRequest


def _str_id(uuid_obj):
    """Convert UUID to string for API calls."""
    return str(uuid_obj)


@pytest.mark.asyncio
async def test_risk_explorer_empty_state(db_session):
    """Test risk explorer returns proper empty state when no risks exist."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        # Create company with no reports/risks
        company = Company(name="Empty Risk Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/risk-explorer",
                params={"company_id": _str_id(company.id)},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["categories"] == []
        assert data["severities"] == []
        assert data["years"] == []
        assert "statuses" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_comparison_empty_state(db_session):
    """Test comparison returns proper empty state when no evolution records exist."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Comparison Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        # Create reports but no risks
        report_prev = Report(company_id=company.id, fiscal_year=2024, source_file="prev.pdf", processing_status="completed")
        report_curr = Report(company_id=company.id, fiscal_year=2025, source_file="curr.pdf", processing_status="completed")
        db_session.add_all([report_prev, report_curr])
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/comparison/compare",
                json={
                    "company_id": _str_id(company.id),
                    "year_current": 2025,
                    "year_previous": 2024,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["new_risks"] == []
        assert data["removed_risks"] == []
        assert data["severity_increased"] == []
        assert data["severity_decreased"] == []
        assert data["modified_risks"] == []
        assert data["total_changes"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_empty_state(db_session):
    """Test dashboard returns proper empty state when no risks exist."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Dashboard Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report_prev = Report(company_id=company.id, fiscal_year=2024, source_file="prev.pdf", processing_status="completed")
        report_curr = Report(company_id=company.id, fiscal_year=2025, source_file="curr.pdf", processing_status="completed")
        db_session.add_all([report_prev, report_curr])
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/dashboard/executive?company_id={company.id}&year_current=2025&year_previous=2024",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_risks_previous"] == 0
        assert data["total_risks_current"] == 0
        assert data["risk_counts_by_status"] == {
            status.value: 0 for status in [
                "NEW", "REMOVED", "UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED"
            ]
        }
        assert data["key_risk_changes"] == []
        assert data["financial_metrics"] == []
        assert data["financial_changes"] == []
        assert data["risk_financial_correlations"] == []
        assert data["evidence"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_heatmap_empty_state(db_session):
    """Test heatmap returns proper empty state when no risks exist."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Heatmap Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report = Report(company_id=company.id, fiscal_year=2025, source_file="report.pdf", processing_status="completed")
        db_session.add(report)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/dashboard/heatmap?company_id={company.id}&year=2025",
            )

        assert response.status_code == 200
        data = response.json()
        assert data["cells"] == []
        assert data["total_risks"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_executive_summary_empty_risks(db_session):
    """Test executive summary handles empty risks properly."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Exec Summary Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report = Report(company_id=company.id, fiscal_year=2025, source_file="report.pdf", processing_status="completed")
        db_session.add(report)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reports/executive-summary",
                json={"company_id": _str_id(company.id), "year": 2025},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["risk_distribution"] == {}
        assert data["top_risks"] == []
        assert data["key_changes"] == []
        assert data["overall_risk_score"] == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scanner_empty_results(db_session):
    """Test scanner returns proper empty state when no matches."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Scanner Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report = Report(company_id=company.id, fiscal_year=2025, source_file="report.pdf", processing_status="completed")
        db_session.add(report)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/scanner/run",
                json={
                    "company_ids": [_str_id(company.id)],
                    "year_current": 2025,
                    "criteria": [
                        {"factor": "category", "operator": "eq", "value": "NonExistentCategory"},
                    ],
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 0
        assert data["results"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_market_intelligence_empty_state(db_session):
    """Test market intelligence returns proper empty state."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Market Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/market-intelligence/{company.id}/events?year_current=2025",
            )

        assert response.status_code == 200
        data = response.json()
        # Should return empty events and related_risks
        assert data["events"] == []
        assert data["related_risks"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_industry_intelligence_empty_state(db_session):
    """Test industry intelligence returns proper empty state."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Industry Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/industry-intelligence/{company.id}?year=2025",
            )

        assert response.status_code == 200
        data = response.json()
        # Should return empty themes and peers
        assert data["themes"] == []
        assert data["peers"] == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_financial_health_empty_metrics(db_session):
    """Test financial health handles empty metrics properly."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        # Test via financial health endpoint
        company = Company(name="Fin Health Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        # Create financial snapshot with no metrics
        snapshot = FinancialSnapshot(
            company_id=company.id,
            fiscal_year=2025,
            currency="INR",
            data_source="test",
        )
        db_session.add(snapshot)
        await db_session.flush()

        # Test the financial health service directly
        from app.intelligence.financial_health import FinancialHealthService
        from app.models.financial_health import FinancialSnapshot as FSSnapshot
        
        # Create minimal snapshots
        current = FSSnapshot(
            company_id=_str_id(company.id),
            report_id=None,
            report_year=2025,
            document_id="test",
            metrics={},
        )
        
        result = FinancialHealthService().analyze(current=current, previous=None, evolution_records=[])
        
        assert result.changes == []
        assert result.correlations == []
        assert result.snapshot_current is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_executive_pdf_empty_risks(db_session):
    """Test executive PDF generation handles empty risks."""
    from app.models.intelligence import ExecutivePDFRequest
    
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="PDF Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report = Report(company_id=company.id, fiscal_year=2025, source_file="report.pdf", processing_status="completed")
        db_session.add(report)
        await db_session.flush()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reports/executive-pdf",
                json={"company_id": _str_id(company.id), "year": 2025},
            )

        # Should succeed even with no risks
        assert response.status_code in (200, 501)  # 501 if PDF generation not implemented
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_risk_explorer_detail_empty(db_session):
    """Test risk explorer detail handles missing risks."""
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        company = Company(name="Detail Empty Corp", sector="Technology")
        db_session.add(company)
        await db_session.flush()

        report = Report(company_id=company.id, fiscal_year=2025, source_file="report.pdf", processing_status="completed")
        db_session.add(report)
        await db_session.flush()

        # Query for a risk that doesn't exist
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/risk-explorer/{uuid4()}?year=2025",
            )

        # Should return 404 for non-existent risk
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()