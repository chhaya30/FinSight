import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { AlertCircle, ExternalLink, Factory } from "lucide-react";
import { GlassCard, PageHeader, ConfidenceMeter } from "@/components/ui-kit";
import { companies, heatmap } from "@/lib/mock-data";

const apiBase = import.meta.env["VITE_API_BASE_URL"] ?? "/api/v1";
type LiveCompany = { id: string; name: string; sector: string | null };
type LiveEvidence = { source: string; source_url: string | null; publication_date: string | null; excerpt: string | null };
type LiveIndustryResponse = { industry: string | null; provider: string; provider_available: boolean; error: string | null; themes: { id: string; name: string; category: string; relevance_score: number; evidence: LiveEvidence; supporting_evidence: LiveEvidence[] }[]; peers: { company_id: string; name: string; industry: string | null; risk_categories: string[]; evidence: LiveEvidence[] }[]; assessments: { title: string; category: string | null; classification: string; explanation: string; evidence: LiveEvidence[] }[]; peer_comparisons: { category: string; company_present: boolean; peer_names: string[]; explanation: string; evidence: LiveEvidence[] }[] };

export const Route = createFileRoute("/industry")({
  head: () => ({
    meta: [
      { title: "Industry Intelligence — GlobalRisk AI" },
      { name: "description", content: "Peer comparison, sector rankings and category heatmaps across the coverage universe." },
      { property: "og:title", content: "Industry Intelligence — GlobalRisk AI" },
      { property: "og:description", content: "Peer benchmarking and sector risk heatmaps." },
    ],
  }),
  component: IndustryLive,
});

function IndustryLive() {
  const [companies, setCompanies] = useState<LiveCompany[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [data, setData] = useState<LiveIndustryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    fetch(`${apiBase}/companies?page_size=100`, { signal: abort.signal })
      .then(async (r) => { if (!r.ok) throw new Error(`Company service returned ${r.status}`); return r.json(); })
      .then((body: { companies: LiveCompany[] }) => { setCompanies(body.companies); setCompanyId((id) => id || body.companies[0]?.id || ""); })
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Unable to load companies."); })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, []);
  useEffect(() => {
    if (!companyId) { setData(null); return; }
    const abort = new AbortController(); setLoading(true); setError(""); setData(null);
    fetch(`${apiBase}/industry-intelligence/${companyId}`, { signal: abort.signal })
      .then(async (r) => { if (!r.ok) throw new Error(`Industry intelligence returned ${r.status}`); return r.json() as Promise<LiveIndustryResponse>; })
      .then(setData)
      .catch((e: unknown) => { if (!(e instanceof DOMException && e.name === "AbortError")) setError(e instanceof Error ? e.message : "Unable to load industry evidence."); })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [companyId]);
  const company = companies.find((item) => item.id === companyId);
  return <div className="mx-auto max-w-[1400px]"><PageHeader eyebrow="Industry Intelligence" title="Peer and sector risk evidence" description="Compare existing company disclosures with externally sourced public peer filing evidence." />
    <div className="panel mb-4 flex flex-wrap items-center gap-3 p-4"><label className="text-xs text-muted-foreground">Company<select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="ml-2 rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground">{companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><span className="text-[10px] text-muted-foreground">Industry: {data?.industry ?? company?.sector ?? "Unavailable"} · Provider: {data?.provider ?? "SEC EDGAR"}</span></div>
    {error && <LiveState error>{error}</LiveState>}{data?.error && <LiveState error>{data.error}</LiveState>}{loading && <LiveState>Loading public peer filings and industry evidence…</LiveState>}
    {!loading && !error && data && !data.themes.length && !data.peers.length && <LiveState>No verified peer filing themes are available. No substitute industry or peer data is shown.</LiveState>}
    {!loading && !error && data && <div className="grid gap-4 lg:grid-cols-2"><section className="panel p-4"><h2 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Factory className="size-4 text-primary" />Industry themes</h2>{data.themes.length ? data.themes.map((theme) => <article key={theme.id} className="border-t border-border/60 py-3"><div className="flex justify-between gap-2"><h3 className="text-xs font-semibold">{theme.name}</h3><span className="text-[10px]">{theme.category} · {Math.round(theme.relevance_score * 100)}%</span></div><LiveSource evidence={theme.evidence} /><p className="mt-1 text-[10px] text-muted-foreground">{theme.evidence.excerpt}</p>{theme.supporting_evidence.map((e, i) => <div key={`${e.source}-${i}`}><LiveSource evidence={e} /><p className="mt-1 text-[10px] text-muted-foreground">{e.excerpt}</p></div>)}</article>) : <p className="text-xs text-muted-foreground">No themes corroborated by multiple peer filings.</p>}</section><section className="panel p-4"><h2 className="mb-3 text-sm font-semibold">Verified peer companies</h2>{data.peers.length ? data.peers.map((peer) => <article key={peer.company_id} className="border-t border-border/60 py-3"><h3 className="text-xs font-semibold">{peer.name}</h3><p className="text-[10px] text-muted-foreground">{peer.industry ?? data.industry} · {peer.risk_categories.join(", ")}</p>{peer.evidence.map((e, i) => <div key={`${e.source}-${i}`}><LiveSource evidence={e} /><p className="line-clamp-3 text-[10px] text-muted-foreground">{e.excerpt}</p></div>)}</article>) : <p className="text-xs text-muted-foreground">No verified same-industry peer filings were found.</p>}</section><section className="panel p-4"><h2 className="mb-3 text-sm font-semibold">Company risk comparisons</h2>{data.assessments.length ? data.assessments.map((item, i) => <article key={`${item.title}-${i}`} className="border-t border-border/60 py-3"><div className="flex justify-between gap-2"><h3 className="text-xs font-semibold">{item.category ?? "Risk"}</h3><span className="text-[10px]">{item.classification.replaceAll("_", " ")}</span></div><p className="mt-1 text-[10px] text-muted-foreground">{item.title} · {item.explanation}</p>{item.evidence.map((e, j) => <LiveSource key={`${e.source}-${j}`} evidence={e} />)}</article>) : <p className="text-xs text-muted-foreground">No comparable Phase 2 disclosures were available.</p>}</section><section className="panel p-4"><h2 className="mb-3 text-sm font-semibold">Peer category comparison</h2>{data.peer_comparisons.length ? data.peer_comparisons.map((item) => <article key={item.category} className="border-t border-border/60 py-3"><h3 className="text-xs font-semibold">{item.category} · {item.company_present ? "also disclosed" : "not found in company disclosures"}</h3><p className="mt-1 text-[10px] text-muted-foreground">{item.peer_names.join(", ")} · {item.explanation}</p>{item.evidence.map((e, i) => <LiveSource key={`${e.source}-${i}`} evidence={e} />)}</article>) : <p className="text-xs text-muted-foreground">No evidence-backed peer comparisons are available.</p>}</section></div>}
  </div>;
}
function LiveSource({ evidence }: { evidence: LiveEvidence }) { return <p className="mt-2 text-[9px] text-muted-foreground">{evidence.source}{evidence.publication_date ? ` · ${evidence.publication_date}` : " · date unavailable"}{evidence.source_url && <> · <a href={evidence.source_url} target="_blank" rel="noreferrer" className="text-primary underline">source <ExternalLink className="inline size-2.5" /></a></>}</p>; }
function LiveState({ children, error = false }: { children: React.ReactNode; error?: boolean }) { return <div className={`rounded-xl border p-4 text-xs ${error ? "border-destructive/40 text-destructive" : "border-border text-muted-foreground"}`}>{error && <AlertCircle className="mr-2 inline size-4" />}{children}</div>; }

const radarData = heatmap.slice(0, 6).map((r) => ({
  category: r.category,
  Kaveri: r.values[3]!.value,
  Peers: Math.round(r.values.reduce((a, b) => a + b.value, 0) / r.values.length),
}));

function Industry() {
  const ranked = [...companies].sort((a, b) => b.score - a.score);
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Industry Intelligence"
        title="Peer and sector benchmarking"
        description="Relative risk positioning across sectors, with category-level peer deltas and sector heatmaps."
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <GlassCard delay={0}>
          <h2 className="mb-3 text-sm font-semibold">Risk ranking</h2>
          <div className="space-y-2">
            {ranked.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-center gap-3 rounded-xl border border-border/60 bg-secondary/25 p-3"
              >
                <span className="num w-5 text-center text-xs text-muted-foreground">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-medium">{c.name}</p>
                  <p className="num text-[10px] text-muted-foreground">{c.sector} · {c.ticker}</p>
                </div>
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${c.score}%` }}
                    transition={{ duration: 0.7, delay: i * 0.05 }}
                    className="h-full rounded-full"
                    style={{ background: c.score > 70 ? "var(--severity-critical)" : "var(--gradient-primary)" }}
                  />
                </div>
                <span className="num w-8 text-right text-sm font-semibold">{c.score}</span>
              </motion.div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <h2 className="mb-3 text-sm font-semibold">Kaveri Energy vs sector peers</h2>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData} outerRadius="72%">
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 }} />
              <Radar dataKey="Peers" stroke="var(--chart-2)" fill="var(--chart-2)" fillOpacity={0.18} />
              <Radar dataKey="Kaveri" stroke="var(--chart-1)" fill="var(--chart-1)" fillOpacity={0.28} />
            </RadarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard className="mt-4" delay={0.2}>
        <h2 className="mb-3 text-sm font-semibold">Sector insight</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Energy leads the universe on composite risk (85) driven almost entirely by climate transition financing,
          while Technology shows the fastest category growth from a lower base as AI regulation disclosures appear
          for the first time. Financials remain stable but carry the highest regulatory persistence score.
        </p>
        <div className="mt-4"><ConfidenceMeter value={0.89} /></div>
      </GlassCard>
    </div>
  );
}
