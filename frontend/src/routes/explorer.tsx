import { useEffect, useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertCircle, Search, SlidersHorizontal } from "lucide-react";
import { ConfidenceMeter, PageHeader } from "@/components/ui-kit";

type ExplorerItem = {
  risk_id: string; company_id: string; company_name: string; report_id: string; year: number; comparison_year: number;
  category: string; severity: string; status: string; title: string; summary: string;
  confidence: number; source_document: string; source_page: number | null; previous_risk_id: string | null;
};
type ExplorerList = {
  items: ExplorerItem[]; total: number; page: number; page_size: number; companies: { id: string; name: string }[];
  categories: string[]; severities: string[]; years: number[]; statuses: string[];
};
type Evidence = { document: string; year: number; page: number | null; chunk_id: string | null; source: string; text: string };
type ClassificationAssessment = { category_confidence: number; severity_confidence: number; classification_confidence: number; evidence_quality: number; low_confidence: boolean; confidence_reason: string; supporting_evidence: Evidence[] };
type RiskVersion = { risk_id: string; year: number; category: string; severity: string; confidence: number; title: string; summary: string; evidence: Evidence; classification_assessment: ClassificationAssessment };
type Claim = { text: string; evidence: { document_id: string; report_year: number | null; page: number; chunk_id: string | null; text_excerpt: string }[] };
type Detail = {
  company_name: string; status: string; current_risk: RiskVersion | null; previous_risk: RiskVersion | null;
  explanation: null | { what_changed: { name: string; before: unknown; after: unknown }[]; why_it_matters: Claim; business_impact: Claim; confidence_score: number; confidence_reason: string };
  financial_analysis: null | { changes: { metric_name: string; direction: string; previous_value: number | null; current_value: number | null; supporting_evidence: { document_id: string; page: number }[] }[] };
  market_signals: null | { provider_available: boolean; events: { title: string; summary: string | null; evidence: { source: string; source_url: string | null } }[]; error: string | null };
  industry_signals: null | { provider_available: boolean; themes: { name: string; evidence: { source: string; source_url: string | null } }[]; peers: { name: string; evidence: { source: string }[] }[]; error: string | null };
};
const apiBase = import.meta.env["VITE_API_BASE_URL"] ?? "/api/v1";

export const Route = createFileRoute("/explorer")({
  head: () => ({ meta: [{ title: "Risk Explorer — GlobalRisk AI" }, { name: "description", content: "Explore evidenced company risks and their year-over-year evolution." }] }),
  component: Explorer,
});

function EvidenceCard({ evidence }: { evidence: Evidence }) {
  return <div className="rounded-lg border border-border/60 bg-secondary/25 p-3">
    <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
      <span className="font-medium text-foreground">{evidence.document}</span><span>FY{evidence.year}</span>
      {evidence.page && <span>p. {evidence.page}</span>}{evidence.chunk_id && <span>chunk {evidence.chunk_id}</span>}
      <span className="ml-auto">{evidence.source}</span>
    </div>
    <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed">{evidence.text || "No source paragraph was stored for this risk."}</p>
  </div>;
}

function Explorer() {
  const [data, setData] = useState<ExplorerList | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [companyId, setCompanyId] = useState("");
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState("");
  const [year, setYear] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (companyId) params.set("company_id", companyId);
    if (category) params.set("category", category);
    if (severity) params.set("severity", severity);
    if (year) params.set("year", year);
    if (status) params.set("status", status);
    if (search.trim()) params.set("search", search.trim());
    params.set("page", String(page));
    params.set("page_size", "50");
    return params.toString();
  }, [companyId, category, severity, year, status, search, page]);

  useEffect(() => { setPage(1); }, [companyId, category, severity, year, status, search]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    fetch(`${apiBase}/risk-explorer${query ? `?${query}` : ""}`, { signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`Risk service returned ${response.status}`); return response.json() as Promise<ExplorerList>; })
      .then(setData)
      .catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) { setData(null); setError(cause instanceof Error ? cause.message : "Unable to load risks."); } })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query]);

  useEffect(() => {
    if (!data || data.items.some((item) => item.risk_id === selectedId && item.comparison_year === selectedYear)) return;
    const first = data.items[0];
    setSelectedId(first?.risk_id ?? "");
    setSelectedYear(first?.comparison_year ?? null);
  }, [data, selectedId, selectedYear]);

  useEffect(() => {
    if (!selectedId) { setDetail(null); return; }
    const controller = new AbortController();
    setDetail(null); setDetailLoading(true); setDetailError("");
    fetch(`${apiBase}/risk-explorer/${selectedId}${selectedYear ? `?year=${selectedYear}` : ""}`, { signal: controller.signal })
      .then(async (response) => { if (!response.ok) throw new Error(`Risk detail returned ${response.status}`); return response.json() as Promise<Detail>; })
      .then(setDetail)
      .catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) setDetailError(cause instanceof Error ? cause.message : "Unable to load risk details."); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selectedId, selectedYear]);

  const active = data?.items.find((item) => item.risk_id === selectedId && item.comparison_year === selectedYear);
  return <div className="mx-auto max-w-[1600px]">
    <PageHeader eyebrow="Risk Explorer" title="Explore company disclosures" description="Search risks across issuers and inspect evidence, matched prior-year language, and related intelligence." />
    <div className="grid gap-4 xl:grid-cols-[340px_minmax(360px,0.9fr)_minmax(440px,1.1fr)]">
      <section className="space-y-3">
        <div className="panel space-y-3 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal className="size-4 text-primary" />Filters</div>
          <label className="relative block"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search company or risk text" className="w-full rounded-lg border border-border bg-secondary/40 py-2 pl-9 pr-3 text-xs outline-none focus:border-primary/50" /></label>
          <Filter label="Company" value={companyId} onChange={setCompanyId}><option value="">All companies</option>{data?.companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Filter>
          <div className="grid grid-cols-2 gap-2">
            <Filter label="Category" value={category} onChange={setCategory}><option value="">All categories</option>{data?.categories.map((item) => <option key={item}>{item}</option>)}</Filter>
            <Filter label="Severity" value={severity} onChange={setSeverity}><option value="">All severities</option>{data?.severities.map((item) => <option key={item}>{item}</option>)}</Filter>
            <Filter label="Year" value={year} onChange={setYear}><option value="">Latest available</option>{data?.years.map((item) => <option key={item}>{item}</option>)}</Filter>
            <Filter label="Status" value={status} onChange={setStatus}><option value="">All statuses</option>{data?.statuses.map((item) => <option key={item}>{item}</option>)}</Filter>
          </div>
        </div>
        <div className="flex items-center justify-between px-1 text-xs text-muted-foreground"><span>{loading ? "Loading risks…" : `${data?.total ?? 0} risks`}</span><span>{active ? `Selected FY${active.year}` : ""}</span></div>
        {error && <StateMessage error>{error}</StateMessage>}
        {!loading && !error && data?.items.length === 0 && <StateMessage>No risks match these filters. Try clearing a filter or broadening your search.</StateMessage>}
        <div className="max-h-[72vh] space-y-2 overflow-y-auto pr-1" aria-busy={loading}>
          {data?.items.map((item) => <button key={`${item.risk_id}-${item.comparison_year}`} onClick={() => { setSelectedId(item.risk_id); setSelectedYear(item.comparison_year); }} className={`w-full rounded-xl border p-3 text-left transition-colors ${item.risk_id === selectedId && item.comparison_year === selectedYear ? "border-primary/60 bg-primary/5" : "border-border/70 bg-card/50 hover:border-primary/35"}`}>
            <div className="flex flex-wrap items-center gap-2"><RiskSeverity severity={item.severity} /><span className="rounded-md border border-border px-1.5 py-0.5 text-[10px]">{item.category}</span><span className="ml-auto text-[10px] text-muted-foreground">{item.status}</span></div>
            <p className="mt-2 text-xs font-semibold">{item.title}</p><p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">{item.summary}</p>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground"><span>{item.company_name} · FY{item.year}</span><span>{Math.round(item.confidence * 100)}% confidence</span></div>
          </button>)}
        </div>
        {(data?.total ?? 0) > 50 && <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{(page - 1) * 50 + 1}–{Math.min(page * 50, data?.total ?? 0)} of {data?.total}</span>
          <div className="flex gap-2"><button disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="rounded-md border border-border px-2.5 py-1 disabled:opacity-40">Previous</button><button disabled={page * 50 >= (data?.total ?? 0)} onClick={() => setPage((value) => value + 1)} className="rounded-md border border-border px-2.5 py-1 disabled:opacity-40">Next</button></div>
        </div>}
      </section>

      <section className="panel min-h-[440px] space-y-4 p-4" aria-live="polite">
        {detailLoading && <StateMessage>Loading risk detail and related signals…</StateMessage>}
        {detailError && <StateMessage error>{detailError}</StateMessage>}
        {!detailLoading && !detailError && !selectedId && <StateMessage>Select a risk to inspect its details.</StateMessage>}
        {detail && !detailLoading && <>
          <div><p className="text-[10px] uppercase tracking-wider text-muted-foreground">{detail.company_name} · {detail.status}</p><h2 className="mt-1 text-base font-semibold">{active?.title ?? detail.current_risk?.title ?? detail.previous_risk?.title}</h2></div>
          {detail.explanation && <>
            <InfoBlock title="What changed">{detail.explanation.what_changed.length ? detail.explanation.what_changed.map((change) => <p key={change.name} className="text-xs"><b>{change.name}</b>: {String(change.before ?? "—")} → {String(change.after ?? "—")}</p>) : detail.explanation.why_it_matters.text}</InfoBlock>
            <InfoBlock title="Why it matters">{detail.explanation.why_it_matters.text}</InfoBlock>
            <InfoBlock title="Business impact">{detail.explanation.business_impact.text}</InfoBlock>
            <div className="space-y-1"><ConfidenceMeter value={detail.explanation.confidence_score} /><p className="text-[10px] text-muted-foreground">{detail.explanation.confidence_reason}</p></div>
          </>}
          {detail.current_risk && <div><h3 className="mb-2 text-xs font-semibold">Current · FY{detail.current_risk.year}</h3><EvidenceCard evidence={detail.current_risk.evidence} /><ClassificationCard assessment={detail.current_risk.classification_assessment} category={detail.current_risk.category} severity={detail.current_risk.severity} /></div>}
          {detail.previous_risk && <div><h3 className="mb-2 text-xs font-semibold">Matched prior year · FY{detail.previous_risk.year}</h3><EvidenceCard evidence={detail.previous_risk.evidence} /><ClassificationCard assessment={detail.previous_risk.classification_assessment} category={detail.previous_risk.category} severity={detail.previous_risk.severity} /></div>}
          {!detail.current_risk && !detail.previous_risk && <StateMessage>No risk version or source evidence is available.</StateMessage>}
        </>}
      </section>

      <section className="space-y-4">
        {detail?.financial_analysis && <InfoBlock title="Financial context">{detail.financial_analysis.changes.length ? detail.financial_analysis.changes.map((change) => <p key={change.metric_name} className="text-xs">{change.metric_name}: {change.previous_value ?? "—"} → {change.current_value ?? "—"} ({change.direction})</p>) : "No financial metric changes were extracted for this report pair."}</InfoBlock>}
        <InfoBlock title="Market signals">{detail?.market_signals?.events?.length ? detail.market_signals.events.map((event) => <p key={event.title} className="text-xs">{event.title} — {event.evidence.source}</p>) : detail?.market_signals?.error ?? "No related market signals are available."}</InfoBlock>
        <InfoBlock title="Industry signals">{detail?.industry_signals?.themes?.length || detail?.industry_signals?.peers?.length ? <>{detail.industry_signals.themes.map((theme) => <p key={theme.name} className="text-xs">Theme: {theme.name} — {theme.evidence.source}</p>)}{detail.industry_signals.peers.map((peer) => <p key={peer.name} className="text-xs">Peer: {peer.name} — {peer.evidence.map((source) => source.source).join(", ")}</p>)}</> : detail?.industry_signals?.error ?? "No related industry signals are available."}</InfoBlock>
      </section>
    </div>
  </div>;
}

function Filter({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return <label className="block text-[10px] text-muted-foreground">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-lg border border-border bg-secondary/40 px-2 py-2 text-xs text-foreground outline-none"><>{children}</></select></label>;
}
function RiskSeverity({ severity }: { severity: string }) {
  const normalized = severity.toLowerCase();
  const color = normalized === "critical" ? "var(--severity-critical)" : normalized === "high" ? "var(--severity-high)" : normalized === "medium" ? "var(--severity-medium)" : normalized === "low" ? "var(--severity-low)" : "var(--muted-foreground)";
  return <span className="rounded-full border px-2 py-0.5 text-[10px] uppercase" style={{ color, borderColor: `color-mix(in oklab, ${color} 40%, transparent)` }}>{severity}</span>;
}
function InfoBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="rounded-xl border border-border/70 bg-card/50 p-4"><h3 className="mb-2 text-xs font-semibold">{title}</h3><div className="space-y-2 text-xs leading-relaxed text-muted-foreground">{children}</div></div>;
}
function ClassificationCard({ assessment, category, severity }: { assessment: ClassificationAssessment; category: string; severity: string }) {
  return <div className={`mt-2 rounded-lg border p-3 ${assessment.low_confidence ? "border-amber-500/40 bg-amber-500/5" : "border-border/60 bg-background/35"}`}>
    <div className="flex items-center justify-between gap-2"><p className="text-[10px] font-semibold">Classification confidence</p>{assessment.low_confidence && <span className="rounded border border-amber-500/40 px-1.5 py-0.5 text-[9px] text-amber-600">Low confidence</span>}</div>
    <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]"><span>Category · {category} · {Math.round(assessment.category_confidence * 100)}%</span><span>Severity · {severity} · {Math.round(assessment.severity_confidence * 100)}%</span><span>Overall · {Math.round(assessment.classification_confidence * 100)}%</span><span>Evidence quality · {Math.round(assessment.evidence_quality * 100)}%</span></div>
    <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">{assessment.confidence_reason}</p>
    {assessment.supporting_evidence.map((evidence, index) => <p key={`${evidence.document}-${evidence.page}-${index}`} className="mt-1 text-[9px] text-muted-foreground">Evidence: {evidence.document} · FY{evidence.year}{evidence.page ? ` · p. ${evidence.page}` : " · page unavailable"}{evidence.chunk_id ? ` · chunk ${evidence.chunk_id}` : " · chunk unavailable"}</p>)}
  </div>;
}
function StateMessage({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return <div className={`rounded-xl border p-4 text-xs ${error ? "border-destructive/40 text-destructive" : "border-border/60 text-muted-foreground"}`}>{error && <AlertCircle className="mb-2 size-4" />}{children}</div>;
}
