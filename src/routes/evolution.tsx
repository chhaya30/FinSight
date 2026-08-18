import { Fragment } from "react";
import { createFileRoute } from "@tanstack/react-router";

import { motion } from "motion/react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { Plus, Minus, TrendingUp, Flame } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter } from "@/components/ui-kit";
import { riskTrend, risks, heatmap } from "@/lib/mock-data";

export const Route = createFileRoute("/evolution")({
  head: () => ({
    meta: [
      { title: "Risk Evolution Analytics — GlobalRisk AI" },
      { name: "description", content: "Track new and removed risks, severity migration, emerging themes, timelines and category heatmaps." },
      { property: "og:title", content: "Risk Evolution Analytics — GlobalRisk AI" },
      { property: "og:description", content: "Year-over-year disclosure evolution and emerging risk themes." },
    ],
  }),
  component: Evolution,
});

function heatColor(v: number) {
  if (v >= 75) return "var(--severity-critical)";
  if (v >= 55) return "var(--severity-high)";
  if (v >= 35) return "var(--severity-medium)";
  return "var(--severity-low)";
}

function Evolution() {
  const added = risks.filter((r) => r.status === "new");
  const escalated = risks.filter((r) => r.status === "escalated");

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Risk Evolution"
        title="How disclosure risk is changing"
        description="Year-over-year additions, removals, severity migration and emerging themes across the coverage universe."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <GlassCard delay={0}>
          <div className="mb-3 flex items-center gap-2">
            <Plus className="size-4" style={{ color: "var(--severity-high)" }} />
            <h2 className="text-sm font-semibold">Newly introduced ({added.length})</h2>
          </div>
          <div className="space-y-2.5">
            {added.map((r) => (
              <div key={r.id} className="rounded-lg border border-border/60 bg-secondary/25 p-2.5">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="num text-[10px] text-muted-foreground">{r.category}</span>
                </div>
                <p className="mt-1.5 text-xs">{r.title}</p>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.05}>
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="size-4" style={{ color: "var(--severity-critical)" }} />
            <h2 className="text-sm font-semibold">Escalated ({escalated.length})</h2>
          </div>
          <div className="space-y-2.5">
            {escalated.map((r) => (
              <div key={r.id} className="rounded-lg border border-border/60 bg-secondary/25 p-2.5">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="num text-[10px] text-muted-foreground">{r.company}</span>
                </div>
                <p className="mt-1.5 text-xs">{r.title}</p>
                <p className="num mt-1 text-[10px]" style={{ color: "var(--negative)" }}>medium → {r.severity}</p>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.1}>
          <div className="mb-3 flex items-center gap-2">
            <Minus className="size-4" style={{ color: "var(--positive)" }} />
            <h2 className="text-sm font-semibold">Removed (3)</h2>
          </div>
          <div className="space-y-2.5">
            {[
              ["Pandemic operational disruption", "Atlas Industries"],
              ["LIBOR transition exposure", "Meridian Financial"],
              ["Legacy pension deficit funding", "Verdant Agri Corp"],
            ].map(([t, c]) => (
              <div key={t} className="rounded-lg border border-border/60 bg-secondary/25 p-2.5 opacity-80">
                <p className="num text-[10px] text-muted-foreground">{c}</p>
                <p className="mt-1 text-xs line-through decoration-muted-foreground/50">{t}</p>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <GlassCard delay={0.15}>
          <h2 className="mb-4 text-sm font-semibold">Composite score timeline</h2>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={riskTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 }} />
              <Line type="monotone" dataKey="score" stroke="var(--chart-1)" strokeWidth={2.4} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard delay={0.2}>
          <div className="mb-3 flex items-center gap-2">
            <Flame className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Emerging themes</h2>
          </div>
          <div className="space-y-3">
            {[
              ["AI regulation & model governance", 180, 0.91],
              ["Climate transition financing", 124, 0.94],
              ["Third-party identity security", 86, 0.88],
              ["Critical audit matters", 41, 0.79],
            ].map(([theme, growth, conf], i) => (
              <motion.div
                key={theme as string}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.06 }}
                className="rounded-xl border border-border/60 bg-secondary/25 p-3"
              >
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium">{theme as string}</p>
                  <span className="num text-[11px]" style={{ color: "var(--negative)" }}>+{growth as number}%</span>
                </div>
                <div className="mt-2">
                  <ConfidenceMeter value={conf as number} />
                </div>
              </motion.div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard className="mt-4 overflow-x-auto" delay={0.25}>
        <h2 className="mb-4 text-sm font-semibold">Category × issuer heatmap</h2>
        <div className="min-w-[720px]">
          <div className="grid grid-cols-[180px_repeat(6,1fr)] gap-1.5">
            <div />
            {heatmap[0]!.values.map((v) => (
              <div key={v.company} className="num pb-1 text-center text-[10px] text-muted-foreground">{v.company}</div>
            ))}
            {heatmap.map((row) => (
              <Fragment key={row.category}>
                <div className="flex items-center pr-2 text-[11px] text-muted-foreground">{row.category}</div>
                {row.values.map((v) => (
                  <motion.div
                    key={row.category + v.company}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    title={`${row.category} · ${v.company} · ${v.value}`}
                    className="num grid h-9 place-items-center rounded-md text-[10px] font-medium transition-transform hover:scale-105"
                    style={{
                      background: `color-mix(in oklab, ${heatColor(v.value)} ${20 + v.value * 0.55}%, transparent)`,
                      color: v.value > 60 ? "var(--background)" : "var(--foreground)",
                    }}
                  >
                    {v.value}
                  </motion.div>
                ))}
              </Fragment>
            ))}

          </div>
        </div>
      </GlassCard>
    </div>
  );
}
