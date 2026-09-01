RISK_CLASSIFICATION_SYSTEM_PROMPT = """You are a risk classification expert. Classify risk statements into the standard risk taxonomy with high accuracy.

Taxonomy Categories:
1. operational - Business operations, processes, systems, continuity
2. financial - Revenue, profitability, margins, costs, earnings
3. regulatory - Compliance, regulation changes, statutory requirements
4. strategic - Competition, market share, business model, innovation
5. cyber - Cybersecurity, data breaches, information security
6. climate - Climate change, carbon, sustainability, transition risk
7. governance - Board, executive compensation, succession, audit
8. supply_chain - Vendors, suppliers, procurement, logistics
9. legal - Litigation, lawsuits, regulatory actions, disputes
10. reputational - Brand, public perception, stakeholder trust
11. talent - Key personnel, retention, recruitment, skills
12. technology - Digital transformation, legacy systems, AI
13. market - Demand, pricing, FX, commodity, interest rates
14. liquidity - Cash flow, funding, working capital, solvency
15. credit - Counterparty, receivables, ratings, defaults
16. esg - Environmental, social, governance sustainability
17. geopolitical - Political risk, trade, sanctions, war
18. auditor_concern - Audit opinions, going concern, control weaknesses"""

RISK_CLASSIFICATION_USER_PROMPT = """Classify the following risk statement into the SINGLE most appropriate category from the taxonomy above.

Risk Statement: "{risk_text}"

Context: This risk was disclosed in a {company_sector} company's annual report for FY{fiscal_year}.

Respond with ONLY the category name (e.g., "cyber") and confidence score (0.0-1.0) in this format:
category: <category_name>
confidence: <score>"""

SEVERITY_CLASSIFICATION_PROMPT = """Assess the severity level of the following risk statement.

Risk Statement: "{risk_text}"
Category: {category}

Severity Guidelines:
- critical: "going concern", "existential", "bankruptcy", "material weakness", "catastrophic", "survival at risk"
- high: "significant", "material", "substantial", "major adverse", "critical impact", "high probability"
- medium: "moderate", "potential", "possible", "may impact", "could affect", "reasonably likely"
- low: "minor", "limited", "minimal", "unlikely", "remote probability", "immaterial"
- informational: "disclosed for transparency", "no material effect", "routine disclosure"

Respond with ONLY the severity level and confidence:
severity: <level>
confidence: <score>"""

CONFIDENCE_CALIBRATION_PROMPT = """Evaluate the confidence of the risk extraction and classification.

Original Text Segment: "{source_text}"
Extracted Risk: "{extracted_risk}"
Category: {category}
Severity: {severity}

Consider:
1. How explicitly is this risk stated in the source?
2. Is the categorization unambiguous?
3. Is the severity assessment well-supported by the language?
4. Are there any ambiguous or hedging language?

Provide a calibrated confidence score (0.0-1.0) and brief reasoning."""
