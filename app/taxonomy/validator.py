from typing import Any

from app.config.logging import get_logger
from app.taxonomy.loader import RiskTaxonomy, get_taxonomy

logger = get_logger(__name__)


class TaxonomyValidator:
    def __init__(self, taxonomy: RiskTaxonomy | None = None):
        self.taxonomy = taxonomy or get_taxonomy()

    def validate_category(self, category: str) -> bool:
        return category in self.taxonomy.categories

    def validate_severity(self, severity: str) -> bool:
        return severity in self.taxonomy.severity_levels

    def validate_risk_item(self, risk_data: dict[str, Any]) -> list[str]:
        errors = []

        if not risk_data.get("category") or not self.validate_category(risk_data["category"]):
            errors.append(f"Invalid category: {risk_data.get('category')}")

        if not risk_data.get("severity") or not self.validate_severity(risk_data["severity"]):
            errors.append(f"Invalid severity: {risk_data.get('severity')}")

        confidence = risk_data.get("confidence_score")
        if confidence is None or not (0 <= confidence <= 1):
            errors.append(f"Invalid confidence_score: {confidence}")

        if not risk_data.get("summary") or len(risk_data["summary"].strip()) < 10:
            errors.append("Summary too short or missing")

        return errors

    def validate_taxonomy_consistency(self) -> list[str]:
        errors = []

        for cat_id, category in self.taxonomy.categories.items():
            if not category.get("name"):
                errors.append(f"Category {cat_id} missing name")
            if not category.get("description"):
                errors.append(f"Category {cat_id} missing description")

        for sev_id, severity in self.taxonomy.severity_levels.items():
            if not severity.get("weight"):
                errors.append(f"Severity {sev_id} missing weight")
            if not severity.get("description"):
                errors.append(f"Severity {sev_id} missing description")

        for cat_id, keywords in self.taxonomy.keywords.items():
            if cat_id not in self.taxonomy.categories:
                errors.append(f"Keywords for unknown category: {cat_id}")
            if not keywords:
                errors.append(f"Category {cat_id} has no keywords")

        return errors

    def suggest_category(self, text: str, top_k: int = 3) -> list[dict[str, Any]]:
        matches = self.taxonomy.match_category(text, threshold=1)
        suggestions = []

        for cat_id in matches:
            cat = self.taxonomy.get_category(cat_id)
            keywords = self.taxonomy.get_category_keywords(cat_id)
            matched_keywords = [kw for kw in keywords if kw.lower() in text.lower()]

            suggestions.append(
                {
                    "category": cat_id,
                    "name": cat.get("name") if cat else cat_id,
                    "matched_keywords": matched_keywords,
                    "match_count": len(matched_keywords),
                }
            )

        suggestions.sort(key=lambda x: x["match_count"], reverse=True)
        return suggestions[:top_k]

    def suggest_severity(self, text: str, category: str = None) -> str:
        severity_indicators = {
            "critical": [
                "existential",
                "bankruptcy",
                "going concern",
                "material weakness",
                "catastrophic",
            ],
            "high": [
                "significant",
                "material",
                "substantial",
                "major",
                "severe",
                "critical impact",
            ],
            "medium": [
                "moderate",
                "potential",
                "possible",
                "may impact",
                "could affect",
            ],
            "low": ["minor", "limited", "minimal", "unlikely", "remote"],
            "informational": ["disclosed for transparency", "no impact", "routine"],
        }

        text_lower = text.lower()
        scores = {}

        for severity, indicators in severity_indicators.items():
            scores[severity] = sum(1 for ind in indicators if ind in text_lower)

        if not any(scores.values()):
            return "medium"

        return max(scores, key=scores.get)


def validate_taxonomy() -> list[str]:
    validator = TaxonomyValidator()
    return validator.validate_taxonomy_consistency()


def validate_risk_item(risk_data: dict[str, Any]) -> list[str]:
    validator = TaxonomyValidator()
    return validator.validate_risk_item(risk_data)
