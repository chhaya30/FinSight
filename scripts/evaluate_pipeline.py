#!/usr/bin/env python3
"""Script to evaluate the risk extraction pipeline."""

import asyncio
import argparse
import json
from pathlib import Path
from uuid import UUID

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Report, RiskItem
from app.taxonomy import get_taxonomy, validate_risk_item

logger = get_logger(__name__)


async def evaluate_pipeline(
    report_id: UUID = None,
    output_file: Path = None,
):
    settings = get_settings()
    setup_logging()

    await init_db()

    taxonomy = get_taxonomy()
    validator = taxonomy

    async with db.session() as session:
        if report_id:
            reports = [await session.get(Report, report_id)]
        else:
            result = await session.execute(
                select(Report).where(Report.processing_status == "completed")
            )
            reports = result.scalars().all()

        all_results = []

        for report in reports:
            if not report:
                continue

            logger.info("evaluating_report", report_id=str(report.id))

            result = await session.execute(
                select(RiskItem).where(RiskItem.report_id == report.id)
            )
            risks = result.scalars().all()

            report_results = {
                "report_id": str(report.id),
                "company_id": str(report.company_id),
                "fiscal_year": report.fiscal_year,
                "total_risks": len(risks),
                "validation_errors": [],
                "category_distribution": {},
                "severity_distribution": {},
                "confidence_stats": {
                    "min": 1.0,
                    "max": 0.0,
                    "avg": 0.0,
                },
            }

            if risks:
                confidences = [r.confidence_score for r in risks]
                result["confidence_stats"]["min"] = min(confidences)
                result["confidence_stats"]["max"] = max(confidences)
                result["confidence_stats"]["avg"] = sum(confidences) / len(confidences)

                for risk in risks:
                    risk_data = {
                        "category": risk.category,
                        "severity": risk.severity,
                        "confidence_score": risk.confidence_score,
                        "summary": risk.summary,
                    }
                    errors = validate_risk_item(risk_data)
                    if errors:
                        result["validation_errors"].append({
                            "risk_id": str(risk.id),
                            "errors": errors,
                        })

                    result["category_distribution"][risk.category] = \
                        result["category_distribution"].get(risk.category, 0) + 1
                    result["severity_distribution"][risk.severity] = \
                        result["severity_distribution"].get(risk.severity, 0) + 1

            all_results.append(report_results)

        if output_file:
            with open(output_file, "w") as f:
                json.dump(all_results, f, indent=2)
            logger.info("evaluation_saved", file=str(output_file))
        else:
            print(json.dumps(all_results, indent=2))

    await db.close()


def main():
    parser = argparse.ArgumentParser(description="Evaluate risk extraction pipeline")
    parser.add_argument("--report-id", type=UUID, help="Specific report ID to evaluate")
    parser.add_argument("--output", type=Path, help="Output JSON file")

    args = parser.parse_args()

    asyncio.run(evaluate_pipeline(args.report_id, args.output))


if __name__ == "__main__":
    main()