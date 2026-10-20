"""Tests for SSE streaming executive summary endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.main import app
from app.db.base import Company, Report, RiskItem
from app.db.session import get_db_session


@pytest.mark.asyncio
async def test_executive_summary_stream_returns_sse_events(db_session):
    """Test that the SSE streaming endpoint returns proper events."""
    # Create test data
    company = Company(name="Stream Test Corp", sector="Technology")
    db_session.add(company)
    await db_session.flush()

    report = Report(
        company_id=company.id,
        fiscal_year=2025,
        source_file="stream-2025.pdf",
        processing_status="completed",
    )
    db_session.add(report)
    await db_session.flush()

    risks = [
        RiskItem(
            report_id=report.id, company_id=company.id,
            category="Cybersecurity", severity=5, severity_label="HIGH", confidence_score=0.92,
            risk_title="Data breach exposure",
            risk_summary="Significant customer data breach risk from third-party vendors",
            source_page=10, source_paragraph="Third-party vendors may expose customer data.",
        ),
        RiskItem(
            report_id=report.id, company_id=company.id,
            category="Regulatory", severity=4, severity_label="HIGH", confidence_score=0.85,
            risk_title="GDPR compliance risk",
            risk_summary="Potential GDPR fines from data processing gaps",
            source_page=15, source_paragraph="Data processing may not fully comply with GDPR.",
        ),
    ]
    db_session.add_all(risks)
    await db_session.flush()

    # Override database dependency
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        await db_session.commit()
        # Make SSE request
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reports/executive-summary/stream",
                json={"company_id": str(company.id), "year": 2025},
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        # Parse SSE events
        content = response.text
        events = []
        for line in content.split("\n"):
            if line.startswith("data: "):
                import json
                events.append(json.loads(line[6:]))
        
        # Verify event structure
        assert len(events) >= 3  # start + content chunks + done
        
        # First event should be start
        assert events[0]["type"] == "start"
        assert events[0]["company"] == "Stream Test Corp"
        assert events[0]["year"] == 2025
        
        # Last event should be done
        assert events[-1]["type"] == "done"
        assert "full_text" in events[-1]
        assert len(events[-1]["full_text"]) > 0
        
        # Should have content events in between
        content_events = [e for e in events if e["type"] == "content"]
        assert len(content_events) > 0
        
        # Full text should contain risk-related terms
        full_text = events[-1]["full_text"].lower()
        assert any(term in full_text for term in ["cybersecurity", "regulatory", "risk", "data"])
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_executive_summary_stream_with_evolution(db_session):
    """Test SSE streaming with evolution data from previous year."""
    company = Company(name="Evolution Stream Corp", sector="Banking")
    db_session.add(company)
    await db_session.flush()

    # Previous year report
    prev_report = Report(
        company_id=company.id,
        fiscal_year=2024,
        source_file="evolution-2024.pdf",
        processing_status="completed",
    )
    # Current year report
    curr_report = Report(
        company_id=company.id,
        fiscal_year=2025,
        source_file="evolution-2025.pdf",
        processing_status="completed",
    )
    db_session.add_all([prev_report, curr_report])
    await db_session.flush()

    # Previous year risks
    prev_risks = [
        RiskItem(
            report_id=prev_report.id, company_id=company.id,
            category="Credit", severity=3, severity_label="MEDIUM", confidence_score=0.75,
            risk_title="Commercial real estate exposure",
            risk_summary="Moderate commercial real estate credit exposure",
            source_page=20, source_paragraph="CRE portfolio shows moderate risk.",
        ),
    ]
    # Current year risks (including evolved ones)
    curr_risks = [
        RiskItem(
            report_id=curr_report.id, company_id=company.id,
            category="Credit", severity=5, severity_label="HIGH", confidence_score=0.9,
            risk_title="Commercial real estate exposure escalated",
            risk_summary="Elevated commercial real estate credit losses expected",
            source_page=22, source_paragraph="CRE losses have increased significantly.",
        ),
        RiskItem(
            report_id=curr_report.id, company_id=company.id,
            category="Cybersecurity", severity=4, severity_label="HIGH", confidence_score=0.88,
            risk_title="New ransomware threat",
            risk_summary="Emerging ransomware threat to banking infrastructure",
            source_page=30, source_paragraph="Ransomware attacks on banks increasing.",
        ),
    ]
    db_session.add_all(prev_risks + curr_risks)
    await db_session.flush()

    # Override database dependency
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        await db_session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reports/executive-summary/stream",
                json={"company_id": str(company.id), "year": 2025, "include_evolution": True},
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        
        content = response.text
        events = []
        for line in content.split("\n"):
            if line.startswith("data: "):
                import json
                events.append(json.loads(line[6:]))
        
        # Should have evolution-aware content
        full_text = events[-1]["full_text"].lower()
        assert "escalated" in full_text or "increased" in full_text or "new" in full_text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_executive_summary_stream_company_not_found(db_session):
    """Test SSE streaming returns 404 for non-existent company."""
    import uuid
    fake_id = str(uuid.uuid4())
    
    # Override database dependency
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/reports/executive-summary/stream",
                json={"company_id": fake_id, "year": 2025},
            )
    
        assert response.status_code == 404
        assert response.json()["detail"] == "Company not found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_executive_summary_stream_no_reports(db_session):
    """Test SSE streaming returns 404 when company has no reports."""
    company = Company(name="No Reports Corp", sector="Technology")
    db_session.add(company)
    await db_session.flush()

    # Override database dependency
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_session] = override_db

    try:
        await db_session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Without year specified, should get "No reports found for company"
            response = await client.post(
                "/api/v1/reports/executive-summary/stream",
                json={"company_id": str(company.id)},
            )
    
        assert response.status_code == 404
        assert response.json()["detail"] == "No reports found for company"
    finally:
        app.dependency_overrides.clear()