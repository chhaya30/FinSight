from app.models.document import PageContent
from app.risk_engine import create_pipeline
from app.risk_engine.detector import RiskCandidate
from app.risk_engine.extractor import ExtractedRisk
from app.risk_engine.severity import SeverityAssessor


def test_phase2_pipeline_returns_after_classification_and_evidence():
    result = create_pipeline().run(
        [PageContent(
            page_number=1,
            text=(
                "RISK FACTORS\n\n"
                "The company may face significant cyber security threats and a material "
                "adverse impact if controls fail. This risk could disrupt operations."
            ),
            char_count=150,
        )],
        document_id="pipeline-log-regression",
    )
    assert result.risks
    assert result.evidence


def test_phase2_fractional_category_severity_bias_uses_discrete_level():
    risk = ExtractedRisk(
        candidate=RiskCandidate(text="A material risk", source_section="Risk Factors", source_page=1, paragraph_index=0),
        category="legal",
        severity="low",
    )
    assessed = SeverityAssessor().assess([risk])
    assert assessed[0].severity == "medium"
