from app.intelligence.classification_confidence import assess_classification_confidence


def test_assessment_is_deterministic_and_uses_phase2_category_and_severity_rules():
    args = dict(
        category="cyber", severity="high", stored_confidence=0.9,
        evidence_text=("A significant cybersecurity breach could expose sensitive customer data "
                       "and create substantial operational and regulatory consequences. "
                       "The company maintains incident response controls, but a disruption may "
                       "affect customer services, require remediation, and result in additional "
                       "oversight, reporting, and recovery costs across affected business units."),
        source_document="annual-report.pdf", page=42,
    )
    first = assess_classification_confidence(**args)
    second = assess_classification_confidence(**args)
    assert first == second
    assert first.category > 0.6
    assert first.severity > 0.6
    assert first.classification <= args["stored_confidence"]
    assert first.evidence_quality > 0.8
    assert first.low_confidence is False


def test_missing_or_weak_evidence_is_zero_or_low_and_never_fabricates_confidence():
    missing = assess_classification_confidence(
        category="credit", severity="high", stored_confidence=None,
        evidence_text=None, source_document=None, page=None,
    )
    assert missing.category == missing.severity == missing.classification == 0
    assert missing.evidence_quality == 0
    assert missing.low_confidence is True
    assert "No source text" in missing.reason

    weak = assess_classification_confidence(
        category="credit", severity="critical", stored_confidence=0.9,
        evidence_text="Risk may occur.", source_document=None, page=None,
    )
    assert weak.evidence_quality < 0.1
    assert weak.classification < 0.1
    assert weak.low_confidence is True

    unlabeled = assess_classification_confidence(
        category=None, severity=None, stored_confidence=float("nan"),
        evidence_text="A documented risk exposure with supporting disclosure text.",
        source_document="report.pdf", page=12,
    )
    assert unlabeled.category == 0
    assert unlabeled.severity == 0
    assert unlabeled.classification == 0
    assert unlabeled.low_confidence is True
