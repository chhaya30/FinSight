from fastapi import APIRouter

from app.intelligence.financial_health import FinancialHealthService
from app.models.financial_health import FinancialHealthRequest, FinancialHealthResponse

router = APIRouter()


@router.post("/analyze", response_model=FinancialHealthResponse)
async def analyze_financial_health(
    request: FinancialHealthRequest,
) -> FinancialHealthResponse:
    result = FinancialHealthService().analyze(
        current=request.snapshot_current,
        previous=request.snapshot_previous,
        evolution_records=request.evolution_records,
    )
    return FinancialHealthResponse(**result.model_dump())