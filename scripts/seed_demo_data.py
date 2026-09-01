#!/usr/bin/env python3
"""Script to seed demo data for development and testing."""

import asyncio
from uuid import uuid4

from app.config.settings import get_settings
from app.config.logging import setup_logging, get_logger
from app.db.session import init_db, db
from app.db.base import Company, Report, RiskItem, FinancialSnapshot, Workspace

logger = get_logger(__name__)


async def seed_demo_data():
    settings = get_settings()
    setup_logging()

    await init_db()

    async with db.session() as session:
        workspace = Workspace(name="Demo Workspace")
        session.add(workspace)
        await session.flush()

        companies_data = [
            {
                "name": "Reliance Industries Ltd",
                "sector": "Conglomerate",
                "market_cap": 1800000.0,
                "listed_exchange": "NSE",
                "workspace_id": workspace.id,
            },
            {
                "name": "Tata Consultancy Services Ltd",
                "sector": "IT Services",
                "market_cap": 1400000.0,
                "listed_exchange": "NSE",
                "workspace_id": workspace.id,
            },
            {
                "name": "HDFC Bank Ltd",
                "sector": "Banking",
                "market_cap": 1200000.0,
                "listed_exchange": "NSE",
                "workspace_id": workspace.id,
            },
            {
                "name": "Infosys Ltd",
                "sector": "IT Services",
                "market_cap": 700000.0,
                "listed_exchange": "NSE",
                "workspace_id": workspace.id,
            },
            {
                "name": "ICICI Bank Ltd",
                "sector": "Banking",
                "market_cap": 650000.0,
                "listed_exchange": "NSE",
                "workspace_id": workspace.id,
            },
        ]

        for comp_data in companies_data:
            existing = await session.execute(
                Company.__table__.select().where(Company.name == comp_data["name"])
            )
            if existing.scalar_one_or_none():
                logger.info("company_exists", name=comp_data["name"])
                continue
            
            company = Company(**comp_data)
            session.add(company)

        await session.commit()

        financial_data = [
            {
                "company_name": "Reliance Industries Ltd",
                "fiscal_year": 2024,
                "revenue": 900000.0,
                "profit": 75000.0,
                "net_margin": 8.3,
                "roe": 12.5,
                "roce": 14.2,
                "eps": 112.5,
                "debt_equity": 0.45,
                "cash_flow": 85000.0,
                "market_cap": 1800000.0,
            },
            {
                "company_name": "Tata Consultancy Services Ltd",
                "fiscal_year": 2024,
                "revenue": 240000.0,
                "profit": 45000.0,
                "net_margin": 18.7,
                "roe": 45.2,
                "roce": 52.1,
                "eps": 125.8,
                "debt_equity": 0.02,
                "cash_flow": 50000.0,
                "market_cap": 1400000.0,
            },
            {
                "company_name": "HDFC Bank Ltd",
                "fiscal_year": 2024,
                "revenue": 180000.0,
                "profit": 52000.0,
                "net_margin": 28.9,
                "roe": 16.8,
                "roce": 18.5,
                "eps": 92.4,
                "debt_equity": 5.2,
                "cash_flow": 120000.0,
                "market_cap": 1200000.0,
            },
        ]

        for fin_data in financial_data:
            company_result = await session.execute(
                Company.__table__.select().where(Company.name == fin_data["company_name"])
            )
            company = company_result.scalar_one_or_none()
            
            if company:
                existing = await session.execute(
                    FinancialSnapshot.__table__.select().where(
                        FinancialSnapshot.company_id == company.id,
                        FinancialSnapshot.fiscal_year == fin_data["fiscal_year"],
                    )
                )
                if not existing.scalar_one_or_none():
                    fin_data_copy = fin_data.copy()
                    fin_data_copy.pop("company_name")
                    fin_data_copy["company_id"] = company.id
                    financial = FinancialSnapshot(**fin_data_copy)
                    session.add(financial)

        await session.commit()
        logger.info("demo_data_seeded")

    await db.close()


def main():
    asyncio.run(seed_demo_data())


if __name__ == "__main__":
    main()