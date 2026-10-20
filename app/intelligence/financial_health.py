import re
from collections.abc import Iterable

from app.models.comparison import RiskEvolutionRecord
from app.models.explainability import EvidenceReference
from app.models.financial_health import (
    FinancialMetricChange,
    FinancialMetricValue,
    FinancialSnapshot,
    RiskFinancialCorrelation,
)


class FinancialSnapshotExtractor:
    """Extract explicitly labelled financial values with page-level provenance."""

    ROWS: dict[str, tuple[str, ...]] = {
        "revenue": ("total net revenue", "total revenue", "revenue"),
        "net_income": ("net income", "net profit", "profit after tax"),
        "total_assets": ("total assets",),
        "total_liabilities": ("total liabilities",),
        "cash_and_equivalents": ("cash and cash equivalents",),
        "debt": ("long-term debt", "total debt"),
        "market_cap": ("market capitalization",),
        "eps": ("diluted", "earnings per share"),
        "roe": ("return on common equity", "return on equity"),
        "loans": ("loans",),
        "deposits": ("deposits",),
    }

    def extract(
        self,
        pages: Iterable[str],
        report_year: int,
        document_id: str,
        report_id: str | None = None,
        company_id: str | None = None,
    ) -> FinancialSnapshot:
        metrics: dict[str, FinancialMetricValue] = {}
        for page_number, page_text in enumerate(pages, start=1):
            normalized = " ".join(page_text.split())
            years = self._find_years(normalized, report_year)
            for metric_name, labels in self.ROWS.items():
                if metric_name in metrics:
                    continue
                match = self._find_row(normalized, labels)
                if match is None:
                    continue
                if metric_name == "debt" and re.search(
                    r"long-term debt.{0,40}\bnote\b", match.group(0), re.IGNORECASE
                ):
                    continue
                values = self._numbers_after_label(match.group("tail"))
                if not values:
                    continue
                if metric_name in {"debt", "total_liabilities"} and len(values) < 2:
                    continue
                value = values[0]
                unit = "percent" if metric_name == "roe" else "absolute"
                metrics[metric_name] = FinancialMetricValue(
                    metric_name=metric_name,
                    value=value,
                    unit=unit,
                    report_year=report_year,
                    document_id=document_id,
                    page=page_number,
                    source_text=match.group(0),
                    metadata={"available_years": years},
                )
        return FinancialSnapshot(
            company_id=company_id,
            report_id=report_id,
            report_year=report_year,
            document_id=document_id,
            metrics=metrics,
        )

    @staticmethod
    def _find_years(text: str, report_year: int) -> list[int]:
        header_match = re.search(
            r"(?:year ended|as of or for the year ended).*?((?:20\d{2}\s+){1,3}20\d{2})",
            text,
            re.IGNORECASE,
        )
        if not header_match:
            return []
        years = [int(value) for value in re.findall(r"20\d{2}", header_match.group(1))]
        return years if report_year in years else [report_year]

    @staticmethod
    def _find_row(text: str, labels: tuple[str, ...]) -> re.Match[str] | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        for match in re.finditer(
            rf"(?P<label>\b(?:{label_pattern})\b)(?P<tail>.{{0,180}})",
            text,
            re.IGNORECASE,
        ):
            tail = re.sub(r"^\s*\([a-z]+\)\s*", "", match.group("tail"), flags=re.IGNORECASE)
            tail = tail.lstrip()
            if re.match(r"(?:\$\s*)?-?\d", tail):
                return match
        return None

    @staticmethod
    def _numbers_after_label(text: str) -> list[float]:
        values = []
        for raw in re.findall(r"(?<![A-Za-z])(?:\$\s*)?\(?-?\d[\d,]*(?:\.\d+)?\)?", text):
            cleaned = raw.replace("$", "").replace(",", "").strip()
            negative = cleaned.startswith("(") and cleaned.endswith(")")
            cleaned = cleaned.strip("()")
            try:
                value = float(cleaned)
            except ValueError:
                continue
            values.append(-value if negative else value)
        return values


class FinancialHealthService:
    """Deterministic financial changes and non-causal risk correlation."""

    def analyze(
        self,
        current: FinancialSnapshot,
        previous: FinancialSnapshot | None = None,
        evolution_records: list[RiskEvolutionRecord] | None = None,
    ):
        changes = self.calculate_changes(previous, current) if previous else []
        correlations = self.correlate_risks(
            changes, evolution_records or []
        )
        from app.models.financial_health import FinancialHealthAnalysis

        return FinancialHealthAnalysis(
            snapshot_previous=previous,
            snapshot_current=current,
            changes=changes,
            correlations=correlations,
        )

    def calculate_changes(
        self,
        previous: FinancialSnapshot,
        current: FinancialSnapshot,
    ) -> list[FinancialMetricChange]:
        changes: list[FinancialMetricChange] = []
        for metric_name in sorted(set(previous.metrics) | set(current.metrics)):
            before = previous.metrics.get(metric_name)
            after = current.metrics.get(metric_name)
            previous_value = before.value if before and self._valid(before.value) else None
            current_value = after.value if after and self._valid(after.value) else None
            evidence = self._evidence(before, after)
            if previous_value is None or current_value is None:
                direction = "UNAVAILABLE"
                absolute = None
                percent = None
            else:
                absolute = current_value - previous_value
                percent = (
                    None if previous_value == 0 else round(absolute / abs(previous_value) * 100, 4)
                )
                direction = (
                    "INCREASED"
                    if absolute > 0
                    else "DECREASED"
                    if absolute < 0
                    else "UNCHANGED"
                )
            changes.append(
                FinancialMetricChange(
                    metric_name=metric_name,
                    report_year_prev=previous.report_year,
                    report_year_current=current.report_year,
                    previous_value=previous_value,
                    current_value=current_value,
                    absolute_change=absolute,
                    percent_change=percent,
                    direction=direction,
                    supporting_evidence=evidence,
                )
            )
        return changes

    def correlate_risks(
        self,
        changes: list[FinancialMetricChange],
        records: list[RiskEvolutionRecord],
    ) -> list[RiskFinancialCorrelation]:
        correlations = []
        for record in records:
            risk_text = self._risk_text(record)
            for change in changes:
                keywords = self._keywords(change.metric_name)
                if not any(keyword in risk_text for keyword in keywords):
                    continue
                evidence = change.supporting_evidence + self._risk_evidence(record)
                correlations.append(
                    RiskFinancialCorrelation(
                        risk_item_id_prev=record.year_1_risk_id,
                        risk_item_id_current=record.year_2_risk_id,
                        change_type=record.change_type.value,
                        metric_name=change.metric_name,
                        metric_direction=change.direction,
                        explanation=(
                            f"{change.metric_name} {change.direction.lower()} between the "
                            f"reported years and overlaps with the risk disclosure terms; "
                            "this is an association, not a causal conclusion."
                        ),
                        confidence_score=self._correlation_confidence(change, evidence),
                        supporting_evidence=evidence,
                    )
                )
        return correlations

    @staticmethod
    def _valid(value: float) -> bool:
        return isinstance(value, (int, float)) and value == value and abs(value) != float("inf")

    @staticmethod
    def _evidence(
        previous: FinancialMetricValue | None,
        current: FinancialMetricValue | None,
    ) -> list[EvidenceReference]:
        return [
            EvidenceReference(
                side=side,
                document_id=metric.document_id,
                report_year=metric.report_year,
                page=metric.page,
                text_excerpt=metric.source_text[:500],
            )
            for side, metric in (("year_1", previous), ("year_2", current))
            if metric is not None and metric.document_id and metric.page
        ]

    @staticmethod
    def _risk_evidence(record: RiskEvolutionRecord) -> list[EvidenceReference]:
        evidence = []
        for side, source in (("year_1", record.evidence_prev), ("year_2", record.evidence_current)):
            if source is not None and source.document_id and source.page:
                evidence.append(
                    EvidenceReference(
                        side=side,
                        document_id=source.document_id,
                        report_year=source.report_year,
                        page=source.page,
                        chunk_id=source.chunk_id,
                        text_excerpt=source.text[:500],
                    )
                )
        return evidence

    @staticmethod
    def _risk_text(record: RiskEvolutionRecord) -> str:
        return " ".join(str(value).lower() for value in record.metadata.values())

    @staticmethod
    def _keywords(metric_name: str) -> tuple[str, ...]:
        return {
            "revenue": ("revenue", "sales"),
            "net_income": ("income", "profit", "earnings"),
            "total_assets": ("asset",),
            "total_liabilities": ("liabilit",),
            "cash_and_equivalents": ("cash", "liquidity"),
            "debt": ("debt", "funding", "financing"),
            "market_cap": ("market", "capitalization"),
            "eps": ("eps", "earnings"),
            "roe": ("equity", "profitability"),
            "loans": ("loan", "credit"),
            "deposits": ("deposit",),
        }.get(metric_name, (metric_name.replace("_", " "),))

    @staticmethod
    def _correlation_confidence(
        change: FinancialMetricChange,
        evidence: list[EvidenceReference],
    ) -> float:
        if not evidence or change.direction == "UNAVAILABLE":
            return 0.0
        return 0.75