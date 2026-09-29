from app.api.routes._phase2_helpers import load_phase2_records
from app.models.comparison import RiskEvolutionRecord


async def compare_report_risks(
    previous_report, current_report, previous_risks, current_risks, include_financial=False
):
    """Use the Phase 2 comparison, explainability, and financial services for a report pair."""
    return await load_phase2_records(
        previous_report, current_report, previous_risks, current_risks,
        include_financial=include_financial,
    )


def evolution_by_risk_id(records: list[RiskEvolutionRecord]) -> dict[str, RiskEvolutionRecord]:
    """Index matched and unmatched evolution records under each present risk ID."""
    indexed: dict[str, RiskEvolutionRecord] = {}
    for record in records:
        for risk_id in (record.year_1_risk_id, record.year_2_risk_id):
            if risk_id is not None:
                indexed[risk_id] = record
    return indexed
