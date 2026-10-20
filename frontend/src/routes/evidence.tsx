import { useEffect, useMemo, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { ArrowLeftRight, FileSearch, Sparkle } from "lucide-react";
import { api } from "@/lib/api";
import { GlassCard, PageHeader, ConfidenceMeter, EvidenceLink, SeverityBadge } from "@/components/ui-kit";

export const Route = createFileRoute("/evidence")({
  head: () => ({ meta: [{ title: "Evidence Viewer — GlobalRisk AI" }] }),
  component: Evidence,
});

type Item = { risk: any; evidence?: any; id: string; label: string; tone: string };
type Comparison = { year_current: number; year_previous: number; [key: string]: any };
type Pair = { change_type?: string; previous_risk?: any; current_risk?: any; previous_evidence?: any; current_evidence?: any };
const groups = [["new_risks", "New risks", "var(--severity-high)"], ["removed_risks", "Removed risks", "var(--muted-foreground)"], ["severity_increased", "Severity increased", "var(--severity-critical)"], ["severity_decreased", "Severity decreased", "var(--severity-medium)"], ["modified_risks", "Modified risks", "var(--severity-high)"]] as const;

function EvidenceColumn({ label, year, evidence, risk, tone }: { label: string; year?: number; evidence?: any; risk?: any; tone: string }) {
  const text = evidence?.text || risk?.source_paragraph || risk?.summary || "No source evidence is available for this side.";
  const unavailable = !evidence && !risk;
  return <div className="panel flex min-h-[280px] flex-col p-0">
    <div className="flex items-center justify-between border-b border-border/60 px-4 py-3"><div><p className="text-sm font-semibold">{label}</p><p className="num text-[10px] text-muted-foreground">{year ? `FY${year}` : "Not present in this year"} · {evidence?.section || "Risk disclosure"}</p></div><span className="num rounded-md border px-2 py-0.5 text-[10px]" style={{ color: tone, borderColor: `color-mix(in oklab, ${tone} 40%, transparent)` }}>{evidence?.page ? `p.${evidence.page}` : "source"}</span></div>
    <p className={`p-5 text-sm leading-relaxed ${unavailable ? "text-muted-foreground/60 italic" : ""}`} style={!unavailable ? { background: `color-mix(in oklab, ${tone} 10%, transparent)`, boxShadow: `inset 2px 0 0 ${tone}` } : undefined}>{text}</p>
  </div>;
}

function Evidence() {
  const search = useSearch({ from: "/evidence" }) as { company_id?: string; year_current?: string; year_previous?: string; risk_id?: string };
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [pair, setPair] = useState<Pair | null>(null);
  const [selectedId, setSelectedId] = useState(search.risk_id || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const items = useMemo<Item[]>(() => comparison ? groups.flatMap(([key, label, tone]) => (comparison[key] || []).map((item: any) => ({ ...item, id: item.risk.id, label, tone }))) : [], [comparison]);
  const selected = items.find((item) => item.id === selectedId) || items[0];

  useEffect(() => {
    if (!search.company_id || !search.year_current || !search.year_previous) return;
    setLoading(true); setError("");
    api.comparison.compare({ company_id: search.company_id, year_current: Number(search.year_current), year_previous: Number(search.year_previous) }).then((data) => setComparison(data as Comparison)).catch((err) => setError(err instanceof Error ? err.message : "Unable to load comparison")).finally(() => setLoading(false));
  }, [search.company_id, search.year_current, search.year_previous]);
  useEffect(() => {
    if (!selected?.id) { setPair(null); return; }
    setLoading(true); setError("");
    api.comparison.getRiskEvidence(selected.id).then((data) => setPair(data as Pair)).catch((err) => setError(err instanceof Error ? err.message : "Unable to load evidence")).finally(() => setLoading(false));
  }, [selected?.id]);

  if (!search.company_id || !search.year_current || !search.year_previous) return <EmptyState text="Open this viewer with company_id, year_previous and year_current query parameters." />;
  if (error) return <EmptyState text={error} />;
  if (loading && !comparison) return <EmptyState text="Loading comparison evidence…" />;
  if (!comparison) return <EmptyState text="No comparison data found." />;
  const current = pair?.current_risk || selected?.risk;
  const previous = pair?.previous_risk;
  const currentEvidence = pair?.current_evidence || selected?.evidence;
  const severity = current?.severity || selected?.risk?.severity || "medium";

  return <div className="mx-auto max-w-[1400px]">
    <PageHeader eyebrow="Evidence Viewer" title="Side-by-side disclosure comparison" description="Select a detected year-over-year change to inspect its source evidence." actions={<span className="num flex items-center gap-2 rounded-xl border border-border bg-secondary/40 px-3 py-2 text-xs"><ArrowLeftRight className="size-3.5 text-primary" /> FY{comparison.year_previous} ↔ FY{comparison.year_current}</span>} />
    <div className="mb-4 flex flex-wrap items-center gap-2"><select value={selected?.id || ""} onChange={(e) => setSelectedId(e.target.value)} className="min-w-[280px] rounded-lg border border-border bg-secondary/40 px-3 py-2 text-sm">{items.map((item) => <option key={item.id} value={item.id}>{item.label} · {item.risk.category} · {item.risk.summary}</option>)}</select><span className="text-xs text-muted-foreground">{items.length} changes available</span></div>
    {selected ? <><div className="mb-4 flex flex-wrap items-center gap-2"><span className="text-sm font-semibold">{selected.risk.category}</span><SeverityBadge severity={severity} /><ConfidenceMeter value={current?.confidence_score || selected.risk.confidence_score || 0} /><span className="text-xs text-muted-foreground">{pair?.change_type || selected.label}</span></div>
      <div className="grid gap-4 lg:grid-cols-2"><EvidenceColumn label="Previous annual report" year={comparison.year_previous} evidence={pair?.previous_evidence} risk={previous} tone="var(--muted-foreground)" /><EvidenceColumn label="Current annual report" year={comparison.year_current} evidence={currentEvidence} risk={current} tone="var(--severity-critical)" /></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3"><GlassCard className="lg:col-span-2" delay={0.1}><div className="mb-3 flex items-center gap-2"><Sparkle className="size-4 text-primary" /><h2 className="text-sm font-semibold">Change context</h2></div><p className="text-sm leading-relaxed text-muted-foreground">{selected.risk.summary}</p><div className="mt-4 flex flex-wrap gap-2">{pair?.previous_evidence?.page && <EvidenceLink source={`FY${comparison.year_previous} AR p.${pair.previous_evidence.page}`} />}{currentEvidence?.page && <EvidenceLink source={`FY${comparison.year_current} AR p.${currentEvidence.page}`} />}</div></GlassCard><GlassCard delay={0.15}><h2 className="mb-3 text-sm font-semibold">Source details</h2><div className="space-y-2 text-xs text-muted-foreground"><p>Risk ID: <span className="num text-foreground">{selected.id}</span></p><p>Category: <span className="text-foreground">{selected.risk.category}</span></p><p>Current page: <span className="num text-foreground">{currentEvidence?.page || "—"}</span></p></div></GlassCard></div>
    </> : <EmptyState text="This comparison has no detected risk changes." />}
  </div>;
}
function EmptyState({ text }: { text: string }) { return <div className="flex min-h-[360px] items-center justify-center rounded-2xl border border-dashed border-border text-sm text-muted-foreground"><div className="flex items-center gap-2"><FileSearch className="size-4" />{text}</div></div>; }
