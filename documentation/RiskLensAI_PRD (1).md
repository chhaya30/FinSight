# RISKLENS AI
### Corporate Risk Intelligence Platform
**Product Requirements Document · Major Project / MVP Edition · 1-Month Build**

| BUILD TIME | CORE MODULES | RELEASE TARGET | TARGET OUTCOME |
|---|---|---|---|
| 4 Weeks (160 hrs) | 10 MVP Modules | Deployable Beta | Production-Ready Demo + Pilot-Ready SaaS |

An AI-powered platform that reads corporate annual reports and filings, extracts material risks with
explainable AI, and tracks how those risks evolve year over year — surfacing what changed, what's new,
and what's disappearing from disclosures, with full traceability back to the source paragraph. Deliberately
excludes technical/trading features (RSI, MACD, price prediction, brokerage integration) to stay focused
on **corporate risk intelligence**, not another stock-picking tool.

---

## 01 · CORE FEATURES

### 1.1 Must-Have MVP Features (Week 1)

- **Corporate Intelligence Repository** — `CRITICAL`
  Annual report upload (drag & drop PDF), multi-year and multi-company support, company profiles,
  report metadata (year, sector, market cap), document version management, search & filter, and
  processing-status tracking.

- **Corporate Risk Intelligence Engine** — `CRITICAL`
  Semantic risk extraction from filings using an LLM pipeline: risk classification and categorization,
  risk chunking, named entity recognition, key topic extraction, material risk detection, severity
  estimation, and AI-generated risk summaries — each with an explainability trail back to source text.

- **Evidence & Explainability Layer** — `CRITICAL`
  Original vs. updated disclosure viewer, side-by-side comparison, highlighted semantic changes, AI
  explanation panel, confidence meter, source paragraph navigation, and citation mapping. This is what
  makes the AI's output trustworthy to an analyst rather than a black box.

- **Risk Evolution Analytics** — `CRITICAL`
  Year-over-year comparison engine: new risk detection, removed risk detection, increased/reduced
  severity detection, modified disclosure detection, emerging theme detection, risk timeline, and an
  AI-generated evolution summary. This is the platform's primary USP.

- **Document Processing Pipeline** — `CRITICAL` *(new: enabled by extra time)*
  Robust PDF ingestion (including scanned/OCR'd filings), persisted chunk + embedding store, and
  incremental reprocessing so new filings can be diffed against prior years without re-running the
  entire pipeline.

### 1.2 High-Impact Differentiators (Week 2)

- **Executive Dashboard** — `HIGH`
  Single-screen overview: company overview, overall risk score, risk distribution, risk timeline,
  emerging risks, top risk categories, AI executive summary, risk trend charts, financial snapshot,
  latest news, and quick actions.

- **Explainable AI Intelligence** — `HIGH`
  Analyst-style narratives: executive risk summary, business impact explanation, risk importance
  explanation, recommendation generation, and an AI confidence indicator on every generated insight.

- **Financial Health Intelligence** — `HIGH`
  Revenue, profit, net margin, ROE, ROCE, EPS, debt/equity, cash flow, market cap, financial trend
  charts, AI financial interpretation, and risk-vs-financial-health correlation — used to validate
  whether extracted risks are actually showing up in the numbers.

- **Market Intelligence** — `HIGH`
  Company news feed, regulatory news, SEBI/SEC filings, NSE/BSE updates, news sentiment analysis,
  event timeline, AI news correlation, and breaking risk alerts — connecting disclosed risk to
  real-world events.

- **Industry Intelligence** — `HIGH`
  Peer comparison, sector heatmap, sector risk trends, common risks, emerging industry risks,
  industry benchmark score, company ranking, and a comparative dashboard.

- **Risk Explorer** — `HIGH` *(inspired by StockEdge)*
  Semantic screening across companies: governance, cyber, climate, regulatory, supply chain, AI
  regulation, ESG, litigation, auditor concern, and financial stability scans, plus custom risk filters.

### 1.3 Scale & Accuracy Features (Week 3)

- **Multi-Factor Risk Scanner** — `MEDIUM` *(not feasible in a hackathon build)*
  Combine conditions across companies (Governance Risk ↑, Cyber Risk ↑, Debt ↑, Revenue ↓, Negative
  News ↑, Auditor Language Changed, FII Holding ↓, Climate Risk ↑) with AND/OR logic, saved scans, and
  custom filters — turning the platform from a lookup tool into an analyst screening engine.

- **Confidence-Scored Risk Classification** — `MEDIUM`
  Move from single-pass LLM extraction to a weighted confidence model (exact regulatory language match,
  semantic similarity match, inferred match) so analysts can see how certain the AI actually is.

- **Executive Report Generator** — `MEDIUM`
  One-click professional PDF export: executive summary, risk evolution report, financial analysis,
  news analysis, evidence report, peer comparison, charts, recommendations, and company snapshot.

- **Custom Risk Taxonomy Rules** — `MEDIUM` *(new)*
  Let analyst teams define or tune their own risk category definitions and severity thresholds via
  config, so the taxonomy can adapt to house conventions (e.g., a fund's specific ESG criteria).

### 1.4 Polish & Productionization (Week 4)

- **Analyst Workspace** — `POLISH`
  Watchlists, saved companies, saved reports, saved scans, personal notes, recent activity, dashboard
  preferences, and favorites.

- **PDF Annotation Workspace** — `POLISH`
  Highlight paragraphs, add notes, bookmark sections, navigate to evidence, AI highlight suggestions,
  share notes, and review comments — collaborative analysis on top of the underlying filings.

- **Authentication & Multi-User Workspaces** — `POLISH` *(new)*
  Basic auth (email/OAuth) with per-team workspaces so the tool can be piloted by a real analyst team,
  not just a single demo login.

- **Dark/Light Theme + Responsive Design** — `POLISH`
  Framer Motion animations, skeleton loaders, interactive cards, presentation mode, search-everywhere,
  and keyboard shortcuts.

- **Test Coverage & Deployment Hardening** — `POLISH` *(new)*
  Unit tests for the extraction/classification pipeline, integration tests for evolution diffing, and
  a real cloud deployment instead of a local-only build.

---

## 02 · TECHNICAL REQUIREMENTS

### 2.1 Recommended Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React 18 + Vite + TailwindCSS | Fast HMR, utility-first styling, rapid iteration |
| Charts/Visuals | Recharts + D3.js | Trend charts, heatmaps, radar charts, Sankey flow |
| Backend | FastAPI (Python 3.11) | Async, auto-docs, strong ecosystem for NLP pipelines |
| Document Parsing | PyMuPDF / pdfplumber + OCR (Tesseract) fallback | Reliable text + layout extraction from annual report PDFs |
| LLM | Claude API | Semantic risk extraction, classification, explainability, narrative generation |
| Embeddings/Retrieval | pgvector or Pinecone | Semantic chunk search, year-over-year similarity matching |
| Database | PostgreSQL | Structured company/report/risk metadata, relational queries |
| State | Zustand + React Query | Lightweight, no boilerplate, instant cache updates |
| Auth | Auth.js / Clerk | Fast to integrate, supports OAuth + email |
| Market/Filing Data | SEBI/SEC/NSE/BSE public APIs + news APIs | Regulatory filings, market data, and news correlation |
| Packaging | Docker Compose + cloud deploy (Fly.io / Render) | Reproducible environment, pilot-ready hosting |

### 2.2 System Architecture

1. **Ingestion Layer** — accepts uploaded annual report PDFs (or fetched regulatory filings),
   detects company/year/sector metadata, and routes to the parsing pipeline; scanned documents fall
   back to OCR.
2. **Extraction Layer** — chunks documents, extracts named entities and topics, and classifies risk
   statements via LLM into category, severity, and confidence score; each extracted risk is linked
   back to its source paragraph and page.
3. **Evolution Resolution Layer** — semantically matches this year's risk statements against prior
   years for the same company, flags new/removed/modified/severity-changed risks, and generates an
   AI evolution summary.
4. **Enrichment Layer** — pulls in financial metrics, market/news data, and sector peer data to
   validate and contextualize extracted risks (e.g., correlating a "liquidity risk" disclosure with
   an actual debt/equity spike).
5. **API Layer** — FastAPI exposes REST endpoints for company data, risk graphs, evolution reports,
   dashboard metrics, and AI narratives, consumed by the React frontend.
6. **Reporting Layer** *(new)* — generates structured PDF/HTML executive reports on demand, combining
   evidence, evolution analysis, and financial correlation into a single downloadable artifact.

### 2.3 Non-Functional Requirements

| Requirement | Target | Approach |
|---|---|---|
| Ingestion Speed | < 30s per 100-page annual report | Parallel chunking, async FastAPI workers |
| Extraction Accuracy | High-precision risk classification with visible confidence | Confidence-scored LLM classification, human-reviewable |
| Evolution Diff Speed | < 10s to compare two years for one company | Pre-embedded chunks, vector similarity search |
| Dashboard Load | < 2s for executive dashboard | Cached aggregates, paginated risk lists |
| Report Support | Multi-year, multi-company | Structured metadata store, incremental reprocessing |
| Data Persistence | Durable across sessions | PostgreSQL with nightly backups |
| Uptime | 99%+ on hosted deployment | Docker Compose + managed hosting with health checks |
| Security | Basic auth, workspace isolation | Auth.js/Clerk, per-workspace row-level access |
| Explainability | Every AI claim traceable to source text | Citation mapping stored alongside every extracted risk |

### 2.4 Core Data Model

- **Company:** `{ id, name, sector, market_cap, listed_exchange, workspace_id }`
- **Report:** `{ id, company_id, fiscal_year, upload_date, processing_status, source_file }`
- **RiskItem:** `{ id, report_id, category, severity, confidence_score, summary, source_page, source_paragraph, entities[] }`
- **EvolutionEntry:** `{ risk_item_id_prev, risk_item_id_current, change_type (NEW|REMOVED|SEVERITY_UP|SEVERITY_DOWN|MODIFIED), ai_summary }`
- **FinancialSnapshot:** `{ company_id, fiscal_year, revenue, profit, net_margin, roe, roce, eps, debt_equity, cash_flow, market_cap }`
- **Workspace** *(new)*: `{ id, name, members[], companies[], created_at }`
- **SavedScan** *(new)*: `{ id, workspace_id, name, filter_conditions[], logic (AND|OR) }`

---

## 03 · ONE-MONTH EXECUTION PLAN

### 3.1 Weekly Roadmap

**Week 1 — Foundation & Extraction Engine**
Project scaffolding (Docker, React+Vite, FastAPI, Postgres+pgvector). PDF/OCR ingestion pipeline.
Corporate Intelligence Repository. Core LLM extraction pipeline: risk classification, chunking, NER,
severity estimation. Evidence layer with source-paragraph linking online.
*Output: Upload a report, get back a structured, evidenced list of extracted risks.*

**Week 2 — Evolution Analytics, Dashboard & Explainability**
Year-over-year evolution resolver (new/removed/modified/severity-changed detection). Executive
Dashboard. Explainable AI narrative generation (executive summaries, business impact explanations).
Financial Health Intelligence module wired to financial snapshots.
*Output: Full core demo flow — upload two years of filings, see what changed and why it matters.*

**Week 3 — Market/Industry Intelligence & Screening**
Market Intelligence (news feed, regulatory filings, sentiment, event correlation). Industry
Intelligence (peer comparison, sector heatmap, benchmarking). Risk Explorer semantic scans.
Multi-Factor Risk Scanner with AND/OR saved scans. Confidence-scored classification refinement.
*Output: Platform works across a real universe of companies, not just one demo company.*

**Week 4 — Workspace, Reporting & Productionization**
Authentication and multi-user workspaces. Analyst Workspace (watchlists, notes, saved scans). PDF
Annotation Workspace. Executive Report Generator (PDF export). Dark/light theme, presentation mode.
Test coverage and cloud deployment.
*Output: Deployable beta suitable for a pilot analyst team or investor/judge demo.*

### 3.2 Suggested Team Allocation (3–4 person team)

| Role | Focus | Key Weeks |
|---|---|---|
| NLP/Backend Lead | Extraction pipeline, evolution resolver, data model | 1–3 |
| Frontend/Viz Lead | Dashboard, evolution viewer, charts, theming | 2–4 |
| Platform/Infra | Auth, financial/news data integration, deployment, testing | 3–4 |
| AI/Product | Prompt design, explainability UX, report generator, demo narrative | 2–4 |

*(Solo builders should follow the same sequence — Week 1 must produce a reliable, evidenced
extraction pipeline before evolution analytics or dashboard work begins.)*

### 3.3 Demo & Pitch Strategy

1. **The Hook (0:00–0:30):** Upload a real company's 3 most recent annual reports live (or use a
   pre-loaded set). Say: *"No analyst reads 300 pages a year, three years running, to catch what
   changed in the risk section. We do it in seconds — with full evidence, not a black box."*
2. **The Wow Moment (0:30–1:30):** Open the Risk Evolution view for one company. Show a "new risk"
   surfaced this year (e.g., a cybersecurity disclosure that didn't exist last year), click through
   to the Evidence panel, and show the exact source paragraph side-by-side across years.
3. **The Intelligence (1:30–2:15):** Show the AI executive summary and the Financial Health
   correlation — e.g., a disclosed "liquidity risk" lining up with a real debt/equity spike in the
   Financial Snapshot.
4. **The Screening Power (2:15–2:45):** Run a Multi-Factor Scan — "Governance Risk ↑ AND Debt ↑ AND
   Auditor Language Changed" — across the company universe and show a ranked result list.
5. **The Close (2:45–3:00):** One-click Executive Report export. *"This is analyst-grade, evidenced,
   explainable risk intelligence — ready for a pilot desk, not just a demo."*

### 3.4 Visual Design Directives

- Clean, trust-forward light/dark themes — this is a professional research tool, not a trading app;
  avoid neon "hype" styling in favor of a calm, analyst-grade aesthetic.
- Confidence Gauge and Risk Score should be the dashboard's visual centerpiece, using a consistent
  red→green severity gradient across the dashboard, evolution view, and exported reports.
- Side-by-side disclosure comparison should use clear diff highlighting (additions/removals/severity
  changes in distinct colors) so semantic changes are legible at a glance.
- Sector heatmaps and risk timelines should animate smoothly on load — skeleton loaders while the
  extraction/evolution pipeline runs, never a blank screen.
- Presentation Mode: enlarged fonts and simplified panels for projector/investor demo viewing.

### 3.5 Competitive Moat — Why This Beats Every Competitor

| Tool | What It Does | What It Misses | Our Edge |
|---|---|---|---|
| Bloomberg/Refinitiv Terminal | Broad market & financial data | Deep semantic risk-disclosure analysis | Purpose-built risk evolution engine |
| StockEdge | Technical/fundamental screening | No disclosure-level semantic intelligence | Risk Explorer built on filing text, not just numbers |
| Generic LLM chat over a PDF | One-off Q&A on a single filing | No structured evolution tracking or evidence trail | Persistent, evidenced, multi-year risk graph |
| Traditional equity research reports | Human analyst narrative | Slow, not scalable across companies | AI-generated at company-universe scale, still evidenced |

### 3.6 Risk Mitigation & Fallback Strategies

- **Risk:** LLM misclassifies or hallucinates a risk not actually in the filing.
  **Mitigation:** Every extracted risk must carry a citation back to source text; low-confidence
  extractions are visually flagged rather than presented as certain.
- **Risk:** Scanned/older filings have poor OCR quality.
  **Mitigation:** OCR fallback with confidence scoring; flag low-quality extractions for manual
  review rather than silently guessing.
- **Risk:** Year-over-year matching produces false "new risk" flags due to reworded language.
  **Mitigation:** Semantic similarity matching (not exact text match) with a tunable similarity
  threshold, refined during Week 3's accuracy pass.
- **Risk:** Multi-Factor Scanner scope creep eats remaining weeks.
  **Mitigation:** Timebox to 3 days; ship with a fixed set of common factor combinations if the full
  custom filter builder isn't stable in time.
- **Risk:** Regulatory/news API access is rate-limited or inconsistent.
  **Mitigation:** Cache pulled data and degrade gracefully — Market Intelligence panels show "last
  updated" timestamps rather than failing silently.
- **Risk:** Deployment/hosting issues on demo day.
  **Mitigation:** Deploy to managed hosting by end of Week 3 so Week 4 is spent hardening a live
  environment, not deploying for the first time under pressure.

### 3.7 Post-Launch Roadmap

**Phase 2:**
AI chat with reports, custom risk alerts, portfolio watchlists, multi-language reports, API access,
scheduled report generation, advanced search.

**Phase 3:**
Mutual fund intelligence, institutional holdings analysis, ETF exposure, earnings call analysis, ESG
intelligence, global market support, portfolio risk analysis, predictive risk trends (research
feature).

### 3.8 Explicit Non-Goals

To keep the product focused on corporate risk intelligence rather than becoming a generic trading
platform, RiskLens AI deliberately excludes: RSI, MACD, candlestick patterns, buy/sell
recommendations, intraday charts, stock price prediction, technical analysis, cryptocurrency trading,
options/futures analytics, portfolio optimization, automated trading, and brokerage integration.

---

*RISKLENS AI · Major Project / MVP PRD*
*Corporate Risk Intelligence Platform · 1-month build roadmap*
*August 2026 · Confidential*
