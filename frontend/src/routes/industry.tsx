import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { AlertCircle, ExternalLink, Factory } from "lucide-react";
import { GlassCard, PageHeader, ConfidenceMeter } from "@/components/ui-kit";
import { api } from "@/lib/api";

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
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader eyebrow="Industry Intelligence" title="Peer and sector risk evidence" description="Compare existing company disclosures with externally sourced public peer filing evidence." />
      <div className="panel mb-4 flex flex-wrap items-center gap-3 p-4">
        <label className="text-xs text-muted-foreground">Company
          <select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="ml-2 rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground">
            {companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
        <span className="text-[10px] text-muted-foreground">Industry: {data?.industry ?? company?.sector ?? "Unavailable"} · Provider: {data?.provider ?? "SEC EDGAR"}</span>
      </div>
      {error && <LiveState error>{error}</LiveState>}
      {data?.error && <LiveState error>{data.error}</LiveState>}
      {loading && <LiveState>Loading public peer filings and industry evidence…</LiveState>}
      {!loading && !error && data && !data.themes.length && !data.peers.length && <LiveState>No verified peer filing themes are available. No substitute industry or peer data is shown.</LiveState>}
      {!loading && !error && data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="panel p-4">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
              <Factory className="size-4 text-primary" /> Industry themes
            </h2>
            {data.themes.length ? data.themes.map((theme) => (
              <article key={theme.id} className="border-t border-border/60 py-3">
                <div className="flex justify-between gap-2">
                  <h3 className="text-xs font-semibold">{theme.name}</h3>
                  <span className="text-[10px]">{theme.category} · {Math.round(theme.relevance_score * 100)}%</span>
                </div>
                <LiveSource evidence={theme.evidence} />
                <p className="mt-1 text-[10px] text-muted-foreground">{theme.evidence.excerpt}</p>
                {theme.supporting_evidence.map((e, i) => (
                  <div key={`${e.source}-${i}`}>
                    <LiveSource evidence={e} />
                    <p className="mt-1 text-[10px] text-muted-foreground">{e.excerpt}</p>
                  </div>
                ))}
              </article>
            )) : (
              <p className="text-xs text-muted-foreground">No themes corroborated by multiple peer filings.</p>
            )}
          </section>
          <section className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold">Verified peer companies</h2>
            {data.peers.length ? data.peers.map((peer) => (
              <article key={peer.company_id} className="border-t border-border/60 py-3">
                <h3 className="text-xs font-semibold">{peer.name}</h3>
                <p className="text-[10px] text-muted-foreground">{peer.industry ?? data.industry} · {peer.risk_categories.join(", ")}</p>
                {peer.evidence.map((e, i) => (
                  <div key={`${e.source}-${i}`}>
                    <LiveSource evidence={e} />
                    <p className="line-clamp-3 text-[10px] text-muted-foreground">{e.excerpt}</p>
                  </div>
                ))}
              </article>
            )) : (
              <p className="text-xs text-muted-foreground">No verified same-industry peer filings were found.</p>
            )}
          </section>
          <section className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold">Company risk comparisons</h2>
            {data.assessments.length ? data.assessments.map((item, i) => (
              <article key={`${item.title}-${i}`} className="border-t border-border/60 py-3">
                <div className="flex justify-between gap-2">
                  <h3 className="text-xs font-semibold">{item.title}</h3>
                  <span className="text-[10px]">{item.category ?? "N/A"} · {item.classification}</span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground">{item.explanation}</p>
                {item.evidence.map((e, j) => (
                  <div key={`${e.source}-${j}`}>
                    <LiveSource evidence={e} />
                  </div>
                ))}
              </article>
            )) : (
              <p className="text-xs text-muted-foreground">No risk assessments available.</p>
            )}
          </section>
          <section className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold">Peer comparisons</h2>
            {data.peer_comparisons.length ? data.peer_comparisons.map((item, i) => (
              <article key={`${item.category}-${i}`} className="border-t border-border/60 py-3">
                <div className="flex justify-between gap-2">
                  <h3 className="text-xs font-semibold">{item.category}</h3>
                  <span className="text-[10px]">{item.company_present ? "Company present" : "Company absent"}</span>
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground">{item.explanation}</p>
                <p className="text-[9px] text-muted-foreground">Peers: {item.peer_names.join(", ")}</p>
                {item.evidence.map((e, j) => (
                  <div key={`${e.source}-${j}`}>
                    <LiveSource evidence={e} />
                  </div>
                ))}
              </article>
            )) : (
              <p className="text-xs text-muted-foreground">No peer comparisons available.</p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function LiveSource({ evidence }: { evidence: LiveEvidence }) {
  return (
    <p className="mt-2 text-[9px] text-muted-foreground">
      {evidence.source}
      {evidence.publication_date ? ` · ${evidence.publication_date}` : " · date unavailable"}
      {evidence.source_url && (
        <>
          · <a href={evidence.source_url} target="_blank" rel="noreferrer" className="text-primary underline">
            source <ExternalLink className="inline size-2.5" />
          </a>
        </>
      )}
    </p>
  );
}

function LiveState({ children, error = false }: { children: React.ReactNode; error?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 text-xs ${error ? "border-destructive/40 text-destructive" : "border-border text-muted-foreground"}`}>
      {error && <AlertCircle className="mr-2 inline size-4" />}
      {children}
    </div>
  );
}