#!/usr/bin/env python3
"""Audit existing database data for invalid values."""

import asyncio
from sqlalchemy import select, func, text
from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import (
    Company,
    Report,
    RiskItem,
    RiskCategory,
    EvolutionEntry,
    FinancialSnapshot,
)

logger = get_logger(__name__)


async def audit_data():
    settings = get_settings()
    setup_logging()
    await init_db()

    async with db.session() as session:
        print("=" * 80)
        print("DATA AUDIT REPORT")
        print("=" * 80)

        # 1. Report processing statuses
        print("\n1. REPORT PROCESSING STATUSES")
        print("-" * 40)
        result = await session.execute(
            select(Report.processing_status, func.count(Report.id))
            .group_by(Report.processing_status)
        )
        valid_statuses = {"uploaded", "queued", "processing", "completed", "failed", "ocr_required", "processed", "cancelled"}
        for status, count in result.all():
            status_str = status or "NULL"
            flag = " ⚠️ INVALID" if status_str not in valid_statuses else ""
            print(f"  {status_str}: {count}{flag}")

        # 2. Report types
        print("\n2. REPORT TYPES")
        print("-" * 40)
        result = await session.execute(
            select(Report.report_type, func.count(Report.id))
            .group_by(Report.report_type)
        )
        valid_types = {"annual_report", "10-K", "20-F", "10-Q", "SEBI_FILING", "BSE_FILING", "NSE_FILING", "OTHER"}
        for rtype, count in result.all():
            rtype_str = rtype or "NULL"
            flag = " ⚠️ INVALID" if rtype_str not in valid_types else ""
            print(f"  {rtype_str}: {count}{flag}")

        # 3. Exchanges (listed_exchange on companies)
        print("\n3. EXCHANGES (companies.listed_exchange)")
        print("-" * 40)
        result = await session.execute(
            select(Company.listed_exchange, func.count(Company.id))
            .group_by(Company.listed_exchange)
        )
        valid_exchanges = {"NSE", "BSE", "NYSE", "NASDAQ", "LSE", "OTHER", None}
        for exchange, count in result.all():
            exchange_str = exchange or "NULL"
            flag = " ⚠️ INVALID" if exchange not in valid_exchanges else ""
            print(f"  {exchange_str}: {count}{flag}")

        # 4. Risk severity and review status
        print("\n4. RISK SEVERITY (1-5)")
        print("-" * 40)
        result = await session.execute(
            select(RiskItem.severity, func.count(RiskItem.id))
            .group_by(RiskItem.severity)
        )
        for sev, count in result.all():
            flag = " ⚠️ OUT OF RANGE" if sev and (sev < 1 or sev > 5) else ""
            print(f"  {sev}: {count}{flag}")

        print("\n   RISK SEVERITY_LABEL")
        print("-" * 40)
        result = await session.execute(
            select(RiskItem.severity_label, func.count(RiskItem.id))
            .group_by(RiskItem.severity_label)
        )
        valid_labels = {"LOW", "MEDIUM", "HIGH", "CRITICAL", None}
        for label, count in result.all():
            label_str = label or "NULL"
            flag = " ⚠️ INVALID" if label not in valid_labels else ""
            print(f"  {label_str}: {count}{flag}")

        print("\n   RISK REVIEW STATUS")
        print("-" * 40)
        result = await session.execute(
            select(RiskItem.review_status, func.count(RiskItem.id))
            .group_by(RiskItem.review_status)
        )
        valid_review = {"pending", "reviewed", "approved", "rejected"}
        for status, count in result.all():
            status_str = status or "NULL"
            flag = " ⚠️ INVALID" if status_str not in valid_review else ""
            print(f"  {status_str}: {count}{flag}")

        # 5. Extraction methods
        print("\n5. EXTRACTION METHODS")
        print("-" * 40)
        result = await session.execute(
            select(RiskItem.extraction_method, func.count(RiskItem.id))
            .group_by(RiskItem.extraction_method)
        )
        valid_methods = {"LLM", "RULE", "HYBRID", "HUMAN", None}
        for method, count in result.all():
            method_str = method or "NULL"
            flag = " ⚠️ INVALID" if method not in valid_methods else ""
            print(f"  {method_str}: {count}{flag}")

        # 6. Risk evolution change types
        print("\n6. EVOLUTION CHANGE TYPES")
        print("-" * 40)
        result = await session.execute(
            select(EvolutionEntry.change_type, func.count(EvolutionEntry.id))
            .group_by(EvolutionEntry.change_type)
        )
        valid_changes = {"NEW", "REMOVED", "SEVERITY_UP", "SEVERITY_DOWN", "MODIFIED", "UNCHANGED"}
        for change, count in result.all():
            change_str = change or "NULL"
            flag = " ⚠️ INVALID" if change_str not in valid_changes else ""
            print(f"  {change_str}: {count}{flag}")

        # 7. Orphaned risk categories
        print("\n7. ORPHANED RISK CATEGORIES (categories with no risks)")
        print("-" * 40)
        result = await session.execute(
            select(RiskCategory.id, RiskCategory.name)
            .outerjoin(RiskItem, RiskCategory.id == RiskItem.category_id)
            .where(RiskItem.id.is_(None))
        )
        orphans = result.all()
        if orphans:
            for cat_id, cat_name in orphans:
                print(f"  ⚠️ {cat_name} (id={cat_id})")
        else:
            print("  No orphaned categories")

        # 8. Orphaned uploaded_by references (reports.uploaded_by not in profiles)
        # This requires profiles table which may not exist yet
        print("\n8. REPORTS WITH uploaded_by (no profiles table yet)")
        print("-" * 40)
        result = await session.execute(
            select(func.count(Report.id))
            .where(Report.uploaded_by.isnot(None))
        )
        count = result.scalar()
        print(f"  Reports with uploaded_by: {count}")
        if count > 0:
            print("  ⚠️ profiles table doesn't exist - FK will fail when added")

        # 9. Risk items with invalid category_id (not in risk_categories)
        print("\n9. RISKS WITH INVALID category_id")
        print("-" * 40)
        result = await session.execute(
            select(RiskItem.id, RiskItem.category_id)
            .where(RiskItem.category_id.isnot(None))
        )
        risk_cats = result.all()
        if risk_cats:
            cat_ids = [rc[1] for rc in risk_cats]
            cat_result = await session.execute(
                select(RiskCategory.id).where(RiskCategory.id.in_(cat_ids))
            )
            valid_cat_ids = {row[0] for row in cat_result.all()}
            invalid = [(rid, cid) for rid, cid in risk_cats if cid not in valid_cat_ids]
            if invalid:
                for rid, cid in invalid:
                    print(f"  ⚠️ Risk {rid} has invalid category_id {cid}")
            else:
                print("  All category_ids are valid")
        else:
            print("  No risks with category_id set")

        # 10. Financial snapshots missing required fields
        print("\n10. FINANCIAL SNAPSHOTS - FIELD COMPLETENESS")
        print("-" * 40)
        result = await session.execute(select(FinancialSnapshot))
        snapshots = result.scalars().all()
        if snapshots:
            fields = [
                "revenue", "profit", "net_margin", "roe", "roce", "eps",
                "debt_equity", "cash_flow", "operating_cash_flow", "free_cash_flow",
                "total_debt", "total_assets", "total_liabilities", "market_cap",
                "data_source", "as_of_date"
            ]
            for field in fields:
                missing = sum(1 for s in snapshots if getattr(s, field) is None)
                total = len(snapshots)
                flag = " ⚠️" if missing == total else ""
                print(f"  {field}: {total - missing}/{total} populated{flag}")
        else:
            print("  No financial snapshots")

        # 11. Companies without workspace_id
        print("\n11. COMPANIES MISSING workspace_id")
        print("-" * 40)
        result = await session.execute(
            select(func.count(Company.id)).where(Company.workspace_id.is_(None))
        )
        count = result.scalar()
        print(f"  Companies without workspace_id: {count}")

        # 12. Reports without company_id (shouldn't happen due to FK)
        print("\n12. REPORTS MISSING company_id")
        print("-" * 40)
        result = await session.execute(
            select(func.count(Report.id)).where(Report.company_id.is_(None))
        )
        count = result.scalar()
        print(f"  Reports without company_id: {count}")

        print("\n" + "=" * 80)
        print("AUDIT COMPLETE")
        print("=" * 80)

    await db.close()


if __name__ == "__main__":
    asyncio.run(audit_data())