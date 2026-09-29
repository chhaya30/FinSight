import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { AlertCircle, ExternalLink, Newspaper } from "lucide-react";
import { PageHeader } from "@/components/ui-kit";

const apiBase = import.meta.env["VITE_API_BASE_URL"] ?? "/api/v1";
type Company = { id: string; name: string; sector: string | null; latest_report_year?: number | null };
type Event = { id: string; title: string; source: string; source_url: string | null; publication_date: string | null; summary: string | null; category: string; relevance_score: number; evidence: { excerpt: string | null } };
type MarketResponse = { provider: string; provider_available: boolean; events: Event[]; related_risks: { event_id: string; change_type: string | null; confidence_score: number; explanation: string }[]; error: string | null };

export const Route = createFileRoute("/market")({
  head: () => ({
    meta: [
      { title: "Market Intelligence — GlobalRisk AI" },
      { name: "description", content: "Real-time news feed, SEBI and SEC filings, sentiment analysis and configurable risk alerts." },
      { property: "og:title", content: "Market Intelligence — GlobalRisk AI" },
      { property: "og:description", content: "News, regulatory filings and sentiment for covered issuers." },
    ],
  }),
  component: Market,
});

function Market() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [companyId, setCompanyId] = useState("");
  const [response, setResponse] = useState<MarketResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/companies?page_size=100`, { signal: controller.signal })
      .then(async (r) => { if (!r.ok) throw new Error(`Company service returned ${r.status}`); return r.json(); })
      .then((body: { companies: Company[] }) => { setCompanies(body.companies); setCompanyId((current) => current || body.companies[0]?.id || ""); })
      .catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) setError(cause instanceof Error ? cause.message : "Unable to load companies."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!companyId) { setResponse(null); return; }
    const controller = new AbortController();
    setLoading(true); setError(""); setResponse(null);
    fetch(`${apiBase}/market-intelligence/${companyId}/events`, { signal: controller.signal })
      .then(async (r) => { if (!r.ok) throw new Error(`Market intelligence returned ${r.status}`); return r.json() as Promise<MarketResponse>; })
      .then(setResponse)
      .catch((cause: unknown) => { if (!(cause instanceof DOMException && cause.name === "AbortError")) setError(cause instanceof Error ? cause.message : "Unable to load market events."); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [companyId]);

  const company = companies.find((item) => item.id === companyId);
  const events = response?.events ?? [];
  return <div className="mx-auto max-w-[1400px]">
    <PageHeader eyebrow="Market Intelligence" title="Company news and market signals" description="External news with publisher provenance and deterministic links to the company’s disclosed risks." />
    <div className="panel mb-4 flex flex-wrap items-center gap-3 p-4"><label className="text-xs text-muted-foreground">Company<select value={companyId} onChange={(e) => setCompanyId(e.target.value)} className="ml-2 rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground">{companies.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><span className="text-[10px] text-muted-foreground">Source: {response?.provider ?? "GDELT"}</span></div>
    {error && <State error>{error}</State>}
    {response?.error && <State error>{response.error}</State>}
    {loading && <State>Loading real company news…</State>}
    {!loading && !error && response && events.length === 0 && <State>No external news results were returned for {company?.name ?? "this company"}. No placeholder stories are shown.</State>}
    {!loading && !error && <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]"><section className="space-y-3">{events.map((event) => <article key={event.id} className="panel p-4"><div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground"><span className="rounded border border-primary/30 bg-primary/10 px-2 py-0.5 text-primary">{event.source}</span><span>{event.category}</span><span>{event.publication_date ?? "Publication date unavailable"}</span><span className="ml-auto">Relevance {Math.round(event.relevance_score * 100)}%</span></div><h2 className="mt-2 text-sm font-semibold">{event.source_url ? <a href={event.source_url} target="_blank" rel="noreferrer" className="hover:text-primary">{event.title} <ExternalLink className="inline size-3" /></a> : event.title}</h2><p className="mt-2 text-xs leading-relaxed text-muted-foreground">{event.summary ?? "Publisher did not provide an article summary."}</p></article>)}</section><aside className="panel h-fit p-4"><h2 className="mb-3 flex items-center gap-2 text-sm font-semibold"><Newspaper className="size-4 text-primary" />Risk links</h2>{response?.related_risks.length ? response.related_risks.map((match) => { const event = events.find((item) => item.id === match.event_id); return <div key={match.event_id} className="border-t border-border/60 py-3"><p className="text-xs font-medium">{event?.title ?? "Linked event"}</p><p className="mt-1 text-[10px] text-muted-foreground">{match.change_type ?? "Risk"} · {Math.round(match.confidence_score * 100)}% term relevance</p><p className="mt-1 text-[10px] text-muted-foreground">{match.explanation}</p></div>; }) : <p className="text-xs text-muted-foreground">No Phase 2 risk record shared supported terms with these events.</p>}</aside></div>}
  </div>;
}

function State({ children, error = false }: { children: React.ReactNode; error?: boolean }) { return <div className={`rounded-xl border p-4 text-xs ${error ? "border-destructive/40 text-destructive" : "border-border text-muted-foreground"}`}>{error && <AlertCircle className="mr-2 inline size-4" />}{children}</div>; }
