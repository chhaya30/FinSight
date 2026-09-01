import time
from dataclasses import dataclass
from typing import Any

from app.config.logging import get_logger
from app.models.document import PageContent
from app.processing.chunker import TextChunk
from app.processing.section_detector import DocumentSection, detect_sections
from app.risk_engine.classifier import RiskClassifier
from app.risk_engine.confidence import ConfidenceCalculator
from app.risk_engine.deduplicator import RiskDeduplicator
from app.risk_engine.detector import RiskDetector
from app.risk_engine.evidence import Evidence, EvidenceBuilder
from app.risk_engine.extractor import ExtractedRisk, RiskExtractor
from app.risk_engine.severity import SeverityAssessor

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    risks: list[ExtractedRisk]
    evidence: list[Evidence]
    chunks: list[TextChunk]
    sections: list[DocumentSection]
    processing_time: float
    metadata: dict[str, Any]


class RiskAnalysisPipeline:
    def __init__(
        self,
        detector: RiskDetector | None = None,
        extractor: RiskExtractor | None = None,
        classifier: RiskClassifier | None = None,
        severity_assessor: SeverityAssessor | None = None,
        confidence_calculator: ConfidenceCalculator | None = None,
        deduplicator: RiskDeduplicator | None = None,
        evidence_builder: EvidenceBuilder | None = None,
    ):
        self.detector = detector or RiskDetector()
        self.extractor = extractor or RiskExtractor()
        self.classifier = classifier or RiskClassifier()
        self.severity_assessor = severity_assessor or SeverityAssessor()
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
        self.deduplicator = deduplicator or RiskDeduplicator()
        self.evidence_builder = evidence_builder or EvidenceBuilder()

    def run(
        self, pages: list[PageContent], document_id: str = "", metadata: dict[str, Any] = None
    ) -> PipelineResult:
        start_time = time.time()

        if metadata is None:
            metadata = {}

        logger.info("pipeline_started", document_id=document_id, pages=len(pages))

        sections = detect_sections([p.text for p in pages])
        logger.debug("sections_detected", count=len(sections))

        candidates = self.detector.detect(sections)
        logger.debug("candidates_detected", count=len(candidates))

        risks = self.extractor.extract(candidates)
        logger.debug("risks_extracted", count=len(risks))

        risks = self.classifier.classify(risks)
        logger.debug("risks_classified", count=len(risks))

        risks = self.severity_assessor.assess(risks)
        logger.debug("severity_assessed", count=len(risks))

        risks = self.confidence_calculator.calculate(risks)
        logger.debug("confidence_calculated", count=len(risks))

        risks = self.deduplicator.deduplicate(risks)
        logger.debug("risks_deduplicated", count=len(risks))

        evidence = self.evidence_builder.build_evidence(risks, pages)
        logger.debug("evidence_built", count=len(evidence))

        processing_time = time.time() - start_time

        result = PipelineResult(
            risks=risks,
            evidence=evidence,
            chunks=[],
            sections=sections,
            processing_time=processing_time,
            metadata={
                "document_id": document_id,
                "total_candidates": len(candidates),
                "final_risks": len(risks),
                "processing_time": processing_time,
                **metadata,
            },
        )

        logger.info("pipeline_completed", document_id=document_id, **result.metadata)
        return result

    def run_on_chunks(self, chunks: list[TextChunk]) -> list[ExtractedRisk]:
        all_risks = []

        for chunk in chunks:
            candidates = self.detector.detect_from_text(chunk.text)
            risks = self.extractor.extract(candidates)
            risks = self.classifier.classify(risks)
            risks = self.severity_assessor.assess(risks)
            risks = self.confidence_calculator.calculate(risks)
            all_risks.extend(risks)

        all_risks = self.deduplicator.deduplicate(all_risks)
        return all_risks


def create_pipeline(**kwargs) -> RiskAnalysisPipeline:
    return RiskAnalysisPipeline(**kwargs)


async def run_risk_analysis(
    pages: list[PageContent], document_id: str = "", metadata: dict[str, Any] = None
) -> PipelineResult:
    pipeline = create_pipeline()
    return pipeline.run(pages, document_id, metadata)
