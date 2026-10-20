import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Star, StickyNote, Bookmark } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge } from "@/components/ui-kit";
import { api } from "@/lib/api";

type Company = {
  id: string;
  name: string;
  ticker_symbol: string | null;
  sector: string | null;
  listed_exchange: string | null;
  country: string | null;
  market_cap: number | null;
  currency: string | null;
  created_at: string;
  updated_at: string;
};

type Risk = {
  id: string;
  report_id: string;
  category: string;
  severity: string;
  confidence_score: number;
  summary: string;
  source_page: number | null;
  source_paragraph: string | null;
  source_text_hash: string | null;
  entities: Array<{ entity_type: string; text: string; start_char: number | null; end_char: number | null; confidence: number | null }>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export const Route = createFileRoute("/workspace")({
  head: () => ({
    meta: [
      { title: "Analyst Workspace — GlobalRisk AI" },
      { name: "description", content: "Watchlists, saved reports, research notes and favourite disclosures in one workspace." },
      { property: "og:title", content: "Analyst Workspace — GlobalRisk AI" },
      { property: "og:description", content: "Watchlists, saved reports and analyst notes." },
    ],
  }),
  component: Workspace,
});

function Workspace() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.companies.list({ page_size: 100 })
      .then((data: { companies: Company[] }) => {
        setCompanies(data.companies);
      })
      .catch(console.error);
    api.risks.list({ page_size: 20 })
      .then((data: { risks: Risk[] }) => {
        setRisks(data.risks);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Workspace"
          title="Loading..."
          description="Loading workspace data..."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Workspace"
        title="Analyst workspace"
        description="Your watchlists, saved briefings, favourites and research notes — shared with your team workspace."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard delay={0}>
          <div className="mb-3 flex items-center gap-2">
            <Star className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Watchlist</h2>
          </div>
          <div className="space-y-2">
            {companies.slice(0, 4).map((c) => (
              <div key={c.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2">
                <span className="num text-[10px] text-primary">{c.ticker_symbol ?? c.id.slice(0, 4)}</span>
                <span className="truncate text-xs">{c.name}</span>
                <span className="num ml-auto text-xs font-semibold">—</span>
              </div>
            ))}
            {companies.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">No companies available</div>
            )}
          </div>
        </GlassCard>

        <GlassCard delay={0.05}>
          <div className="mb-3 flex items-center gap-2">
            <Bookmark className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Saved reports</h2>
          </div>
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground text-center py-4">No saved reports yet</p>
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="mb-3 flex items-center gap-2">
            <StickyNote className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Notes</h2>
          </div>
          <textarea
            defaultValue="Follow up on covenant headroom vs FY26 refinancing calendar. Cross-check with leverage trend."
            className="h-32 w-full resize-none rounded-xl border border-border bg-secondary/25 p-3 text-xs outline-none"
          />
        </GlassCard>
      </div>

      <GlassCard className="mt-4" delay={0.15}>
        <h2 className="mb-3 text-sm font-semibold">Favourite disclosures</h2>
        <div className="grid gap-2.5 md:grid-cols-2">
          {risks.slice(0, 4).map((r) => (
            <div key={r.id} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
              <div className="flex items-center gap-2">
                <SeverityBadge severity={r.severity.toLowerCase() as any} />
                <span className="num text-[10px] text-muted-foreground">{r.category}</span>
              </div>
              <p className="mt-1.5 text-xs">{r.summary.slice(0, 80)}...</p>
            </div>
          ))}
          {risks.length === 0 && (
            <div className="text-xs text-muted-foreground text-center py-4">No risks available</div>
          )}
        </div>
      </GlassCard>
    </div>
  );
}
