import pytest

from app.comparison.evolution import EvolutionSummaryBuilder, RiskEvolutionClassifier
from app.comparison.matcher import SemanticRiskMatcher
from app.comparison.normalizer import RiskNormalizer
from app.models.comparison import CandidateMatch, EvolutionChangeType, RiskMatchResult
from app.models.risk import NormalizedRisk, RiskEvidence
from tests.test_phase2_normalization_matching import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_evolution_case_1_new_risk():
    """Test unmatched Year-2 risk is classified as NEW."""
    normalizer = RiskNormalizer()
    y1_risks = [normalizer.normalize({"risk_id": "y1-1", "title": "Cybersecurity risk", "summary": "Data breach"}, 2024)]
    y2_risks = [
        normalizer.normalize({"risk_id": "y2-1", "title": "Cybersecurity risk", "summary": "Data breach"}, 2025),
        normalizer.normalize({"risk_id": "y2-new", "title": "Climate change tax", "summary": "Carbon regulation tax"}, 2025),
    ]

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks(y2_risks, y1_risks, y2_year=2025, y1_year=2024)

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution(y2_risks, y1_risks, matches, y2_year=2025, y1_year=2024)

    new_rec = next((r for r in records if r.year_2_risk_id == "y2-new"), None)
    assert new_rec is not None
    assert new_rec.change_type == EvolutionChangeType.NEW
    assert new_rec.year_1_risk_id is None


@pytest.mark.asyncio
async def test_evolution_case_2_removed_risk():
    """Test unmatched Year-1 risk is classified as REMOVED."""
    normalizer = RiskNormalizer()
    y1_risks = [
        normalizer.normalize({"risk_id": "y1-1", "title": "Cybersecurity risk", "summary": "Data breach"}, 2024),
        normalizer.normalize({"risk_id": "y1-removed", "title": "Legacy software risk", "summary": "Old mainframe deprecation"}, 2024),
    ]
    y2_risks = [
        normalizer.normalize({"risk_id": "y2-1", "title": "Cybersecurity risk", "summary": "Data breach"}, 2025),
    ]

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks(y2_risks, y1_risks, y2_year=2025, y1_year=2024)

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution(y2_risks, y1_risks, matches, y2_year=2025, y1_year=2024)

    rem_rec = next((r for r in records if r.year_1_risk_id == "y1-removed"), None)
    assert rem_rec is not None
    assert rem_rec.change_type == EvolutionChangeType.REMOVED
    assert rem_rec.year_2_risk_id is None


@pytest.mark.asyncio
async def test_evolution_case_3_unchanged_risk():
    """Test identical matched risk is classified as UNCHANGED."""
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize({"risk_id": "r1", "category": "Cyber", "severity": "High", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2024)
    y2 = normalizer.normalize({"risk_id": "r2", "category": "Cyber", "severity": "High", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2025)

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks([y2], [y1])

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution([y2], [y1], matches)

    assert len(records) == 1
    assert records[0].change_type == EvolutionChangeType.UNCHANGED


@pytest.mark.asyncio
async def test_evolution_case_4_escalated_high_to_critical():
    """Test High -> Critical structured severity shift triggers ESCALATED."""
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize({"risk_id": "r1", "severity": "High", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2024)
    y2 = normalizer.normalize({"risk_id": "r2", "severity": "Critical", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2025)

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks([y2], [y1])

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution([y2], [y1], matches)

    assert len(records) == 1
    assert records[0].change_type == EvolutionChangeType.ESCALATED
    assert records[0].severity_prev == "High"
    assert records[0].severity_current == "Critical"
    assert "severity" in records[0].changed_attributes


@pytest.mark.asyncio
async def test_evolution_case_5_deescalated_critical_to_high():
    """Test Critical -> High structured severity shift triggers DE-ESCALATED."""
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize({"risk_id": "r1", "severity": "Critical", "title": "Cyber Risk", "summary": "Cyber breach"}, 2024)
    y2 = normalizer.normalize({"risk_id": "r2", "severity": "High", "title": "Cyber Risk", "summary": "Cyber breach"}, 2025)

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks([y2], [y1])

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution([y2], [y1], matches)

    assert len(records) == 1
    assert records[0].change_type == EvolutionChangeType.DE_ESCALATED
    assert records[0].severity_prev == "Critical"
    assert records[0].severity_current == "High"


@pytest.mark.asyncio
async def test_title_wording_change_alone_causes_modified_not_escalated():
    """Test title wording changes alone yield MODIFIED, never ESCALATED or DE-ESCALATED."""
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize({"risk_id": "r1", "severity": "High", "title": "Supply Chain Bottlenecks", "summary": "Vendor disruption"}, 2024)
    y2 = normalizer.normalize({"risk_id": "r2", "severity": "High", "title": "Global Supply Chain & Geopolitical Disruption", "summary": "Vendor disruption"}, 2025)

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks([y2], [y1])

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution([y2], [y1], matches)

    assert len(records) == 1
    assert records[0].change_type == EvolutionChangeType.MODIFIED
    assert records[0].change_type != EvolutionChangeType.ESCALATED
    assert "title" in records[0].changed_attributes


@pytest.mark.asyncio
async def test_missing_severity_does_not_invent_escalation():
    """Test missing severity values yield MODIFIED or UNCHANGED, never ESCALATED."""
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize({"risk_id": "r1", "severity": "High", "title": "Cyber Risk", "summary": "Cyber breach"}, 2024)
    y2 = normalizer.normalize({"risk_id": "r2", "severity": "", "title": "Cyber Security Risk", "summary": "Cyber breach"}, 2025)

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks([y2], [y1])

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution([y2], [y1], matches)

    assert len(records) == 1
    assert records[0].change_type in (EvolutionChangeType.MODIFIED, EvolutionChangeType.UNCHANGED)
    assert records[0].change_type != EvolutionChangeType.ESCALATED


@pytest.mark.asyncio
async def test_one_to_one_matching_prevents_duplicate_classifications():
    """Test greedy 1-to-1 match resolution prevents assigning a single Year-1 risk to multiple Year-2 risks."""
    normalizer = RiskNormalizer()
    y1_list = [normalizer.normalize({"risk_id": "y1-shared", "title": "Supply Chain Risk", "summary": "Vendor issue"}, 2024)]
    y2_list = [
        normalizer.normalize({"risk_id": "y2-a", "title": "Supply Chain Risk A", "summary": "Vendor issue"}, 2025),
        normalizer.normalize({"risk_id": "y2-b", "title": "Supply Chain Risk B", "summary": "Vendor issue"}, 2025),
    ]

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks(y2_list, y1_list)

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution(y2_list, y1_list, matches)

    # Exactly 2 records for 2 Year-2 risks
    assert len(records) == 2
    y1_matches = [r for r in records if r.year_1_risk_id == "y1-shared"]
    # Only 1 Year-2 risk gets paired with y1-shared; the other gets NEW
    assert len(y1_matches) == 1
    new_records = [r for r in records if r.change_type == EvolutionChangeType.NEW]
    assert len(new_records) == 1


@pytest.mark.asyncio
async def test_summary_counts_equal_underlying_records():
    """Test summary statistics match exact record counts and satisfy invariants."""
    normalizer = RiskNormalizer()
    y1_risks = [
        normalizer.normalize({"risk_id": "y1-1", "severity": "High", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2024),
        normalizer.normalize({"risk_id": "y1-2", "severity": "High", "title": "Supply Chain", "summary": "Vendor issue"}, 2024),
        normalizer.normalize({"risk_id": "y1-removed", "title": "Legacy IT", "summary": "Old system"}, 2024),
    ]
    y2_risks = [
        normalizer.normalize({"risk_id": "y2-1", "severity": "Critical", "title": "Cyber Risk", "summary": "Cyber security breach"}, 2025), # ESCALATED
        normalizer.normalize({"risk_id": "y2-2", "severity": "High", "title": "Global Supply Chain & Vendor Risk", "summary": "Vendor issue"}, 2025), # MODIFIED
        normalizer.normalize({"risk_id": "y2-new", "title": "Climate Regulation", "summary": "ESG tax"}, 2025), # NEW
    ]

    provider = MockEmbeddingProvider()
    matcher = SemanticRiskMatcher(embedding_provider=provider)
    matches = await matcher.match_all_risks(y2_risks, y1_risks)

    classifier = RiskEvolutionClassifier()
    records = classifier.classify_evolution(y2_risks, y1_risks, matches)

    builder = EvolutionSummaryBuilder()
    summary = builder.build_summary(records, y1_year=2024, y2_year=2025, total_y1_count=len(y1_risks), total_y2_count=len(y2_risks))

    assert summary.total_year_1_risks == 3
    assert summary.total_year_2_risks == 3
    assert summary.escalated_count == 1
    assert summary.modified_count == 1
    assert summary.new_count == 1
    assert summary.removed_count == 1
    assert summary.unchanged_count == 0
    assert summary.de_escalated_count == 0

    # Test exact summary arithmetic invariants
    assert summary.total_year_1_risks == (summary.unchanged_count + summary.modified_count + summary.escalated_count + summary.de_escalated_count + summary.removed_count)
    assert summary.total_year_2_risks == (summary.unchanged_count + summary.modified_count + summary.escalated_count + summary.de_escalated_count + summary.new_count)


def test_likelihood_change_uses_same_ordered_classification():
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize(
        {"risk_id": "r1", "severity": "High", "likelihood": "LOW", "title": "Risk", "summary": "Exposure"},
        2024,
    )
    y2 = normalizer.normalize(
        {"risk_id": "r2", "severity": "High", "likelihood": "HIGH", "title": "Risk", "summary": "Exposure"},
        2025,
    )
    matches = [
        RiskMatchResult(
            year_2_risk_id="r2",
            candidate_matches=[
                CandidateMatch(year_1_risk_id="r1", semantic_similarity=1, match_confidence=1)
            ],
        )
    ]

    record = RiskEvolutionClassifier().classify_evolution([y2], [y1], matches)[0]

    assert record.change_type == EvolutionChangeType.ESCALATED
    assert record.changed_attributes["likelihood"].before == "LOW"


def test_conflicting_dimensions_are_modified_deterministically():
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize(
        {"risk_id": "r1", "severity": "High", "impact": "HIGH", "title": "Risk", "summary": "Exposure"},
        2024,
    )
    y2 = normalizer.normalize(
        {"risk_id": "r2", "severity": "Critical", "impact": "LOW", "title": "Risk", "summary": "Exposure"},
        2025,
    )
    matches = [
        RiskMatchResult(
            year_2_risk_id="r2",
            candidate_matches=[
                CandidateMatch(year_1_risk_id="r1", semantic_similarity=1, match_confidence=1)
            ],
        )
    ]

    record = RiskEvolutionClassifier().classify_evolution([y2], [y1], matches)[0]

    assert record.change_type == EvolutionChangeType.MODIFIED
    assert set(record.changed_attributes) == {"severity", "impact"}


def test_evolution_preserves_report_and_evidence_references():
    normalizer = RiskNormalizer()
    y1 = normalizer.normalize(
        {
            "risk_id": "r1",
            "report_id": "report-2024",
            "title": "Risk",
            "summary": "Exposure",
            "source_page": 12,
            "evidence": {
                "document_id": "doc-2024",
                "report_year": 2024,
                "page": 12,
                "chunk_id": "chunk-1",
                "text": "Exposure",
            },
        },
        2024,
    )
    y2 = normalizer.normalize(
        {
            "risk_id": "r2",
            "report_id": "report-2025",
            "title": "Risk",
            "summary": "Exposure",
            "source_page": 24,
            "evidence": {
                "document_id": "doc-2025",
                "report_year": 2025,
                "page": 24,
                "chunk_id": "chunk-2",
                "text": "Exposure",
            },
        },
        2025,
    )
    matches = [
        RiskMatchResult(
            year_2_risk_id="r2",
            candidate_matches=[
                CandidateMatch(year_1_risk_id="r1", semantic_similarity=1, match_confidence=1)
            ],
        )
    ]

    record = RiskEvolutionClassifier().classify_evolution([y2], [y1], matches)[0]

    assert record.report_id_prev == "report-2024"
    assert record.report_id_current == "report-2025"
    assert record.evidence_prev.page == 12
    assert record.evidence_prev.chunk_id == "chunk-1"
    assert record.evidence_current.page == 24
    assert record.evidence_current.chunk_id == "chunk-2"
