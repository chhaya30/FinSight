"""Run Phase 2.1.1-2.1.4 against actual annual-report PDFs."""

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.comparison.evolution import EvolutionSummaryBuilder, RiskEvolutionClassifier
from app.comparison.matcher import SemanticRiskMatcher
from app.comparison.normalizer import RiskNormalizer
from app.ingestion import create_adaptive_fallback_router
from app.models.document import PageContent
from app.processing import find_risk_section
from app.risk_engine import create_pipeline


def extract_risks(pdf_path: Path, report_year: int) -> list[dict]:
    document = create_adaptive_fallback_router().process(pdf_path)
    pages = [
        PageContent(page_number=i + 1, text=page.text, char_count=page.char_count)
        for i, page in enumerate(document.pages)
    ]
    pipeline = create_pipeline()
    risk_section = find_risk_section([page.text for page in pages])
    if risk_section is None:
        raise RuntimeError(f"No risk section found in actual annual report: {pdf_path}")
    candidates = pipeline.detector.detect([risk_section])
    extracted = pipeline.extractor.extract(candidates)
    extracted = pipeline.classifier.classify(extracted)
    extracted = pipeline.confidence_calculator.calculate(extracted)
    extracted = pipeline.deduplicator.deduplicate(extracted)
    if not extracted:
        raise RuntimeError(f"No risks extracted from actual annual report: {pdf_path}")
    risks = []
    for index, risk in enumerate(extracted, start=1):
        risks.append(
            {
                "risk_id": f"{report_year}-{index:04d}",
                "report_id": pdf_path.name,
                "report_year": report_year,
                "category": risk.category,
                "title": risk.summary[:120],
                "summary": risk.summary,
                "severity": risk.severity if risk.severity else None,
                "source_page": risk.candidate.source_page,
                "evidence": {
                    "document_id": pdf_path.name,
                    "report_year": report_year,
                    "page": risk.candidate.source_page,
                    "text": risk.candidate.text,
                    "section": risk.candidate.source_section,
                    "metadata": {"paragraph_index": risk.candidate.paragraph_index},
                },
            }
        )
    return risks


async def main(year_1_file: Path, year_1: int, year_2_file: Path, year_2: int) -> None:
    print("FINSIGHT REAL-DATA SMOKE TEST - PHASE 2.1.1 through 2.1.4")
    y1_raw = extract_risks(year_1_file, year_1)
    y2_raw = extract_risks(year_2_file, year_2)
    normalizer = RiskNormalizer()
    y1 = await normalizer.normalize_batch(y1_raw, report_year=year_1, generate_embeddings=False)
    y2 = await normalizer.normalize_batch(y2_raw, report_year=year_2, generate_embeddings=False)

    from tests.test_phase2_normalization_matching import MockEmbeddingProvider

    matches = await SemanticRiskMatcher(embedding_provider=MockEmbeddingProvider()).match_all_risks(
        y2, y1, y2_year=year_2, y1_year=year_1
    )
    records = RiskEvolutionClassifier().classify_evolution(
        y2, y1, matches, y2_year=year_2, y1_year=year_1
    )
    summary = EvolutionSummaryBuilder().build_summary(
        records, year_1, year_2, len(y1), len(y2)
    )
    matched_unique = sum(
        len(summary.by_status.get(status, []))
        for status in ("UNCHANGED", "MODIFIED", "ESCALATED", "DE-ESCALATED")
    )
    assert len(records) == len(
        {(r.year_1_risk_id, r.year_2_risk_id, r.change_type) for r in records}
    )
    assert summary.total_year_1_risks == matched_unique + summary.removed_count
    assert summary.total_year_2_risks == matched_unique + summary.new_count
    assert all(r.evidence_prev or r.evidence_current for r in records)
    print(f"Extracted risks: Year {year_1}={len(y1)}, Year {year_2}={len(y2)}")
    print(f"Classifications: { {key: len(value) for key, value in summary.by_status.items()} }")
    print(f"Summary counts: Y1={summary.total_year_1_risks}, Y2={summary.total_year_2_risks}, matched={matched_unique}")
    print("REAL-DATA SMOKE TEST PASSED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year-1-file", type=Path, required=True)
    parser.add_argument("--year-1", type=int, required=True)
    parser.add_argument("--year-2-file", type=Path, required=True)
    parser.add_argument("--year-2", type=int, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.year_1_file, args.year_1, args.year_2_file, args.year_2))