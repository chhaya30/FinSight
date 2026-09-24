from fastapi import APIRouter

from app.comparison.explainability import ExplainabilityService
from app.models.explainability import ExplainabilityRequest, ExplainabilityResponse

router = APIRouter()


@router.post("/evolution", response_model=ExplainabilityResponse)
async def explain_evolution(request: ExplainabilityRequest) -> ExplainabilityResponse:
    """Return evidence-grounded explanations for Phase 2.1 evolution records."""
    explanations = ExplainabilityService().explain_records(request.records)
    return ExplainabilityResponse(explanations=explanations)