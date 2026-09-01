# Risk Taxonomy

## Overview

The GlobalRisk AI taxonomy defines 18 risk categories organized by business impact area. Each category includes keywords for automatic classification and subcategories for granular analysis.

## Categories

### 1. Operational Risk
Risks arising from business operations, processes, systems, and people.

**Keywords:** operational risk, business disruption, process failure, system outage, operational efficiency, business continuity, disaster recovery, factory, plant, production halt, facility, equipment failure

**Subcategories:**
- Business Continuity
- Process Failure
- System Outage
- Facility Risk

### 2. Financial Risk
Risks affecting financial performance, profitability, and financial stability.

**Keywords:** financial risk, revenue decline, profitability, margin pressure, cost increase, earnings volatility, impairment, write-down, goodwill, financial performance, profit warning

**Subcategories:**
- Revenue Decline
- Margin Pressure
- Cost Overrun
- Impairment Risk

### 3. Regulatory Risk
Risks from changes in laws, regulations, and compliance requirements.

**Keywords:** regulatory risk, compliance, regulation, regulatory change, statutory requirement, license, permit, regulatory approval, sebi, sec, rbi, regulatory action, non-compliance

**Subcategories:**
- Compliance Risk
- Regulatory Change
- Licensing Risk

### 4. Strategic Risk
Risks to business strategy, competitive position, and long-term viability.

**Keywords:** strategic risk, competition, market share, strategic initiative, business model, digital transformation, innovation, new entrant, disruptive technology, strategic shift

**Subcategories:**
- Competitive Risk
- Innovation Risk
- Business Model Risk

### 5. Cyber Risk
Cybersecurity threats, data breaches, and information security risks.

**Keywords:** cyber, cybersecurity, data breach, information security, ransomware, phishing, malware, hacking, data privacy, gdpr, data protection, cyber attack, security incident, unauthorized access

**Subcategories:**
- Data Breach
- Ransomware
- Privacy Violation
- Cyber Attack

### 6. Climate Risk
Physical and transition risks from climate change.

**Keywords:** climate change, carbon emission, net zero, physical risk, transition risk, sustainability, environmental regulation, greenhouse gas, climate-related, decarbonization

**Subcategories:**
- Physical Climate Risk
- Transition Climate Risk
- Regulatory Climate Risk

### 7. Governance Risk
Corporate governance, board effectiveness, and oversight risks.

**Keywords:** governance, board, corporate governance, executive compensation, succession planning, independent director, audit committee, related party transaction, whistleblower, board independence

**Subcategories:**
- Board Effectiveness
- Succession Risk
- Compensation Risk

### 8. Supply Chain Risk
Vendor dependencies, logistics disruptions, and procurement risks.

**Keywords:** supply chain, vendor, supplier, procurement, single source, concentration risk, third party, logistics, raw material shortage, supply disruption

**Subcategories:**
- Vendor Concentration
- Logistics Disruption
- Raw Material Risk

### 9. Legal Risk
Litigation, regulatory actions, and legal proceedings.

**Keywords:** litigation, lawsuit, legal proceeding, contingent liability, arbitration, settlement, class action, regulatory action, court order, injunction, legal claim

**Subcategories:**
- Litigation Risk
- Regulatory Enforcement
- Contractual Risk

### 10. Reputational Risk
Brand damage, stakeholder trust, and public perception risks.

**Keywords:** reputation, brand damage, public perception, media scrutiny, social media, stakeholder trust, customer confidence, boycott, reputational harm

**Subcategories:**
- Brand Damage
- Stakeholder Trust
- Media Risk

### 11. Talent Risk
Key personnel retention, recruitment, and succession planning risks.

**Keywords:** talent, human capital, key personnel, retention, recruitment, succession planning, skills gap, talent shortage, executive departure, leadership change

**Subcategories:**
- Key Person Risk
- Succession Risk
- Skills Gap

### 12. Technology Risk
Technology disruption, legacy systems, and digital transformation risks.

**Keywords:** technology risk, legacy system, technical debt, digital transformation, automation, artificial intelligence, ai regulation, platform migration, system replacement

**Subcategories:**
- Legacy System
- Digital Transformation
- AI Risk

### 13. Market Risk
Market demand, pricing, foreign exchange, and commodity price risks.

**Keywords:** market risk, demand decline, pricing pressure, foreign exchange, commodity price, interest rate risk, equity price, customer concentration, market volatility

**Subcategories:**
- Demand Risk
- Pricing Risk
- Foreign Exchange Risk

### 14. Liquidity Risk
Cash flow, funding, working capital, and solvency risks.

**Keywords:** liquidity risk, cash flow, working capital, funding risk, solvency, debt maturity, refinancing risk, covenant breach, liquidity position

**Subcategories:**
- Funding Risk
- Covenant Risk
- Refinancing Risk

### 15. Credit Risk
Counterparty default, receivables, and credit rating risks.

**Keywords:** credit risk, counterparty risk, default risk, credit rating, bad debt, provision for doubtful, impairment loss, receivables, credit exposure

**Subcategories:**
- Counterparty Risk
- Receivables Risk
- Rating Downgrade

### 16. ESG Risk
Environmental, social, and governance sustainability risks.

**Keywords:** esg, environmental social, diversity inclusion, human rights, community impact, stakeholder engagement, sustainable finance, green bond, esg rating

**Subcategories:**
- Environmental Risk
- Social Risk
- Governance Risk

### 17. Geopolitical Risk
Political instability, trade wars, sanctions, and regulatory changes.

**Keywords:** geopolitical, political risk, trade war, sanctions, tariff, export control, war, conflict, regime change, political instability

**Subcategories:**
- Trade Risk
- Sanctions Risk
- Political Instability

### 18. Auditor Concern
Audit qualifications, going concern, material weaknesses, and control deficiencies.

**Keywords:** auditor, audit opinion, going concern, material weakness, internal control, significant deficiency, emphasis of matter, qualified opinion, adverse opinion, audit qualification

**Subcategories:**
- Going Concern
- Material Weakness
- Control Deficiency

## Severity Levels

| Level | Weight | Description |
|-------|--------|-------------|
| Critical | 5 | Existential threat to business continuity; immediate board attention required |
| High | 4 | Significant impact on financials, operations, or reputation; urgent mitigation needed |
| Medium | 3 | Moderate impact manageable with existing controls; monitoring required |
| Low | 2 | Minor impact; routine monitoring sufficient |
| Informational | 1 | Disclosed for transparency; no immediate action required |

## Classification Logic

### Rule-Based Classification
Each category has weighted keyword rules. The category with the highest score is assigned.

### Severity Assessment
Severity is determined by:
1. Language intensity (critical/high/medium/low/informational keywords)
2. Category-specific bias (e.g., cyber, auditor_concern get +1 level)
3. Confidence score calibration

### Confidence Scoring
Combines:
- Base detection confidence (40%)
- Category match quality (20%)
- Severity consistency (15%)
- Entity extraction count (15%)
- Text length factor (10%)

## Customization

The taxonomy is defined in `app/taxonomy/data/risk_taxonomy_v1.json` and can be extended by:
1. Adding new categories
2. Modifying keywords and weights
3. Adding subcategories
4. Adjusting severity level descriptions

To reload taxonomy at runtime:
```python
from app.taxonomy import reload_taxonomy
reload_taxonomy()
```