from typing import Any

from app.config.logging import get_logger
from app.risk_engine.extractor import ExtractedRisk

logger = get_logger(__name__)


class ConfidenceCalculator:
    def __init__(
        self,
        base_weight: float = 0.4,
        category_weight: float = 0.2,
        severity_weight: float = 0.15,
        entity_weight: float = 0.15,
        length_weight: float = 0.1,
    ):
        self.weights = {
            "base": base_weight,
            "category": category_weight,
            "severity": severity_weight,
            "entity": entity_weight,
            "length": length_weight,
        }

    def calculate(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        for risk in risks:
            risk.confidence_score = self._compute_confidence(risk)
            risk.metadata["confidence_breakdown"] = self._get_breakdown(risk)

        logger.info("confidence_calculated", count=len(risks))
        return risks

    def _compute_confidence(self, risk: ExtractedRisk) -> float:
        base_score = risk.candidate.confidence

        category_score = 1.0 if risk.category != "general" else 0.5

        severity_score = self._severity_to_score(risk.severity)

        entity_score = min(len(risk.entities) / 5.0, 1.0)

        length_score = min(len(risk.candidate.text) / 1000.0, 1.0)

        confidence = (
            base_score * self.weights["base"]
            + category_score * self.weights["category"]
            + severity_score * self.weights["severity"]
            + entity_score * self.weights["entity"]
            + length_score * self.weights["length"]
        )

        return min(max(confidence, 0.0), 1.0)

    def _severity_to_score(self, severity: str) -> float:
        mapping = {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "informational": 0.2,
        }
        return mapping.get(severity, 0.5)

    def _get_breakdown(self, risk: ExtractedRisk) -> dict[str, float]:
        base_score = risk.candidate.confidence
        category_score = 1.0 if risk.category != "general" else 0.5
        severity_score = self._severity_to_score(risk.severity)
        entity_score = min(len(risk.entities) / 5.0, 1.0)
        length_score = min(len(risk.candidate.text) / 1000.0, 1.0)

        return {
            "base": base_score * self.weights["base"],
            "category": category_score * self.weights["category"],
            "severity": severity_score * self.weights["severity"],
            "entity": entity_score * self.weights["entity"],
            "length": length_score * self.weights["length"],
            "total": risk.confidence_score,
        }


class ConfidenceCalibrator:
    def __init__(self):
        self.calibration_data = {}

    def calibrate(
        self,
        risks: list[ExtractedRisk],
        ground_truth: list[dict[str, Any]] = None,
    ) -> list[ExtractedRisk]:
        if ground_truth:
            self._learn_calibration(ground_truth)

        for risk in risks:
            risk.confidence_score = self._apply_calibration(risk.confidence_score)

        return risks

    def _learn_calibration(self, ground_truth: list[dict[str, Any]]):
        pass

    def _apply_calibration(self, confidence: float) -> float:
        return confidence


def calculate_confidence(risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
    calculator = ConfidenceCalculator()
    return calculator.calculate(risks)
