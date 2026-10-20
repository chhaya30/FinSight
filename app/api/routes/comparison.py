from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.logging import get_logger
from app.db.base import Company, EvolutionEntry, Report, RiskItem, RiskCitation
from app.db.session import get_db_session
from app.models.comparison import (
    ComparisonRequest,
    ComparisonResponse,
    EvidenceComparisonResponse,
    EvolutionSummary,
    RiskWithEvidence,
)
from app.models.risk import RiskEvidence, RiskItemResponse

logger = get_logger(__name__)

router = APIRouter()


def _build_risk_evidence(risk: RiskItem) -> Optional[RiskEvidence]:
    """Build RiskEvidence from RiskItem citations and metadata."""
    # Try to get the primary citation
    primary_citation = None
    if risk.citations:
        primary_citation = next((c for c in risk.citations if c.citation_type == "primary"), None)
        if not primary_citation:
            primary_citation = risk.citations[0]
    
    if primary_citation:
        return RiskEvidence(
            document_id=str(primary_citation.chunk_id) if primary_citation.chunk_id else None,
            report_year=None,  # Will be filled from report if needed
            page=primary_citation.page_number,
            chunk_id=str(primary_citation.chunk_id) if primary_citation.chunk_id else None,
            text=primary_citation.source_text[:500] if primary_citation.source_text else "",
            section=None,
            text_hash=risk.source_text_hash,
            char_start=primary_citation.start_char,
            char_end=primary_citation.end_char,
            context_before=primary_citation.highlighted_text,
            context_after=None,
            metadata={
                "category": risk.category,
                "severity": risk.severity_label,
                "confidence_score": risk.confidence_score,
                "citation_type": primary_citation.citation_type,
            },
        )
    
    # Fallback to risk metadata
    if risk.source_page or risk.source_paragraph:
        return RiskEvidence(
            document_id=None,
            report_year=None,
            page=risk.source_page,
            chunk_id=None,
            text=risk.source_paragraph or risk.risk_summary or "",
            section=None,
            text_hash=risk.source_text_hash,
            char_start=None,
            char_end=None,
            context_before=None,
            context_after=None,
            metadata={
                "category": risk.category,
                "severity": risk.severity_label,
                "confidence_score": risk.confidence_score,
            },
        )
    
    return None


def _validate_evidence_for_change_type(
    change_type: str,
    evidence_prev: Optional[RiskEvidence],
    evidence_current: Optional[RiskEvidence],
) -> tuple[bool, str]:
    """
    Validate that evidence is present according to change type requirements.
    
    Acceptance criteria:
    - New risk ke liye current page evidence
    - Removed risk ke liye previous page evidence
    - Modified risk ke liye dono years ka evidence
    - Explanation evidence se traceable ho
    """
    if change_type == "NEW":
        if not evidence_current:
            return False, "NEW risk requires current year evidence"
        if not evidence_current.page:
            return False, "NEW risk requires current year page reference"
        return True, ""
    
    elif change_type == "REMOVED":
        if not evidence_prev:
            return False, "REMOVED risk requires previous year evidence"
        if not evidence_prev.page:
            return False, "REMOVED risk requires previous year page reference"
        return True, ""
    
    elif change_type in ("MODIFIED", "ESCALATED", "DE-ESCALATED", "SEVERITY_UP", "SEVERITY_DOWN"):
        if not evidence_prev:
            return False, f"{change_type} risk requires previous year evidence"
        if not evidence_current:
            return False, f"{change_type} risk requires current year evidence"
        if not evidence_prev.page:
            return False, f"{change_type} risk requires previous year page reference"
        if not evidence_current.page:
            return False, f"{change_type} risk requires current year page reference"
        return True, ""
    
    return True, ""


@router.post("/compare", response_model=ComparisonResponse)
async def compare_years(
    request: ComparisonRequest,
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, request.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report_current = await db.execute(
        select(Report).where(
            Report.company_id == request.company_id,
            Report.fiscal_year == request.year_current,
        )
    )
    report_current = report_current.scalar_one_or_none()
    if not report_current:
        raise HTTPException(
            status_code=404,
            detail=f"Report for FY{request.year_current} not found",
        )

    report_prev = await db.execute(
        select(Report).where(
            Report.company_id == request.company_id,
            Report.fiscal_year == request.year_previous,
        )
    )
    report_prev = report_prev.scalar_one_or_none()
    if not report_prev:
        raise HTTPException(
            status_code=404,
            detail=f"Report for FY{request.year_previous} not found",
        )

    # Fetch risks with citations
    risks_current = await db.execute(
        select(RiskItem)
        .where(RiskItem.report_id == report_current.id)
        .options(selectinload(RiskItem.citations))
    )
    risks_current = risks_current.scalars().all()

    risks_prev = await db.execute(
        select(RiskItem)
        .where(RiskItem.report_id == report_prev.id)
        .options(selectinload(RiskItem.citations))
    )
    risks_prev = risks_prev.scalars().all()

    existing_evolutions = await db.execute(
        select(EvolutionEntry).where(
            EvolutionEntry.risk_item_id_prev.in_([r.id for r in risks_prev])
            | EvolutionEntry.risk_item_id_current.in_([r.id for r in risks_current])
        )
    )
    existing_evolutions = existing_evolutions.scalars().all()

    if existing_evolutions:
        current_ids = {e.risk_item_id_current for e in existing_evolutions}
        new_risks = [r for r in risks_current if r.id not in current_ids]

        prev_ids = {e.risk_item_id_prev for e in existing_evolutions}
        removed_risks = [r for r in risks_prev if r.id not in prev_ids]

        escalated = []
        de_escalated = []
        modified = []

        for evo in existing_evolutions:
            if evo.change_type == "ESCALATED":
                escalated.append(evo)
            elif evo.change_type == "DE-ESCALATED":
                de_escalated.append(evo)
            elif evo.change_type == "MODIFIED":
                modified.append(evo)

        # Validate evidence for all change types and log warnings
        validation_issues = []

        for r in new_risks:
            evidence = _build_risk_evidence(r)
            valid, msg = _validate_evidence_for_change_type("NEW", None, evidence)
            if not valid:
                validation_issues.append(f"Risk {r.id}: {msg}")

        for r in removed_risks:
            evidence = _build_risk_evidence(r)
            valid, msg = _validate_evidence_for_change_type("REMOVED", evidence, None)
            if not valid:
                validation_issues.append(f"Risk {r.id}: {msg}")

        for r in escalated:
            evidence = _build_risk_evidence(r)
            valid, msg = _validate_evidence_for_change_type("ESCALATED", evidence, evidence)
            if not valid:
                validation_issues.append(f"Risk {r.id}: {msg}")

        for r in de_escalated:
            evidence = _build_risk_evidence(r)
            valid, msg = _validate_evidence_for_change_type("DE-ESCALATED", evidence, evidence)
            if not valid:
                validation_issues.append(f"Risk {r.id}: {msg}")

        for r in modified:
            evidence = _build_risk_evidence(r)
            valid, msg = _validate_evidence_for_change_type("MODIFIED", evidence, evidence)
            if not valid:
                validation_issues.append(f"Risk {r.id}: {msg}")

        if validation_issues:
            logger.warning("evidence_validation_issues", issues=validation_issues)

        return ComparisonResponse(
            company_id=request.company_id,
            year_current=request.year_current,
            year_previous=request.year_previous,
            new_risks=[
                RiskWithEvidence(
                    risk=RiskItemResponse.model_validate(r),
                    evidence=_build_risk_evidence(r),
                )
                for r in new_risks
            ],
            removed_risks=[
                RiskWithEvidence(
                    risk=RiskItemResponse.model_validate(r),
                    evidence=_build_risk_evidence(r),
                )
                for r in removed_risks
            ],
            severity_increased=[
                RiskWithEvidence(
                    risk=RiskItemResponse.model_validate(r),
                    evidence=_build_risk_evidence(r),
                )
                for r in escalated
            ],
            severity_decreased=[
                RiskWithEvidence(
                    risk=RiskItemResponse.model_validate(r),
                    evidence=_build_risk_evidence(r),
                )
                for r in de_escalated
            ],
            modified_risks=[
                RiskWithEvidence(
                    risk=RiskItemResponse.model_validate(r),
                    evidence=_build_risk_evidence(r),
                )
                for r in modified
            ],
            total_changes=len(existing_evolutions),
            processing_time_seconds=0.0,
        )

    return ComparisonResponse(
        company_id=request.company_id,
        year_current=request.year_current,
        year_previous=request.year_previous,
        new_risks=[],
        removed_risks=[],
        severity_increased=[],
        severity_decreased=[],
        modified_risks=[],
        total_changes=0,
        processing_time_seconds=0.0,
    )


@router.get("/{company_id}/evolution", response_model=ComparisonResponse)
async def get_evolution(
    company_id: UUID,
    year_current: int = Query(...),
    year_previous: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    request = ComparisonRequest(
        company_id=company_id,
        year_current=year_current,
        year_previous=year_previous,
    )
    return await compare_years(request, db)


@router.get("/evidence/{risk_id}", response_model=EvidenceComparisonResponse)
async def get_risk_evidence(
    risk_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Return both sides of the evolution record containing a selected risk."""
    risk_result = await db.execute(
        select(RiskItem)
        .where(RiskItem.id == risk_id)
        .options(selectinload(RiskItem.citations))
    )
    selected = risk_result.scalar_one_or_none()
    if not selected:
        raise HTTPException(status_code=404, detail="Risk not found")

    evolution_result = await db.execute(
        select(EvolutionEntry)
        .where(
            (EvolutionEntry.risk_item_id_prev == str(risk_id))
            | (EvolutionEntry.risk_item_id_current == str(risk_id))
        )
        .order_by(EvolutionEntry.created_at.desc())
        .limit(1)
    )
    evolution = evolution_result.scalar_one_or_none()

    previous = None
    current = None
    if evolution:
        if evolution.risk_item_id_prev:
            previous_result = await db.execute(
                select(RiskItem)
                .where(RiskItem.id == evolution.risk_item_id_prev)
                .options(selectinload(RiskItem.citations))
            )
            previous = previous_result.scalar_one_or_none()
        if evolution.risk_item_id_current:
            current_result = await db.execute(
                select(RiskItem)
                .where(RiskItem.id == evolution.risk_item_id_current)
                .options(selectinload(RiskItem.citations))
            )
            current = current_result.scalar_one_or_none()

    if not previous and not current:
        current = selected

    async def report_year(risk: RiskItem | None) -> int | None:
        if not risk:
            return None
        result = await db.execute(select(Report.fiscal_year).where(Report.id == risk.report_id))
        return result.scalar_one_or_none()

    async def evidence(risk: RiskItem | None) -> RiskEvidence | None:
        item = _build_risk_evidence(risk) if risk else None
        if item:
            item.report_year = await report_year(risk)
        return item

    return EvidenceComparisonResponse(
        risk_id=risk_id,
        change_type=evolution.change_type if evolution else None,
        previous_risk=RiskItemResponse.model_validate(previous) if previous else None,
        current_risk=RiskItemResponse.model_validate(current) if current else None,
        previous_evidence=await evidence(previous),
        current_evidence=await evidence(current),
    )


@router.get("/{company_id}/summary", response_model=EvolutionSummary)
async def get_evolution_summary(
    company_id: UUID,
    year_current: int = Query(...),
    year_previous: int = Query(...),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report_current = await db.execute(
        select(Report).where(
            Report.company_id == company_id,
            Report.fiscal_year == year_current,
        )
    )
    report_current = report_current.scalar_one_or_none()

    report_prev = await db.execute(
        select(Report).where(
            Report.company_id == company_id,
            Report.fiscal_year == year_previous,
        )
    )
    report_prev = report_prev.scalar_one_or_none()

    if not report_current or not report_prev:
        raise HTTPException(status_code=404, detail="Reports not found for both years")

    risks_current = await db.execute(
        select(RiskItem).where(RiskItem.report_id == report_current.id)
    )
    risks_current = risks_current.scalars().all()

    risks_prev = await db.execute(select(RiskItem).where(RiskItem.report_id == report_prev.id))
    risks_prev = risks_prev.scalars().all()

    evolutions = await db.execute(
        select(EvolutionEntry).where(
            EvolutionEntry.risk_item_id_prev.in_([r.id for r in risks_prev])
            | EvolutionEntry.risk_item_id_current.in_([r.id for r in risks_current])
        )
    )
    evolutions = evolutions.scalars().all()

    new_count = sum(1 for e in evolutions if e.change_type == "NEW")
    removed_count = sum(1 for e in evolutions if e.change_type == "REMOVED")
    escalated = sum(1 for e in evolutions if e.change_type == "ESCALATED")
    de_escalated = sum(1 for e in evolutions if e.change_type == "DE-ESCALATED")
    modified = sum(1 for e in evolutions if e.change_type == "MODIFIED")

    current_categories = {}
    for r in risks_current:
        current_categories[r.category] = current_categories.get(r.category, 0) + 1

    prev_categories = {}
    for r in risks_prev:
        prev_categories[r.category] = prev_categories.get(r.category, 0) + 1

    top_new = sorted(current_categories.items(), key=lambda x: x[1], reverse=True)[:5]
    top_removed = sorted(prev_categories.items(), key=lambda x: x[1], reverse=True)[:5]

    return EvolutionSummary(
        company_id=company_id,
        period=f"{year_previous}-{year_current}",
        total_risks_current=len(risks_current),
        total_risks_previous=len(risks_prev),
        net_change=len(risks_current) - len(risks_prev),
        new_risks_count=new_count,
        removed_risks_count=removed_count,
        severity_changes={
            "increased": escalated,
            "decreased": de_escalated,
            "modified": modified,
        },
        top_new_categories=[{"category": c, "count": cnt} for c, cnt in top_new],
        top_removed_categories=[{"category": c, "count": cnt} for c, cnt in top_removed],
        ai_narrative=(
            f"Risk profile evolved from {len(risks_prev)} risks in FY{year_previous} "
            f"to {len(risks_current)} risks in FY{year_current}."
        ),
    )


@router.get("/{company_id}/timeline")
async def get_risk_timeline(
    company_id: UUID,
    category: str | None = Query(None),
    years: int = Query(5, ge=2, le=10),
    db: AsyncSession = Depends(get_db_session),
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query = (
        select(Report.fiscal_year, func.count(RiskItem.id))
        .join(RiskItem, RiskItem.report_id == Report.id)
        .where(Report.company_id == company_id)
        .group_by(Report.fiscal_year)
        .order_by(Report.fiscal_year.desc())
        .limit(years)
    )

    if category:
        query = query.where(RiskItem.category == category)

    result = await db.execute(query)
    timeline = result.all()

    return {"timeline": [{"year": year, "risk_count": count} for year, count in timeline]}
