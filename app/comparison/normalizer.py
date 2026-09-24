import uuid
from typing import Any

from app.config.logging import get_logger
from app.models.risk import NormalizedRisk, RiskEvidence
from app.processing.cleaner import clean_text

logger = get_logger(__name__)


def derive_risk_title(text: str, max_words: int = 10) -> str:
    """Derive a clean, concise risk title from text if an explicit title is not provided."""
    if not text:
        return "Untitled Risk"

    cleaned = clean_text(text)
    first_sentence = cleaned.split(".")[0].strip()
    words = first_sentence.split()
    if len(words) <= max_words:
        return first_sentence
    return " ".join(words[:max_words]) + "..."


class RiskNormalizer:
    """Service to normalize extracted risk data into standard canonical NormalizedRisk instances."""

    def __init__(self, embedding_provider: Any | None = None):
        self.embedding_provider = embedding_provider

    def normalize(
        self,
        raw_risk: dict[str, Any] | Any,
        report_year: int,
        company_id: str | None = None,
        report_id: str | None = None,
    ) -> NormalizedRisk:
        """Convert an extracted risk dict, ORM object, or dataclass into a canonical NormalizedRisk."""
        if isinstance(raw_risk, dict):
            return self._normalize_dict(raw_risk, report_year, company_id, report_id)
        elif (
            hasattr(raw_risk, "__dict__")
            or hasattr(raw_risk, "summary")
            or hasattr(raw_risk, "category")
        ):
            return self._normalize_object(raw_risk, report_year, company_id, report_id)
        else:
            raise ValueError(f"Unsupported risk object type for normalization: {type(raw_risk)}")

    def _normalize_dict(
        self,
        data: dict[str, Any],
        report_year: int,
        company_id: str | None = None,
        report_id: str | None = None,
    ) -> NormalizedRisk:
        risk_id = str(data.get("risk_id") or data.get("id") or uuid.uuid4())
        comp_id = str(data.get("company_id") or company_id or "") or None
        rep_id = str(data.get("report_id") or data.get("document_id") or report_id or "") or None
        year = data.get("report_year") or data.get("fiscal_year") or report_year

        category = str(data.get("risk_category") or data.get("category") or "Uncategorized").strip()
        raw_sev = data.get("severity")
        severity = str(raw_sev).strip() if raw_sev is not None and str(raw_sev).strip() else None
        confidence = float(data.get("confidence_score") or data.get("confidence") or 0.8)


        description = str(
            data.get("risk_description")
            or data.get("summary")
            or data.get("text")
            or data.get("source_paragraph")
            or ""
        ).strip()

        raw_title = data.get("risk_title") or data.get("title")
        if raw_title:
            title = str(raw_title).strip()
        else:
            title = derive_risk_title(description)

        likelihood = data.get("likelihood")
        impact = data.get("impact")
        drivers = data.get("drivers") if isinstance(data.get("drivers"), list) else []
        affected_areas = (
            data.get("affected_areas") if isinstance(data.get("affected_areas"), list) else []
        )

        # Evidence construction
        raw_evidence = data.get("evidence")
        source_page = data.get("source_page") or data.get("page")

        if isinstance(raw_evidence, RiskEvidence):
            evidence = raw_evidence
        elif isinstance(raw_evidence, dict):
            evidence = RiskEvidence(
                document_id=str(raw_evidence.get("document_id") or rep_id or ""),
                report_year=raw_evidence.get("report_year") or year,
                page=raw_evidence.get("page") or source_page,
                chunk_id=raw_evidence.get("chunk_id"),
                text=raw_evidence.get("text") or description,
                section=raw_evidence.get("section"),
                text_hash=raw_evidence.get("text_hash"),
                char_start=raw_evidence.get("char_start"),
                char_end=raw_evidence.get("char_end"),
                context_before=raw_evidence.get("context_before"),
                context_after=raw_evidence.get("context_after"),
                metadata=raw_evidence.get("metadata") or {},
            )
        else:
            evidence = RiskEvidence(
                document_id=rep_id,
                report_year=year,
                page=source_page,
                text=description,
                metadata={"category": category, "severity": severity},
            )

        embedding = data.get("embedding")

        return NormalizedRisk(
            risk_id=risk_id,
            company_id=comp_id,
            report_id=rep_id,
            report_year=year,
            category=category,
            title=title,
            description=description,
            severity=severity,
            likelihood=likelihood,
            impact=impact,
            drivers=drivers,
            affected_areas=affected_areas,
            evidence=evidence,
            source_page=source_page if source_page and source_page > 0 else None,
            confidence_score=confidence,
            embedding=embedding,
            extra_metadata=data.get("metadata") or data.get("extra_metadata") or {},
        )

    def _normalize_object(
        self,
        obj: Any,
        report_year: int,
        company_id: str | None = None,
        report_id: str | None = None,
    ) -> NormalizedRisk:
        risk_id = str(getattr(obj, "id", getattr(obj, "risk_id", uuid.uuid4())))
        comp_id = str(getattr(obj, "company_id", company_id or "")) or None
        rep_id = (
            str(getattr(obj, "report_id", getattr(obj, "document_id", report_id or ""))) or None
        )

        category = str(
            getattr(obj, "category", getattr(obj, "risk_category", "Uncategorized"))
        ).strip()
        raw_severity = getattr(obj, "severity", None)
        severity = str(raw_severity).strip() if raw_severity is not None else None
        confidence = float(getattr(obj, "confidence_score", getattr(obj, "confidence", 0.8)))

        description = str(
            getattr(
                obj,
                "summary",
                getattr(obj, "risk_description", getattr(obj, "source_paragraph", "")),
            )
        ).strip()

        title_val = getattr(obj, "title", getattr(obj, "risk_title", None))
        if title_val:
            title = str(title_val).strip()
        else:
            title = derive_risk_title(description)

        source_page = getattr(obj, "source_page", getattr(obj, "page", None))

        evidence_obj = getattr(obj, "evidence", None)
        if isinstance(evidence_obj, RiskEvidence):
            evidence = evidence_obj
        elif isinstance(evidence_obj, dict):
            evidence = RiskEvidence(
                document_id=str(evidence_obj.get("document_id") or rep_id or ""),
                report_year=evidence_obj.get("report_year") or report_year,
                page=evidence_obj.get("page") or source_page,
                chunk_id=evidence_obj.get("chunk_id"),
                text=evidence_obj.get("text") or description,
                section=evidence_obj.get("section"),
                metadata=evidence_obj.get("metadata") or {},
            )
        else:
            evidence = RiskEvidence(
                document_id=rep_id,
                report_year=report_year,
                page=source_page,
                text=description,
                metadata={"category": category, "severity": severity},
            )

        embedding = getattr(obj, "embedding", None)

        return NormalizedRisk(
            risk_id=risk_id,
            company_id=comp_id,
            report_id=rep_id,
            report_year=report_year,
            category=category,
            title=title,
            description=description,
            severity=severity,
            likelihood=getattr(obj, "likelihood", None),
            impact=getattr(obj, "impact", None),
            drivers=getattr(obj, "drivers", []) or [],
            affected_areas=getattr(obj, "affected_areas", []) or [],
            evidence=evidence,
            source_page=source_page if source_page and source_page > 0 else None,
            confidence_score=confidence,
            embedding=embedding,
        )

    async def normalize_batch(
        self,
        raw_risks: list[Any],
        report_year: int,
        company_id: str | None = None,
        report_id: str | None = None,
        generate_embeddings: bool = True,
    ) -> list[NormalizedRisk]:
        """Normalize a list of raw risks and optionally compute vector embeddings."""
        normalized_list = [
            self.normalize(r, report_year=report_year, company_id=company_id, report_id=report_id)
            for r in raw_risks
        ]

        if generate_embeddings and self.embedding_provider:
            texts_to_embed = [f"{r.title}. {r.description}".strip() for r in normalized_list]
            if texts_to_embed:
                try:
                    embeddings = await self.embedding_provider.embed(texts_to_embed)
                    for r, emb in zip(normalized_list, embeddings, strict=False):
                        r.embedding = emb

                except Exception as e:
                    logger.warning("batch_embedding_failed", error=str(e))

        return normalized_list
