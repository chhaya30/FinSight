from enum import Enum

from app.config.logging import get_logger
from app.risk_engine.extractor import ExtractedRisk

logger = get_logger(__name__)


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


SEVERITY_WEIGHTS = {
    SeverityLevel.CRITICAL: 5,
    SeverityLevel.HIGH: 4,
    SeverityLevel.MEDIUM: 3,
    SeverityLevel.LOW: 2,
    SeverityLevel.INFORMATIONAL: 1,
}

SEVERITY_DESCRIPTIONS = {
    SeverityLevel.CRITICAL: (
        "Existential threat to business continuity; immediate board attention required"
    ),
    SeverityLevel.HIGH: (
        "Significant impact on financials, operations, or reputation; urgent mitigation needed"
    ),
    SeverityLevel.MEDIUM: "Moderate impact manageable with existing controls; monitoring required",
    SeverityLevel.LOW: "Minor impact; routine monitoring sufficient",
    SeverityLevel.INFORMATIONAL: "Disclosed for transparency; no immediate action required",
}


class SeverityAssessor:
    def __init__(self):
        self.category_severity_bias = {
            "auditor_concern": 1,
            "cyber": 1,
            "liquidity": 1,
            "legal": 0.5,
            "credit": 0.5,
        }

    def assess(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        for risk in risks:
            risk.severity = self._determine_severity(risk)

        logger.info("severity_assessed", count=len(risks))
        return risks

    def _determine_severity(self, risk: ExtractedRisk) -> str:
        base_severity = risk.severity
        bias = self.category_severity_bias.get(risk.category, 0)

        if bias > 0:
            severity_order = list(SeverityLevel)
            current_idx = severity_order.index(SeverityLevel(base_severity))
            new_idx = max(0, current_idx - bias)
            return severity_order[new_idx].value

        return base_severity

    def get_weight(self, severity: str) -> int:
        return SEVERITY_WEIGHTS.get(SeverityLevel(severity), 3)

    def get_description(self, severity: str) -> str:
        return SEVERITY_DESCRIPTIONS.get(SeverityLevel(severity), "")

    def compare_severity(self, severity1: str, severity2: str) -> int:
        order = list(SeverityLevel)
        idx1 = order.index(SeverityLevel(severity1))
        idx2 = order.index(SeverityLevel(severity2))
        return idx1 - idx2


def assess_severity(risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
    assessor = SeverityAssessor()
    return assessor.assess(risks)
