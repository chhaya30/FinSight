import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Bell, Newspaper, FileCheck2 } from "lucide-react";
import { GlassCard, PageHeader, ConfidenceMeter } from "@/components/ui-kit";
import { news } from "@/lib/mock-data";

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
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Market Intelligence"
        title="Live market and regulatory signals"
        description="Streaming coverage from newswires, SEC EDGAR and SEBI filings with sentiment scoring against your watchlist."
      />

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <GlassCard className="p-0" delay={0}>
          <div className="flex items-center gap-2 border-b border-border/60 px-4 py-3">
            <Newspaper className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Signal feed</h2>
            <span className="num ml-auto flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <span className="size-1.5 animate-pulse rounded-full bg-primary" /> live
            </span>
          </div>
          <div className="divide-y divide-border/40">
            {news.map((n, i) => (
              <motion.article
                key={n.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="p-4 transition-colors hover:bg-secondary/25"
              >
                <div className="num flex flex-wrap items-center gap-2 text-[10px]">
                  <span className="rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-primary">{n.source}</span>
                  <span className="text-muted-foreground">{n.time} ago</span>
                  {n.tags.map((t) => (
                    <span key={t} className="rounded-md bg-secondary px-1.5 py-0.5 text-muted-foreground">{t}</span>
                  ))}
                  <span
                    className="ml-auto rounded-md px-1.5 py-0.5"
                    style={{
                      color: n.sentiment >= 0 ? "var(--positive)" : "var(--negative)",
                      background: `color-mix(in oklab, ${n.sentiment >= 0 ? "var(--positive)" : "var(--negative)"} 12%, transparent)`,
                    }}
                  >
                    sentiment {n.sentiment >= 0 ? "+" : ""}{n.sentiment.toFixed(2)}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium leading-snug">{n.title}</p>
              </motion.article>
            ))}
          </div>
        </GlassCard>

        <div className="space-y-4">
          <GlassCard delay={0.1}>
            <div className="mb-3 flex items-center gap-2">
              <FileCheck2 className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">Regulatory filings</h2>
            </div>
            <div className="space-y-2">
              {[
                ["SEC", "8-K", "Nimbus Cloud Systems", "Today"],
                ["SEBI", "Reg 30", "Kaveri Energy Ltd", "Today"],
                ["SEC", "10-Q", "Meridian Financial", "2d"],
                ["SEBI", "BRSR Core", "Verdant Agri Corp", "4d"],
              ].map(([reg, form, co, when]) => (
                <div key={`${co}-${form}`} className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2">
                  <span className="num rounded-md bg-secondary px-1.5 py-0.5 text-[10px]">{reg}</span>
                  <span className="num text-[11px] text-primary">{form}</span>
                  <span className="truncate text-xs">{co}</span>
                  <span className="num ml-auto text-[10px] text-muted-foreground">{when}</span>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.15}>
            <div className="mb-3 flex items-center gap-2">
              <Bell className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">Active alerts</h2>
            </div>
            <div className="space-y-2.5">
              {[
                ["Severity uplift on watchlist name", "Kaveri Energy Ltd", 0.94],
                ["Negative sentiment cluster (3+ sources)", "Solstice Pharma", 0.87],
                ["New AI regulation disclosure detected", "Nimbus Cloud Systems", 0.9],
              ].map(([t, c, conf]) => (
                <div key={t as string} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
                  <p className="text-xs font-medium">{t as string}</p>
                  <p className="num mt-0.5 text-[10px] text-muted-foreground">{c as string}</p>
                  <div className="mt-2"><ConfidenceMeter value={conf as number} /></div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
