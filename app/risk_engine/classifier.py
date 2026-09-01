from app.config.logging import get_logger
from app.risk_engine.extractor import ExtractedRisk
from app.taxonomy.classifier_rules import RuleBasedClassifier, SeverityRules
from app.taxonomy.loader import get_taxonomy

logger = get_logger(__name__)


class RiskClassifier:
    def __init__(self):
        self.taxonomy = get_taxonomy()
        self.rule_classifier = RuleBasedClassifier()

    def classify(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        for risk in risks:
            risk.category = self._refine_category(risk)
            risk.severity = self._refine_severity(risk)
            risk.confidence_score = self._calibrate_confidence(risk)

        logger.info("risks_classified", count=len(risks))
        return risks

    def _refine_category(self, risk: ExtractedRisk) -> str:
        scores = self.rule_classifier.classify(risk.candidate.text)

        if scores:
            top_category = max(scores, key=scores.get)
            if scores[top_category] > 1.0:
                return top_category

        matches = self.taxonomy.match_category(risk.candidate.text, threshold=1)
        if matches:
            return matches[0]

        return risk.category

    def _refine_severity(self, risk: ExtractedRisk) -> str:
        return SeverityRules.classify_severity(risk.candidate.text, risk.category)

    def _calibrate_confidence(self, risk: ExtractedRisk) -> float:
        confidence = risk.confidence_score

        category_match = self._check_category_consistency(risk)
        if category_match:
            confidence += 0.1

        severity_match = self._check_severity_consistency(risk)
        if severity_match:
            confidence += 0.05

        entity_bonus = min(len(risk.entities) * 0.02, 0.1)
        confidence += entity_bonus

        return min(confidence, 1.0)

    def _check_category_consistency(self, risk: ExtractedRisk) -> bool:
        scores = self.rule_classifier.classify(risk.candidate.text)
        return risk.category in scores and scores[risk.category] > 0.5

    def _check_severity_consistency(self, risk: ExtractedRisk) -> bool:
        severity_keywords = {
            "critical": ["existential", "bankruptcy", "going concern", "material weakness"],
            "high": ["significant", "material", "substantial", "major", "severe"],
            "medium": ["moderate", "potential", "possible", "may impact"],
            "low": ["minor", "limited", "minimal", "unlikely"],
            "informational": ["disclosed for transparency", "no impact"],
        }
        keywords = severity_keywords.get(risk.severity, [])
        text_lower = risk.candidate.text.lower()
        return any(kw in text_lower for kw in keywords)


class LLMBasedRiskClassifier(RiskClassifier):
    def __init__(self, llm_client=None):
        super().__init__()
        self.llm_client = llm_client

    def classify(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        if self.llm_client:
            return self._classify_with_llm(risks)
        return super().classify(risks)

    def _classify_with_llm(self, risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
        return super().classify(risks)


def classify_risks(risks: list[ExtractedRisk]) -> list[ExtractedRisk]:
    classifier = RiskClassifier()
    return classifier.classify(risks)
