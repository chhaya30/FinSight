from fastapi import APIRouter, Query

from app.comparison.explainability import ExplainabilityService
from app.llm.explanation_service import LLMExplanationService
from app.models.explainability import ExplainabilityRequest, ExplainabilityResponse

router = APIRouter()


@router.post("/evolution", response_model=ExplainabilityResponse)
async def explain_evolution(request: ExplainabilityRequest) -> ExplainabilityResponse:
    """Return evidence-grounded explanations for Phase 2.1 evolution records."""
    explanations = ExplainabilityService().explain_records(request.records)
    return ExplainabilityResponse(explanations=explanations)


@router.post("/evolution/llm", response_model=ExplainabilityResponse)
async def explain_evolution_with_llm(
    request: ExplainabilityRequest,
    company_name: str = Query("the company"),
) -> ExplainabilityResponse:
    """Generate optional LLM wording while preserving evidence-backed fallback output."""
    explanations = await LLMExplanationService().explain_records(
        request.records, company_name=company_name
    )
    return ExplainabilityResponse(explanations=explanations)
