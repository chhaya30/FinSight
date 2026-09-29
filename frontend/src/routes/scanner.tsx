import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertCircle, Plus, ScanSearch, Trash2, Zap } from "lucide-react";
import { ConfidenceMeter, GlassCard, PageHeader } from "@/components/ui-kit";

type Factor = "category" | "status" | "severity" | "financial_signal" | "market_signal" | "industry_signal" | "evidence_quality" | "classification_confidence";
type Criterion = { factor: Factor; operator: "eq" | "gte" | "observed"; value: string | number | boolean };
type Clause = Criterion & { id: number };
type Options = { companies: { id: string; name: string; sector: string | null }[]; sectors: string[]; years: number[]; categories: string[]; severities: string[]; statuses: string[]; factor_operators: Record<Factor, string[]> };
type FactorResult = { factor: Factor; label: string; observed: boolean; value: unknown; score: number | null; explanation: string; evidence: { document_id: string | null; source_url: string | null; report_year: number | null; page: number | null; chunk_id: string | null; source: string; excerpt: string }[] };
type Result = { risk_id: string; company_id: string; company_name: string; sector: string | null; report_year: number; previous_year: number | null; title: string; category: string; severity: string; status: string; classification_confidence: number; evidence_quality: number; overall_score: number; assessment: string; coverage: number; matched: boolean; contributing_factors: FactorResult[] };
type ScanResponse = { scan_id: string; logic: "AND" | "OR"; total_matches: number; page: number; page_size: number; results: Result[]; factor_weights: Record<string, number> };
const apiBase = import.meta.env["VITE_API_BASE_URL"] ?? "/api/v1";
const FACTORS: { value: Factor; label: string }[] = [
  { value: "category", label: "Risk category" },
  { value: "status", label: "Evolution status" }, { value: "severity", label: "Severity" },
  { value: "financial_signal", label: "Financial change" }, { value: "market_signal", label: "Market signal" },
  { value: "industry_signal", label: "Industry signal" }, { value: "evidence_quality", label: "Evidence provenance" },
  { value: "classification_confidence", label: "Classification confidence" },
];

export const Route = createFileRoute("/scanner")({
  head: () => ({ meta: [{ title: "Multi-Factor Risk Scanner — GlobalRisk AI" }, { name: "description", content: "Screen evidence-linked company risk signals with deterministic AND/OR criteria." }] }),
  component: Scanner,
});

function Scanner() {
  const [options, setOptions] = useState<Options | null>(null);
  const [criteria, setCriteria] = useState<Clause[]>([]);
  const [logic, setLogic] = useState<"AND" | "OR">("AND");
  const [companyId, setCompanyId] = useState("");
  const [sector, setSector] = useState("");
  const [yearCurrent, setYearCurrent] = useState("");
  const [yearPrevious, setYearPrevious] = useState("");
  const [page, setPage] = useState(1);
  const [response, setResponse] = useState<ScanResponse | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [optionsError, setOptionsError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/scanner/options`, { signal: controller.signal })
      .then(async (result) => { if (!result.ok) throw new Error(`Scanner options returned ${result.status}`); return result.json() as Promise<Options>; })
      .then(setOptions)
      .catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) setOptionsError(cause instanceof Error ? cause.message : "Unable to load scan options."); })
      .finally(() => { if (!controller.signal.aborted) setLoadingOptions(false); });
    return () => controller.abort();
  }, []);

  const addClause = () => setCriteria((items) => [...items, { id: Date.now(), factor: "severity", operator: "gte", value: 0.78 }]);
  const updateClause = (id: number, patch: Partial<Clause>) => setCriteria((items) => items.map((item) => item.id === id ? { ...item, ...patch } : item));
  const valuesFor = (factor: Factor): (string | number | boolean)[] => {
    if (factor === "category") return options?.categories ?? [];
    if (factor === "status") return options?.statuses ?? [];
    if (factor === "severity") return ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"];
    if (factor === "financial_signal") return ["ADVERSE", "FAVORABLE", "MIXED"];
    if (factor === "market_signal") return ["RELATED", "NONE"];
    if (factor === "industry_signal") return ["INDUSTRY_WIDE", "COMPANY_SPECIFIC", "UNCLASSIFIED", "NONE"];
    if (factor === "evidence_quality" || factor === "classification_confidence") return [0, 0.25, 0.5, 0.75, 0.9];
    return [true, false];
  };
  const factorLabel = useMemo(() => Object.fromEntries(FACTORS.map((factor) => [factor.value, factor.label])) as Record<Factor, string>, []);

  const run = async (nextPage = 1) => {
    setLoading(true); setError(""); setPage(nextPage);
    const body = {
      company_ids: companyId ? [companyId] : [], sectors: sector ? [sector] : [],
      year_current: yearCurrent ? Number(yearCurrent) : null,
      year_previous: yearPrevious ? Number(yearPrevious) : null,
      logic, criteria: criteria.map(({ factor, operator, value }) => ({ factor, operator, value })),
      page: nextPage, page_size: 50,
    };
    try {
      const result = await fetch(`${apiBase}/scanner/run`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      if (!result.ok) throw new Error(`Scan returned ${result.status}`);
      setResponse(await result.json() as ScanResponse);
    } catch (cause) {
      setResponse(null);
      setError(cause instanceof Error ? cause.message : "Unable to run the scan.");
    } finally { setLoading(false); }
  };

  return <div className="mx-auto max-w-[1400px]">
    <PageHeader eyebrow="Scanner" title="Multi-factor risk scanner" description="Combine Phase 2 evolution with financial, market, industry, evidence, and confidence signals. Every result shows its inputs and limits." />
    <GlassCard delay={0}>
      <div className="mb-4 flex items-center gap-2"><ScanSearch className="size-4 text-primary" /><h2 className="text-sm font-semibold">Screen definition</h2><div className="ml-auto flex overflow-hidden rounded-lg border border-border text-[10px]">{(["AND", "OR"] as const).map((value) => <button key={value} onClick={() => setLogic(value)} className={`px-3 py-1.5 ${logic === value ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>{value}</button>)}</div></div>
      {optionsError && <StateMessage error>{optionsError}</StateMessage>}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Filter label="Company" value={companyId} onChange={setCompanyId}><option value="">All companies</option>{options?.companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Filter>
        <Filter label="Sector" value={sector} onChange={setSector}><option value="">All sectors</option>{options?.sectors.map((item) => <option key={item}>{item}</option>)}</Filter>
        <Filter label="Current year" value={yearCurrent} onChange={(value) => { setYearCurrent(value); if (value && yearPrevious && Number(yearPrevious) >= Number(value)) setYearPrevious(""); }}><option value="">Latest available per company</option>{options?.years.map((item) => <option key={item}>{item}</option>)}</Filter>
        <Filter label="Previous year" value={yearPrevious} onChange={setYearPrevious}><option value="">Nearest earlier report</option>{options?.years.filter((item) => !yearCurrent || item < Number(yearCurrent)).map((item) => <option key={item}>{item}</option>)}</Filter>
      </div>
      <div className="space-y-2">
        {criteria.map((clause, index) => <div key={clause.id} className="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-secondary/25 p-2.5">
          <span className="w-8 text-[10px] text-primary">{index === 0 ? "IF" : logic}</span>
          <select value={clause.factor} onChange={(event) => { const factor = event.target.value as Factor; const operator = (options?.factor_operators[factor]?.[0] ?? "eq") as Clause["operator"]; updateClause(clause.id, { factor, operator, value: valuesFor(factor)[0] ?? "" }); }} className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs">{FACTORS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select>
          <select value={clause.operator} onChange={(event) => updateClause(clause.id, { operator: event.target.value as Clause["operator"], value: event.target.value === "observed" ? true : clause.operator === "observed" ? valuesFor(clause.factor)[0] ?? "" : clause.value })} className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs">{(options?.factor_operators[clause.factor] ?? ["eq"]).map((operator) => <option key={operator} value={operator}>{operator === "gte" ? "at least" : operator === "observed" ? "is observed" : "is"}</option>)}</select>
          {clause.operator === "observed" ? <select value={String(clause.value)} onChange={(event) => updateClause(clause.id, { value: event.target.value === "true" })} className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs"><option value="true">yes</option><option value="false">no</option></select> : <select value={String(clause.value)} onChange={(event) => updateClause(clause.id, { value: clause.factor === "evidence_quality" || clause.factor === "classification_confidence" || clause.operator === "gte" ? Number(event.target.value) : event.target.value })} className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs">{valuesFor(clause.factor).map((value) => <option key={String(value)} value={String(value)}>{typeof value === "number" ? `${Math.round(value * 100)}%` : String(value)}</option>)}</select>}
          <button aria-label="Remove condition" onClick={() => setCriteria((items) => items.filter((item) => item.id !== clause.id))} className="ml-auto rounded-md p-1 text-muted-foreground hover:bg-secondary"><Trash2 className="size-3.5" /></button>
        </div>)}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button disabled={loadingOptions || !options} onClick={addClause} className="flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3 py-2 text-xs disabled:opacity-50"><Plus className="size-3.5" />Add condition</button>
        <button disabled={loading || loadingOptions} onClick={() => void run(1)} className="flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-medium disabled:opacity-50" style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}><Zap className="size-3.5" />{loading ? "Scanning…" : "Run scan"}</button>
      </div>
    </GlassCard>

    {loadingOptions && <div className="mt-4"><StateMessage>Loading available companies and report years…</StateMessage></div>}
    {error && <div className="mt-4"><StateMessage error>{error}</StateMessage></div>}
    {response && <GlassCard className="mt-4" delay={0.1}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-sm font-semibold">Scan results</h2><p className="text-[10px] text-muted-foreground">{response.total_matches} matching risks · {logic} criteria · results ranked by transparent observed-signal score</p></div><span className="rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground">{response.scan_id}</span></div>
      {response.results.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">No risks meet these criteria in the selected report scope.</p> : <div className="space-y-3">{response.results.map((result) => <ResultCard key={`${result.risk_id}-${result.report_year}`} result={result} />)}</div>}
      {response.total_matches > response.page_size && <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground"><span>Page {response.page}</span><div className="flex gap-2"><button disabled={page <= 1 || loading} onClick={() => void run(page - 1)} className="rounded-md border border-border px-2.5 py-1 disabled:opacity-40">Previous</button><button disabled={page * response.page_size >= response.total_matches || loading} onClick={() => void run(page + 1)} className="rounded-md border border-border px-2.5 py-1 disabled:opacity-40">Next</button></div></div>}
      <p className="mt-4 border-t border-border/60 pt-3 text-[10px] leading-relaxed text-muted-foreground">Score weights: {Object.entries(response.factor_weights).map(([factor, weight]) => `${factorLabel[factor as Factor] ?? factor} ${Math.round(weight * 100)}%`).join(" · ")}. Missing factors are omitted and remaining weights are normalized. Classification confidence and evidence provenance are reported separately. Scores summarize co-occurrence and disclosed conditions; they are not causal conclusions or outcome probabilities.</p>
    </GlassCard>}
  </div>;
}

function ResultCard({ result }: { result: Result }) {
  return <article className="rounded-xl border border-border/70 bg-secondary/20 p-4">
    <div className="flex flex-wrap items-start gap-3"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full border border-border px-2 py-0.5 text-[10px] uppercase">{result.severity}</span><span className="text-[10px] text-muted-foreground">{result.category} · {result.status} · FY{result.report_year}{result.previous_year ? ` vs FY${result.previous_year}` : ""}</span></div><h3 className="mt-2 text-sm font-semibold">{result.title}</h3><p className="mt-1 text-[11px] text-muted-foreground">{result.company_name}{result.sector ? ` · ${result.sector}` : ""}</p></div><div className="w-44"><p className="mb-1 text-[10px] text-muted-foreground">Observed-signal score · {Math.round(result.overall_score * 100)}</p><div className="h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full bg-primary" style={{ width: `${result.overall_score * 100}%` }} /></div></div></div>
    <p className="mt-3 text-xs leading-relaxed text-muted-foreground">{result.assessment}</p>
    <div className="mt-3 grid gap-3 sm:grid-cols-3"><div><p className="mb-1 text-[10px] text-muted-foreground">Classification confidence · {Math.round(result.classification_confidence * 100)}%</p><ConfidenceMeter value={result.classification_confidence} /></div><div><p className="mb-1 text-[10px] text-muted-foreground">Evidence quality · {Math.round(result.evidence_quality * 100)}%</p><ConfidenceMeter value={result.evidence_quality} /></div><div><p className="mb-1 text-[10px] text-muted-foreground">Signal coverage · {Math.round(result.coverage * 100)}%</p><ConfidenceMeter value={result.coverage} /></div></div>
    <div className="mt-4 grid gap-2 lg:grid-cols-2">{result.contributing_factors.map((factor) => <div key={factor.factor} className="rounded-lg border border-border/60 bg-background/35 p-3"><div className="flex items-center justify-between gap-2"><p className="text-[11px] font-semibold">{factor.label}</p><span className="text-[10px] text-muted-foreground">{factor.observed ? String(factor.value) : "Unavailable"}{factor.score !== null ? ` · ${Math.round(factor.score * 100)}` : ""}</span></div><p className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{factor.explanation}</p>{factor.evidence.map((evidence, index) => <div key={`${evidence.document_id}-${evidence.page}-${index}`} className="mt-2 border-t border-border/50 pt-2 text-[10px] text-muted-foreground"><p>{evidence.document_id ?? evidence.source}{evidence.report_year ? ` · FY${evidence.report_year}` : ""}{evidence.page ? ` · p. ${evidence.page}` : ""}{evidence.chunk_id ? ` · chunk ${evidence.chunk_id}` : ""} · {evidence.source}{evidence.source_url && <> · <a href={evidence.source_url} target="_blank" rel="noreferrer" className="text-primary underline">source link</a></>}</p>{evidence.excerpt && <p className="mt-1 line-clamp-2">{evidence.excerpt}</p>}</div>)}</div>)}</div>
  </article>;
}

function Filter({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return <label className="block text-[10px] text-muted-foreground">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-lg border border-border bg-secondary/40 px-2 py-2 text-xs text-foreground outline-none"><>{children}</></select></label>;
}
function StateMessage({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return <div className={`rounded-xl border p-4 text-xs ${error ? "border-destructive/40 text-destructive" : "border-border/60 text-muted-foreground"}`}>{error && <AlertCircle className="mr-2 inline size-4" />}{children}</div>;
}
