import { createFileRoute } from "@tanstack/react-router";
import { Star, StickyNote, Bookmark } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge } from "@/components/ui-kit";
import { companies, risks } from "@/lib/mock-data";

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
                <span className="num text-[10px] text-primary">{c.ticker}</span>
                <span className="truncate text-xs">{c.name}</span>
                <span className="num ml-auto text-xs font-semibold">{c.score}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.05}>
          <div className="mb-3 flex items-center gap-2">
            <Bookmark className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Saved reports</h2>
          </div>
          <div className="space-y-2">
            {[
              ["Kaveri FY25 Risk Briefing", "2 days ago"],
              ["Sector: Energy transition scan", "5 days ago"],
              ["Nimbus cyber deep-dive", "1 week ago"],
            ].map(([t, when]) => (
              <div key={t} className="rounded-lg border border-border/60 bg-secondary/25 px-3 py-2">
                <p className="text-xs font-medium">{t}</p>
                <p className="num text-[10px] text-muted-foreground">{when}</p>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="mb-3 flex items-center gap-2">
            <StickyNote className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Notes</h2>
          </div>
          <textarea
            defaultValue="Follow up on Kaveri covenant headroom vs FY26 refinancing calendar. Cross-check with Atlas leverage trend."
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
                <SeverityBadge severity={r.severity} />
                <span className="num text-[10px] text-muted-foreground">{r.company}</span>
              </div>
              <p className="mt-1.5 text-xs">{r.title}</p>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
