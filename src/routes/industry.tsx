import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { GlassCard, PageHeader, ConfidenceMeter } from "@/components/ui-kit";
import { companies, heatmap } from "@/lib/mock-data";

export const Route = createFileRoute("/industry")({
  head: () => ({
    meta: [
      { title: "Industry Intelligence — GlobalRisk AI" },
      { name: "description", content: "Peer comparison, sector rankings and category heatmaps across the coverage universe." },
      { property: "og:title", content: "Industry Intelligence — GlobalRisk AI" },
      { property: "og:description", content: "Peer benchmarking and sector risk heatmaps." },
    ],
  }),
  component: Industry,
});

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
