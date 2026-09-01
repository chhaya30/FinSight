export type Severity = "critical" | "high" | "medium" | "low";

export const companies = [
  { id: "atlas", name: "Atlas Industries", ticker: "ATLS", sector: "Industrials", score: 78, delta: +6, market: "NYSE" },
  { id: "nimbus", name: "Nimbus Cloud Systems", ticker: "NMBS", sector: "Technology", score: 64, delta: -4, market: "NASDAQ" },
  { id: "meridian", name: "Meridian Financial", ticker: "MRDN", sector: "Financials", score: 71, delta: +2, market: "NYSE" },
  { id: "kaveri", name: "Kaveri Energy Ltd", ticker: "KAVE", sector: "Energy", score: 85, delta: +11, market: "NSE" },
  { id: "solstice", name: "Solstice Pharma", ticker: "SLST", sector: "Healthcare", score: 52, delta: -7, market: "NASDAQ" },
  { id: "verdant", name: "Verdant Agri Corp", ticker: "VRDT", sector: "Materials", score: 60, delta: +1, market: "NSE" },
];

export const riskCategories = [
  "Governance",
  "Cybersecurity",
  "ESG",
  "Climate",
  "Regulatory",
  "Litigation",
  "Supply Chain",
  "AI Regulation",
  "Auditor Concerns",
  "Financial Stability",
] as const;

export type RiskCategory = (typeof riskCategories)[number];

export type Risk = {
  id: string;
  company: string;
  category: RiskCategory;
  title: string;
  severity: Severity;
  confidence: number;
  year: number;
  status: "new" | "escalated" | "persistent" | "removed";
  summary: string;
  quote: string;
  source: string;
  entities: string[];
  topics: string[];
};

export const risks: Risk[] = [
  {
    id: "R-1041",
    company: "Kaveri Energy Ltd",
    category: "Climate",
    title: "Carbon transition costs may exceed provisioned capital",
    severity: "critical",
    confidence: 0.94,
    year: 2025,
    status: "new",
    summary:
      "The FY25 disclosure introduces explicit language about accelerated decarbonisation capex that is not matched by committed funding, implying balance-sheet strain within 24 months.",
    quote:
      "Our transition plan contemplates capital expenditure materially in excess of currently committed facilities, and there can be no assurance such financing will be available on acceptable terms.",
    source: "FY2025 Annual Report · Item 1A · p.42",
    entities: ["CERC", "Ministry of Power", "Scope 3"],
    topics: ["decarbonisation capex", "financing risk"],
  },
  {
    id: "R-1042",
    company: "Nimbus Cloud Systems",
    category: "Cybersecurity",
    title: "Third-party breach exposure across managed identity vendors",
    severity: "high",
    confidence: 0.89,
    year: 2025,
    status: "escalated",
    summary:
      "Language expanded from generic security boilerplate to naming vendor concentration and a prior incident, signalling elevated residual risk.",
    quote:
      "A security incident at one of our identity providers in the prior fiscal year affected a subset of enterprise tenants and could recur.",
    source: "FY2025 10-K · Risk Factors · p.28",
    entities: ["SEC", "CISA", "SOC 2"],
    topics: ["vendor concentration", "incident recurrence"],
  },
  {
    id: "R-1043",
    company: "Meridian Financial",
    category: "Regulatory",
    title: "Heightened supervisory scrutiny of consumer lending book",
    severity: "high",
    confidence: 0.86,
    year: 2025,
    status: "persistent",
    summary:
      "Consistent multi-year disclosure with intensified wording around examinations and potential remediation orders.",
    quote:
      "We are subject to ongoing examinations that may result in supervisory findings, remediation requirements or civil money penalties.",
    source: "FY2025 10-K · Item 1A · p.19",
    entities: ["CFPB", "OCC"],
    topics: ["supervisory findings", "remediation"],
  },
  {
    id: "R-1044",
    company: "Solstice Pharma",
    category: "Litigation",
    title: "Product liability class actions in two jurisdictions",
    severity: "critical",
    confidence: 0.91,
    year: 2025,
    status: "escalated",
    summary: "New consolidated proceedings disclosed with an unquantified loss contingency and reduced insurance headroom.",
    quote: "We are unable to estimate a range of reasonably possible loss in respect of the consolidated proceedings.",
    source: "FY2025 20-F · Legal Proceedings · p.63",
    entities: ["FDA", "District of New Jersey"],
    topics: ["loss contingency", "insurance headroom"],
  },
  {
    id: "R-1045",
    company: "Atlas Industries",
    category: "Supply Chain",
    title: "Single-source dependency for precision castings",
    severity: "medium",
    confidence: 0.81,
    year: 2025,
    status: "persistent",
    summary: "Supplier concentration language unchanged year-over-year, but backlog growth increases the impact of disruption.",
    quote: "Certain critical components are sourced from a single qualified supplier with limited alternative capacity.",
    source: "FY2025 Annual Report · p.31",
    entities: ["Tier-1 suppliers"],
    topics: ["single source", "backlog exposure"],
  },
  {
    id: "R-1046",
    company: "Nimbus Cloud Systems",
    category: "AI Regulation",
    title: "EU AI Act classification uncertainty for inference products",
    severity: "high",
    confidence: 0.88,
    year: 2025,
    status: "new",
    summary: "First-time disclosure of AI-specific regulatory exposure with conformity assessment cost commentary.",
    quote: "Certain of our offerings may be classified as high-risk AI systems, requiring conformity assessments.",
    source: "FY2025 10-K · Item 1A · p.34",
    entities: ["European Commission", "EU AI Act"],
    topics: ["conformity assessment", "classification risk"],
  },
  {
    id: "R-1047",
    company: "Verdant Agri Corp",
    category: "Auditor Concerns",
    title: "Critical audit matter on biological asset valuation",
    severity: "medium",
    confidence: 0.79,
    year: 2025,
    status: "new",
    summary: "Auditor flagged significant judgement in fair value of biological assets — a leading indicator of restatement risk.",
    quote: "Valuation of biological assets was identified as a critical audit matter due to significant management judgement.",
    source: "FY2025 Annual Report · Auditor's Report · p.88",
    entities: ["Statutory Auditor", "Ind AS 41"],
    topics: ["fair value judgement", "critical audit matter"],
  },
  {
    id: "R-1048",
    company: "Meridian Financial",
    category: "Governance",
    title: "Board independence reduced after two director resignations",
    severity: "medium",
    confidence: 0.83,
    year: 2025,
    status: "new",
    summary: "Governance composition change reduces independent majority on the audit committee.",
    quote: "Two independent directors resigned during the year; the Board is in the process of identifying replacements.",
    source: "FY2025 Proxy Statement · p.11",
    entities: ["Audit Committee", "Nominating Committee"],
    topics: ["board independence", "committee composition"],
  },
  {
    id: "R-1049",
    company: "Kaveri Energy Ltd",
    category: "ESG",
    title: "Community relations disputes at two generation sites",
    severity: "low",
    confidence: 0.72,
    year: 2025,
    status: "persistent",
    summary: "Ongoing land and community engagement matters, stable severity versus prior year.",
    quote: "We continue to engage with local stakeholders in respect of land acquisition matters at two project sites.",
    source: "FY2025 BRSR · Principle 4 · p.57",
    entities: ["SEBI", "BRSR"],
    topics: ["community engagement", "land acquisition"],
  },
  {
    id: "R-1050",
    company: "Atlas Industries",
    category: "Financial Stability",
    title: "Covenant headroom narrowing on revolving facility",
    severity: "high",
    confidence: 0.9,
    year: 2025,
    status: "escalated",
    summary: "Leverage covenant headroom compressed from 1.4x to 0.6x, a material change in financial flexibility language.",
    quote: "As of year end, headroom under our net leverage covenant had narrowed relative to the prior year.",
    source: "FY2025 Annual Report · MD&A · p.24",
    entities: ["Syndicate lenders"],
    topics: ["covenant headroom", "liquidity"],
  },
];

export const documents = [
  { id: "D-9001", name: "Kaveri_Energy_FY2025_Annual_Report.pdf", company: "Kaveri Energy Ltd", year: 2025, type: "Annual Report", pages: 264, size: "14.2 MB", status: "indexed", version: "v3", uploaded: "2026-07-28", ocr: true, risks: 42 },
  { id: "D-9002", name: "Nimbus_10K_FY2025.pdf", company: "Nimbus Cloud Systems", year: 2025, type: "10-K", pages: 188, size: "9.8 MB", status: "indexed", version: "v2", uploaded: "2026-07-26", ocr: true, risks: 37 },
  { id: "D-9003", name: "Meridian_10K_FY2025.pdf", company: "Meridian Financial", year: 2025, type: "10-K", pages: 212, size: "11.1 MB", status: "processing", version: "v1", uploaded: "2026-08-03", ocr: true, risks: 0 },
  { id: "D-9004", name: "Solstice_20F_FY2025.pdf", company: "Solstice Pharma", year: 2025, type: "20-F", pages: 240, size: "12.6 MB", status: "indexed", version: "v1", uploaded: "2026-07-19", ocr: false, risks: 29 },
  { id: "D-9005", name: "Atlas_FY2024_Annual_Report.pdf", company: "Atlas Industries", year: 2024, type: "Annual Report", pages: 198, size: "10.4 MB", status: "indexed", version: "v4", uploaded: "2026-05-11", ocr: true, risks: 33 },
  { id: "D-9006", name: "Verdant_BRSR_FY2025.pdf", company: "Verdant Agri Corp", year: 2025, type: "BRSR", pages: 96, size: "5.2 MB", status: "queued", version: "v1", uploaded: "2026-08-04", ocr: true, risks: 0 },
];

export const riskTrend = [
  { year: "2020", critical: 3, high: 8, medium: 14, low: 19, score: 51 },
  { year: "2021", critical: 4, high: 9, medium: 16, low: 18, score: 55 },
  { year: "2022", critical: 6, high: 12, medium: 15, low: 17, score: 62 },
  { year: "2023", critical: 5, high: 14, medium: 18, low: 15, score: 66 },
  { year: "2024", critical: 8, high: 15, medium: 17, low: 14, score: 71 },
  { year: "2025", critical: 11, high: 19, medium: 16, low: 12, score: 78 },
];

export const financials = [
  { period: "Q1-24", revenue: 1180, ebitda: 262, fcf: 88, leverage: 2.4 },
  { period: "Q2-24", revenue: 1246, ebitda: 271, fcf: 96, leverage: 2.5 },
  { period: "Q3-24", revenue: 1310, ebitda: 288, fcf: 71, leverage: 2.8 },
  { period: "Q4-24", revenue: 1402, ebitda: 301, fcf: 110, leverage: 2.7 },
  { period: "Q1-25", revenue: 1388, ebitda: 292, fcf: 64, leverage: 3.1 },
  { period: "Q2-25", revenue: 1471, ebitda: 314, fcf: 82, leverage: 3.3 },
];

export const news = [
  { id: 1, source: "Reuters", time: "12m", sentiment: -0.62, title: "Kaveri Energy flags higher transition capex, shares slip 4%", tags: ["Climate", "Capex"] },
  { id: 2, source: "SEC EDGAR", time: "48m", sentiment: -0.31, title: "Nimbus Cloud Systems files 8-K on identity vendor incident", tags: ["Cyber", "Filing"] },
  { id: 3, source: "SEBI", time: "2h", sentiment: 0.12, title: "SEBI issues revised BRSR Core assurance timelines", tags: ["Regulatory", "ESG"] },
  { id: 4, source: "Bloomberg", time: "3h", sentiment: 0.44, title: "Atlas Industries wins multi-year defence casting contract", tags: ["Supply Chain"] },
  { id: 5, source: "FT", time: "5h", sentiment: -0.78, title: "Solstice Pharma litigation consolidated in New Jersey", tags: ["Litigation"] },
  { id: 6, source: "SEC EDGAR", time: "7h", sentiment: -0.08, title: "Meridian Financial discloses supervisory examination update", tags: ["Regulatory"] },
];

export const heatmap = riskCategories.map((category) => ({
  category,
  values: companies.map((c) => ({
    company: c.ticker,
    value: Math.round(((category.length * 7 + c.ticker.charCodeAt(0) + c.score) % 100)),
  })),
}));

export const severityMeta: Record<Severity, { label: string; color: string }> = {
  critical: { label: "Critical", color: "var(--severity-critical)" },
  high: { label: "High", color: "var(--severity-high)" },
  medium: { label: "Medium", color: "var(--severity-medium)" },
  low: { label: "Low", color: "var(--severity-low)" },
};
