from uuid import UUID
from typing import AsyncGenerator
import json
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import Company, FinancialSnapshot, Report, RiskItem
from app.db.session import get_db_session
from app.llm.base import create_system_message, create_user_message
from app.llm.prompts.comparison import (
    EVOLUTION_SUMMARY_PROMPT,
    EXECUTIVE_RISK_SUMMARY_PROMPT,
)
from app.llm.provider_factory import get_default_llm
from app.models.intelligence import (
    ExecutivePDFRequest,
    ExecutiveSummaryRequest,
    ExecutiveSummaryResponse,
    FinancialHealthResponse,
    PeerComparisonRequest,
    PeerComparisonResponse,
)
from fpdf import FPDF

logger = get_logger(__name__)

router = APIRouter()


class ExecutiveReportPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, "GlobalRisk AI - Confidential", align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 12, 200, 12)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(0, 51, 102)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def sub_section_title(self, title):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(51, 51, 51)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(51, 51, 51)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet_point(self, text, indent=15):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(51, 51, 51)
        x = self.get_x()
        self.cell(indent, 5, "")
        self.set_font("Helvetica", "", 9)
        self.cell(5, 5, chr(8226))
        self.multi_cell(0, 5, text)
        self.ln(1)

    def key_value(self, key, value, indent=15):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(51, 51, 51)
        self.cell(indent, 5, "")
        self.cell(50, 5, f"{key}:")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, str(value), new_x="LMARGIN", new_y="NEXT")


@router.post("/executive-summary", response_model=ExecutiveSummaryResponse)
async def generate_executive_summary(
    request: ExecutiveSummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, request.company_id, options=[selectinload(Company.reports)])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    target_year = request.year
    if target_year is None:
        target_year = max((r.fiscal_year for r in company.reports), default=None)

    if target_year is None:
        raise HTTPException(status_code=404, detail="No reports found for company")

    report = next((r for r in company.reports if r.fiscal_year == target_year), None)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for FY{target_year} not found")

    risks = await db.execute(select(RiskItem).where(RiskItem.report_id == report.id))
    risks = risks.scalars().all()

    risk_distribution = {}
    for risk in risks:
        risk_distribution[risk.severity] = risk_distribution.get(risk.severity, 0) + 1

    top_risks = sorted(risks, key=lambda r: r.confidence_score, reverse=True)[:5]

    financial = await db.execute(
        select(FinancialSnapshot).where(
            FinancialSnapshot.company_id == request.company_id,
            FinancialSnapshot.fiscal_year == target_year,
        )
    )
    financial = financial.scalar_one_or_none()

    return ExecutiveSummaryResponse(
        company_id=request.company_id,
        company_name=company.name,
        fiscal_year=target_year,
        overall_risk_score=sum(r.confidence_score for r in risks) / len(risks) if risks else 0,
        risk_distribution=risk_distribution,
        top_risks=[
            {
                "category": r.category,
                "severity": r.severity,
                "summary": r.summary,
                "confidence": r.confidence_score,
            }
            for r in top_risks
        ],
        key_changes=[],
        financial_health="Financial data available" if financial else "No financial data",
        ai_narrative=(
            f"Executive summary for {company.name} FY{target_year}. "
            f"{len(risks)} material risks identified across "
            f"{len(risk_distribution)} severity levels."
        ),
        confidence_score=0.85,
        generated_at=func.now(),
    )


@router.post("/executive-summary/stream")
async def generate_executive_summary_stream(
    request: ExecutiveSummaryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Generate executive summary with SSE streaming."""
    company_id = str(request.company_id)
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    target_year = request.year
    if target_year is None:
        report_query = select(Report).where(Report.company_id == company_id).order_by(Report.fiscal_year.desc())
        report_result = await db.execute(report_query)
        latest_report = report_result.scalars().first()
        if latest_report:
            target_year = latest_report.fiscal_year
        else:
            raise HTTPException(status_code=404, detail="No reports found for company")

    report_query = select(Report).where(
        Report.company_id == company_id,
        Report.fiscal_year == target_year,
    )
    report_result = await db.execute(report_query)
    report = report_result.scalars().first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for FY{target_year} not found")

    risks = await db.execute(select(RiskItem).where(RiskItem.report_id == report.id))
    risks = risks.scalars().all()

    # Get evolution data if requested
    evolution_summary = ""
    if request.include_evolution:
        prev_report = await db.execute(
            select(Report).where(
                Report.company_id == company_id,
                Report.fiscal_year == target_year - 1,
            )
        )
        prev_report = prev_report.scalar_one_or_none()
        if prev_report:
            prev_risks = await db.execute(select(RiskItem).where(RiskItem.report_id == prev_report.id))
            prev_risks = prev_risks.scalars().all()
            
            from app.comparison.matcher import SemanticRiskMatcher
            from app.comparison.evolution import RiskEvolutionClassifier
            from app.comparison.normalizer import RiskNormalizer
            
            normalizer = RiskNormalizer()
            prev_normalized = await normalizer.normalize_batch(
                [{
                    "risk_id": str(r.id),
                    "report_id": str(prev_report.id),
                    "report_year": prev_report.fiscal_year,
                    "category": r.category,
                    "title": r.risk_summary[:120] if r.risk_summary else "",
                    "summary": r.risk_summary or "",
                    "severity": r.severity,
                    "source_page": r.source_page,
                    "evidence": {
                        "document_id": prev_report.source_file,
                        "report_year": prev_report.fiscal_year,
                        "page": r.source_page,
                        "text": r.source_paragraph or r.risk_summary or "",
                    },
                } for r in prev_risks],
                report_year=prev_report.fiscal_year,
                generate_embeddings=True,
            )
            curr_normalized = await normalizer.normalize_batch(
                [{
                    "risk_id": str(r.id),
                    "report_id": str(report.id),
                    "report_year": report.fiscal_year,
                    "category": r.category,
                    "title": r.risk_summary[:120] if r.risk_summary else "",
                    "summary": r.risk_summary or "",
                    "severity": r.severity,
                    "source_page": r.source_page,
                    "evidence": {
                        "document_id": report.source_file,
                        "report_year": report.fiscal_year,
                        "page": r.source_page,
                        "text": r.source_paragraph or r.risk_summary or "",
                    },
                } for r in risks],
                report_year=report.fiscal_year,
                generate_embeddings=True,
            )
            
            matches = await SemanticRiskMatcher().match_all_risks(
                curr_normalized, prev_normalized,
                y2_year=report.fiscal_year, y1_year=prev_report.fiscal_year
            )
            records = RiskEvolutionClassifier().classify_evolution(
                curr_normalized, prev_normalized, matches,
                y2_year=report.fiscal_year, y1_year=prev_report.fiscal_year
            )
            
            new_count = sum(1 for r in records if r.change_type.value == "NEW")
            removed_count = sum(1 for r in records if r.change_type.value == "REMOVED")
            severity_up_count = sum(1 for r in records if r.change_type.value == "ESCALATED")
            severity_down_count = sum(1 for r in records if r.change_type.value == "DE-ESCALATED")
            modified_count = sum(1 for r in records if r.change_type.value == "MODIFIED")
            
            key_changes_text = "\n".join([
                f"- {r.change_type.value}: {r.metadata.get('title_y2', 'Unknown')}" 
                for r in records if r.change_type.value != "UNCHANGED"
            ][:5])
            
            evolution_summary = EVOLUTION_SUMMARY_PROMPT.format(
                company_name=company.name,
                prev_year=prev_report.fiscal_year,
                curr_year=report.fiscal_year,
                new_count=new_count,
                removed_count=removed_count,
                severity_up_count=severity_up_count,
                severity_down_count=severity_down_count,
                modified_count=modified_count,
                key_changes=key_changes_text or "No significant changes",
            )

    # Get financial context if requested
    financial_context = "No financial data available"
    if request.include_financial:
        financial = await db.execute(
            select(FinancialSnapshot).where(
                FinancialSnapshot.company_id == company_id,
                FinancialSnapshot.fiscal_year == target_year,
            )
        )
        financial = financial.scalar_one_or_none()
        if financial:
            financial_context = (
                f"Revenue: {financial.revenue}, Profit: {financial.profit}, "
                f"Net Margin: {financial.net_margin}, ROE: {financial.roe}, "
                f"Debt/Equity: {financial.debt_equity}, Cash Flow: {financial.cash_flow}"
            )

    # Prepare risk profile for executive summary prompt
    risk_distribution = {}
    for risk in risks:
        risk_distribution[risk.severity] = risk_distribution.get(risk.severity, 0) + 1
    
    category_breakdown = {}
    for risk in risks:
        category_breakdown[risk.category] = category_breakdown.get(risk.category, 0) + 1
    
    top_risks_text = "\n".join([
        f"- {r.category} (Severity: {r.severity}, Confidence: {r.confidence_score:.2f}): {r.risk_summary[:100] if r.risk_summary else ''}"
        for r in sorted(risks, key=lambda x: x.confidence_score, reverse=True)[:5]
    ])

    # Choose prompt based on whether we have evolution data
    if evolution_summary:
        prompt = evolution_summary
    else:
        prompt = EXECUTIVE_RISK_SUMMARY_PROMPT.format(
            company_name=company.name,
            year=target_year,
            total_risks=len(risks),
            severity_breakdown=risk_distribution,
            category_breakdown=category_breakdown,
            top_risks=top_risks_text,
            evolution_highlights="No prior year data for comparison",
            financial_context=financial_context,
        )

    llm = get_default_llm()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from LLM stream."""
        if not llm or not llm.is_available():
            # Fallback to non-streaming response
            fallback_narrative = (
                f"Executive summary for {company.name} FY{target_year}. "
                f"{len(risks)} material risks identified across "
                f"{len(risk_distribution)} severity levels."
            )
            yield f"data: {json.dumps({'type': 'content', 'data': fallback_narrative})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        try:
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'start', 'company': company.name, 'year': target_year})}\n\n"
            
            # Stream the LLM response
            accumulated = ""
            async for chunk in llm.generate_stream([
                create_system_message("You are a senior risk analyst writing executive summaries for board-level review. Be concise, professional, and focus on material risks and strategic implications."),
                create_user_message(prompt),
            ]):
                accumulated += chunk
                yield f"data: {json.dumps({'type': 'content', 'data': chunk})}\n\n"
            
            # Send completion
            yield f"data: {json.dumps({'type': 'done', 'full_text': accumulated})}\n\n"
        except Exception as e:
            logger.error("executive_summary_stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/executive-summary/pdf")
async def generate_executive_summary_pdf(
    request: ExecutivePDFRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Generate executive summary as a downloadable PDF report."""
    company = await db.get(Company, request.company_id, options=[selectinload(Company.reports)])
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    target_year = request.year
    if target_year is None:
        target_year = max((r.fiscal_year for r in company.reports), default=None)

    if target_year is None:
        raise HTTPException(status_code=404, detail="No reports found for company")

    report = next((r for r in company.reports if r.fiscal_year == target_year), None)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for FY{target_year} not found")

    # Get current year risks
    risks = await db.execute(select(RiskItem).where(RiskItem.report_id == report.id))
    risks = risks.scalars().all()

    # Get previous year data if evolution requested
    prev_report = None
    prev_risks = []
    evolution_data = {}
    if request.include_evolution:
        prev_report_result = await db.execute(
            select(Report).where(
                Report.company_id == request.company_id,
                Report.fiscal_year == target_year - 1,
            )
        )
        prev_report = prev_report_result.scalar_one_or_none()
        if prev_report:
            prev_risks_result = await db.execute(select(RiskItem).where(RiskItem.report_id == prev_report.id))
            prev_risks = prev_risks_result.scalars().all()
            
            from app.comparison.matcher import SemanticRiskMatcher
            from app.comparison.evolution import RiskEvolutionClassifier
            from app.comparison.normalizer import RiskNormalizer
            
            normalizer = RiskNormalizer()
            prev_normalized = await normalizer.normalize_batch(
                [{
                    "risk_id": str(r.id),
                    "report_id": str(prev_report.id),
                    "report_year": prev_report.fiscal_year,
                    "category": r.category,
                    "title": r.risk_summary[:120] if r.risk_summary else "",
                    "summary": r.risk_summary or "",
                    "severity": r.severity,
                    "source_page": r.source_page,
                    "evidence": {
                        "document_id": prev_report.source_file,
                        "report_year": prev_report.fiscal_year,
                        "page": r.source_page,
                        "text": r.source_paragraph or r.risk_summary or "",
                    },
                } for r in prev_risks],
                report_year=prev_report.fiscal_year,
                generate_embeddings=True,
            )
            curr_normalized = await normalizer.normalize_batch(
                [{
                    "risk_id": str(r.id),
                    "report_id": str(report.id),
                    "report_year": report.fiscal_year,
                    "category": r.category,
                    "title": r.risk_summary[:120] if r.risk_summary else "",
                    "summary": r.risk_summary or "",
                    "severity": r.severity,
                    "source_page": r.source_page,
                    "evidence": {
                        "document_id": report.source_file,
                        "report_year": report.fiscal_year,
                        "page": r.source_page,
                        "text": r.source_paragraph or r.risk_summary or "",
                    },
                } for r in risks],
                report_year=report.fiscal_year,
                generate_embeddings=True,
            )
            
            matches = await SemanticRiskMatcher().match_all_risks(
                curr_normalized, prev_normalized,
                y2_year=report.fiscal_year, y1_year=prev_report.fiscal_year
            )
            records = RiskEvolutionClassifier().classify_evolution(
                curr_normalized, prev_normalized, matches,
                y2_year=report.fiscal_year, y1_year=prev_report.fiscal_year
            )
            
            new_count = sum(1 for r in records if r.change_type.value == "NEW")
            removed_count = sum(1 for r in records if r.change_type.value == "REMOVED")
            severity_up_count = sum(1 for r in records if r.change_type.value == "ESCALATED")
            severity_down_count = sum(1 for r in records if r.change_type.value == "DE-ESCALATED")
            modified_count = sum(1 for r in records if r.change_type.value == "MODIFIED")
            
            evolution_data = {
                "new_count": new_count,
                "removed_count": removed_count,
                "severity_up_count": severity_up_count,
                "severity_down_count": severity_down_count,
                "modified_count": modified_count,
                "records": records,
            }

    # Get financial data if requested
    financial = None
    if request.include_financial:
        financial_result = await db.execute(
            select(FinancialSnapshot).where(
                FinancialSnapshot.company_id == request.company_id,
                FinancialSnapshot.fiscal_year == target_year,
            )
        )
        financial = financial_result.scalar_one_or_none()

    # Generate PDF
    pdf = ExecutiveReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Title page
    pdf.ln(30)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "Executive Risk Summary", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 10, company.name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Fiscal Year {target_year}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "Confidential - For Internal Use Only", align="C", new_x="LMARGIN", new_y="NEXT")

    # Risk Overview
    pdf.add_page()
    pdf.section_title("1. Risk Overview")
    
    risk_distribution = {}
    for risk in risks:
        risk_distribution[risk.severity] = risk_distribution.get(risk.severity, 0) + 1
    
    pdf.key_value("Total Risks Identified", len(risks))
    pdf.key_value("Overall Risk Score", f"{sum(r.confidence_score for r in risks) / len(risks) * 10:.1f}/10" if risks else "N/A")
    pdf.key_value("Severity Breakdown", "")
    for sev, count in sorted(risk_distribution.items()):
        pdf.key_value(f"  {sev.capitalize()}", count, indent=20)
    pdf.ln(3)

    # Top Risks
    pdf.section_title("2. Top Material Risks")
    top_risks = sorted(risks, key=lambda r: r.confidence_score, reverse=True)[:5]
    for i, risk in enumerate(top_risks, 1):
        pdf.sub_section_title(f"Risk {i}: {risk.category} ({risk.severity.capitalize()})")
        pdf.key_value("Confidence", f"{risk.confidence_score:.0%}")
        if risk.source_page:
            pdf.key_value("Source Page", risk.source_page)
        pdf.body_text(risk.risk_summary or risk.summary or "No summary available")
        pdf.ln(2)

    # Year-over-Year Evolution
    if request.include_evolution and prev_report and evolution_data:
        pdf.add_page()
        pdf.section_title("3. Year-over-Year Risk Evolution")
        pdf.key_value("Comparison Period", f"FY{evolution_data.get('prev_year', target_year - 1)} vs FY{target_year}")
        pdf.key_value("New Risks", evolution_data.get("new_count", 0))
        pdf.key_value("Removed Risks", evolution_data.get("removed_count", 0))
        pdf.key_value("Severity Increased", evolution_data.get("severity_up_count", 0))
        pdf.key_value("Severity Decreased", evolution_data.get("severity_down_count", 0))
        pdf.key_value("Modified Risks", evolution_data.get("modified_count", 0))
        pdf.ln(3)

        # New risks
        new_risks = [r for r in evolution_data.get("records", []) if r.change_type.value == "NEW"]
        if new_risks:
            pdf.sub_section_title("New Risks Identified")
            for r in new_risks[:5]:
                title = r.metadata.get("title_y2", "Unknown")
                sev = r.metadata.get("severity_y2", "Unknown")
                page = r.metadata.get("page_y2", "N/A")
                pdf.bullet_point(f"{title} (Severity: {sev}, Page: {page})")
            pdf.ln(2)

        # Removed risks
        removed_risks = [r for r in evolution_data.get("records", []) if r.change_type.value == "REMOVED"]
        if removed_risks:
            pdf.sub_section_title("Risks Removed")
            for r in removed_risks[:5]:
                title = r.metadata.get("title_y1", "Unknown")
                page = r.metadata.get("page_y1", "N/A")
                pdf.bullet_point(f"{title} (Page: {page})")
            pdf.ln(2)

        # Escalated risks
        escalated = [r for r in evolution_data.get("records", []) if r.change_type.value == "ESCALATED"]
        if escalated:
            pdf.sub_section_title("Risks with Increased Severity")
            for r in escalated[:5]:
                title = r.metadata.get("title_y2", "Unknown")
                prev_sev = r.metadata.get("severity_y1", "Unknown")
                curr_sev = r.metadata.get("severity_y2", "Unknown")
                page = r.metadata.get("page_y2", "N/A")
                pdf.bullet_point(f"{title} ({prev_sev} -> {curr_sev}, Page: {page})")
            pdf.ln(2)

        # De-escalated risks
        de_escalated = [r for r in evolution_data.get("records", []) if r.change_type.value == "DE-ESCALATED"]
        if de_escalated:
            pdf.sub_section_title("Risks with Decreased Severity")
            for r in de_escalated[:5]:
                title = r.metadata.get("title_y2", "Unknown")
                prev_sev = r.metadata.get("severity_y1", "Unknown")
                curr_sev = r.metadata.get("severity_y2", "Unknown")
                page = r.metadata.get("page_y2", "N/A")
                pdf.bullet_point(f"{title} ({prev_sev} -> {curr_sev}, Page: {page})")
            pdf.ln(2)

    # Financial Health
    if request.include_financial and financial:
        pdf.add_page()
        pdf.section_title("4. Financial Health Context")
        pdf.key_value("Revenue", f"${financial.revenue:,.0f}" if financial.revenue else "N/A")
        pdf.key_value("Profit", f"${financial.profit:,.0f}" if financial.profit else "N/A")
        pdf.key_value("Net Margin", f"{financial.net_margin:.1f}%" if financial.net_margin else "N/A")
        pdf.key_value("ROE", f"{financial.roe:.1f}%" if financial.roe else "N/A")
        pdf.key_value("Debt/Equity", f"{financial.debt_equity:.2f}" if financial.debt_equity else "N/A")
        pdf.key_value("Cash Flow", f"${financial.cash_flow:,.0f}" if financial.cash_flow else "N/A")
        pdf.ln(3)

    # AI Narrative
    pdf.add_page()
    pdf.section_title("5. AI-Generated Executive Narrative")
    
    # Build prompt for AI narrative
    risk_distribution = {}
    for risk in risks:
        risk_distribution[risk.severity] = risk_distribution.get(risk.severity, 0) + 1
    
    category_breakdown = {}
    for risk in risks:
        category_breakdown[risk.category] = category_breakdown.get(risk.category, 0) + 1
    
    top_risks_text = "\n".join([
        f"- {r.category} (Severity: {r.severity}, Confidence: {r.confidence_score:.2f}): {r.risk_summary[:100] if r.risk_summary else ''}"
        for r in sorted(risks, key=lambda x: x.confidence_score, reverse=True)[:5]
    ])
    
    financial_context = "No financial data available"
    if financial:
        financial_context = (
            f"Revenue: {financial.revenue}, Profit: {financial.profit}, "
            f"Net Margin: {financial.net_margin}, ROE: {financial.roe}, "
            f"Debt/Equity: {financial.debt_equity}, Cash Flow: {financial.cash_flow}"
        )
    
    evolution_highlights = "No prior year data for comparison"
    if prev_report and evolution_data:
        evolution_highlights = (
            f"Compared to FY{prev_report.fiscal_year}: "
            f"{evolution_data.get('new_count', 0)} new risks, "
            f"{evolution_data.get('removed_count', 0)} removed risks, "
            f"{evolution_data.get('severity_up_count', 0)} severity increases, "
            f"{evolution_data.get('severity_down_count', 0)} severity decreases."
        )
    
    prompt = EXECUTIVE_RISK_SUMMARY_PROMPT.format(
        company_name=company.name,
        year=target_year,
        total_risks=len(risks),
        severity_breakdown=risk_distribution,
        category_breakdown=category_breakdown,
        top_risks=top_risks_text,
        evolution_highlights=evolution_highlights,
        financial_context=financial_context,
    )

    llm = get_default_llm()
    ai_narrative = ""
    if llm and llm.is_available():
        try:
            ai_narrative = await llm.generate([
                create_system_message("You are a senior risk analyst writing executive summaries for board-level review. Be concise, professional, and focus on material risks and strategic implications."),
                create_user_message(prompt),
            ])
        except Exception as e:
            logger.error("pdf_ai_narrative_error", error=str(e))
            ai_narrative = "AI narrative generation failed. Please review risk data manually."
    else:
        ai_narrative = (
            f"Executive summary for {company.name} FY{target_year}. "
            f"{len(risks)} material risks identified across "
            f"{len(risk_distribution)} severity levels. "
            f"{evolution_highlights}. "
            f"{financial_context}."
        )
    
    pdf.body_text(ai_narrative)

    # Evidence Appendix
    if risks:
        pdf.add_page()
        pdf.section_title("6. Evidence Appendix")
        pdf.body_text("The following table lists the source evidence for each risk identified in this report.")
        pdf.ln(2)
        
        # Table header
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(10, 6, "#", border=1, fill=True, align="C")
        pdf.cell(35, 6, "Category", border=1, fill=True, align="C")
        pdf.cell(20, 6, "Severity", border=1, fill=True, align="C")
        pdf.cell(20, 6, "Confidence", border=1, fill=True, align="C")
        pdf.cell(20, 6, "Page", border=1, fill=True, align="C")
        pdf.cell(85, 6, "Summary", border=1, fill=True, align="C")
        pdf.ln()
        
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(51, 51, 51)
        for i, risk in enumerate(risks, 1):
            pdf.cell(10, 6, str(i), border=1, align="C")
            pdf.cell(35, 6, risk.category[:30], border=1)
            pdf.cell(20, 6, risk.severity.capitalize(), border=1, align="C")
            pdf.cell(20, 6, f"{risk.confidence_score:.0%}", border=1, align="C")
            pdf.cell(20, 6, str(risk.source_page) if risk.source_page else "N/A", border=1, align="C")
            summary = (risk.risk_summary or risk.summary or "")[:70]
            pdf.cell(85, 6, summary, border=1)
            pdf.ln()

    # Output PDF
    pdf_bytes = pdf.output()
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    
    filename = f"{company.name.replace(' ', '_')}_FY{target_year}_Executive_Risk_Summary.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get("/{company_id}/financial-health", response_model=FinancialHealthResponse)
async def get_financial_health(
    company_id: UUID,
    fiscal_year: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if fiscal_year is None:
        report = await db.execute(
            select(Report)
            .where(Report.company_id == company_id)
            .order_by(Report.fiscal_year.desc())
        )
        report = report.scalar_one_or_none()
        if report:
            fiscal_year = report.fiscal_year

    if fiscal_year is None:
        raise HTTPException(status_code=404, detail="No reports found for company")

    financial = await db.execute(
        select(FinancialSnapshot).where(
            FinancialSnapshot.company_id == company_id,
            FinancialSnapshot.fiscal_year == fiscal_year,
        )
    )
    financial = financial.scalar_one_or_none()

    if not financial:
        raise HTTPException(status_code=404, detail="Financial snapshot not found")

    return FinancialHealthResponse(
        company_id=company_id,
        fiscal_year=fiscal_year,
        metrics=[],
        revenue=financial.revenue,
        profit=financial.profit,
        net_margin=financial.net_margin,
        roe=financial.roe,
        roce=financial.roce,
        eps=financial.eps,
        debt_equity=financial.debt_equity,
        cash_flow=financial.cash_flow,
        market_cap=financial.market_cap,
    )


@router.post("/peer-comparison", response_model=PeerComparisonResponse)
async def peer_comparison(
    request: PeerComparisonRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    peers_query = select(Company).where(Company.id != company_id)
    if request.sector:
        peers_query = peers_query.where(Company.sector == request.sector)
    if request.peer_company_ids:
        peers_query = peers_query.where(Company.id.in_(request.peer_company_ids))

    peers_result = await db.execute(peers_query.limit(10))
    peers = peers_result.scalars().all()

    return PeerComparisonResponse(
        company_id=company_id,
        peers=[{"id": str(p.id), "name": p.name, "sector": p.sector} for p in peers],
        benchmark_metrics={},
        risk_profile_comparison={},
        total_peers=len(peers),
    )


@router.get("/{company_id}/risk-explorer")
async def risk_explorer(
    company_id: UUID,
    category: str | None = Query(None),
    severity: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = (
        select(RiskItem)
        .join(Report, RiskItem.report_id == Report.id)
        .where(Report.company_id == company_id)
    )

    if category:
        query = query.where(RiskItem.category == category)
    if severity:
        query = query.where(RiskItem.severity == severity)

    result = await db.execute(query)
    risks = result.scalars().all()

    return {
        "company_id": company_id,
        "filters": {"category": category, "severity": severity},
        "risks_found": len(risks),
        "risks": [
            {
                "id": str(r.id),
                "category": r.category,
                "severity": r.severity,
                "summary": r.summary,
                "confidence": r.confidence_score,
                "year": r.report.fiscal_year if r.report else None,
            }
            for r in risks
        ],
    }
