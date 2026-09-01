import { createFileRoute } from "@tanstack/react-router";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Sparkle } from "lucide-react";
import { GlassCard, PageHeader, StatCard, ConfidenceMeter, EvidenceLink, Sparkline } from "@/components/ui-kit";
import { financials } from "@/lib/mock-data";

export const Route = createFileRoute("/financials")({
  head: () => ({
    meta: [
      { title: "Financial Health Intelligence — GlobalRisk AI" },
      { name: "description", content: "KPI trends, leverage, cash conversion and AI insights correlating financials with disclosure risk." },
      { property: "og:title", content: "Financial Health Intelligence — GlobalRisk AI" },
      { property: "og:description", content: "Financial KPIs correlated with disclosure risk signals." },
    ],
  }),
  component: Financials,
});

const tip = {
  contentStyle: { background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 12, fontSize: 12 },
};

function Financials() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Financial Health"
        title="Financial health intelligence"
        description="Atlas Industries · quarterly fundamentals correlated against extracted disclosure risk."
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Revenue (Q2-25)" value="$1.47B" delta={6.0} hint="QoQ" />
        <StatCard label="EBITDA margin" value="21.3%" delta={-0.8} hint="vs Q1-25" delay={0.05} />
        <StatCard label="Free cash flow" value="$82M" delta={28.1} hint="QoQ" delay={0.1} />
        <StatCard label="Net leverage" value="3.3x" delta={6.5} hint="covenant 3.75x" delay={0.15} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2" delay={0.1}>
          <h2 className="mb-4 text-sm font-semibold">Revenue, EBITDA and leverage</h2>
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={financials}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="period" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="l" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <Tooltip {...tip} />
              <Bar yAxisId="l" dataKey="revenue" fill="var(--chart-1)" radius={[6, 6, 0, 0]} opacity={0.85} />
              <Bar yAxisId="l" dataKey="ebitda" fill="var(--chart-2)" radius={[6, 6, 0, 0]} opacity={0.85} />
              <Line yAxisId="r" type="monotone" dataKey="leverage" stroke="var(--severity-critical)" strokeWidth={2.4} dot={{ r: 3 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="mb-3 flex items-center gap-2">
            <Sparkle className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">AI financial insight</h2>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Revenue growth of 6% QoQ is outpaced by a 38bps margin contraction and rising leverage. The pattern maps
            directly to the FY25 covenant-headroom disclosure: growth is being funded on the revolver rather than
            operating cash, compressing flexibility ahead of the FY26 refinancing window.
          </p>
          <div className="mt-4 space-y-3">
            <ConfidenceMeter value={0.9} />
            <div className="flex flex-wrap gap-1.5">
              <EvidenceLink source="FY25 MD&A p.24" />
              <EvidenceLink source="Notes — Borrowings p.118" />
            </div>
          </div>
        </GlassCard>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <GlassCard delay={0.2}>
          <h2 className="mb-3 text-sm font-semibold">Free cash flow trend</h2>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={financials}>
              <defs>
                <linearGradient id="fcf" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-5)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--chart-5)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="period" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <Tooltip {...tip} />
              <Area type="monotone" dataKey="fcf" stroke="var(--chart-5)" fill="url(#fcf)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard delay={0.25}>
          <h2 className="mb-3 text-sm font-semibold">Risk correlation matrix</h2>
          <div className="space-y-2.5">
            {[
              ["Leverage ↔ Financial Stability risk", 0.87],
              ["Margin ↔ Supply Chain risk", 0.64],
              ["Capex ↔ Climate risk", 0.71],
              ["Legal provisions ↔ Litigation risk", 0.92],
            ].map(([label, v]) => (
              <div key={label as string}>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{label as string}</span>
                  <span className="num">{(v as number).toFixed(2)}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{ width: `${(v as number) * 100}%`, background: "var(--gradient-primary)" }} />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.3}>
          <h2 className="mb-3 text-sm font-semibold">Key ratios</h2>
          <div className="space-y-3">
            {[
              ["Current ratio", "1.34", [1.5, 1.44, 1.4, 1.38, 1.36, 1.34]],
              ["Interest cover", "4.1x", [5.6, 5.2, 4.9, 4.5, 4.3, 4.1]],
              ["ROIC", "11.8%", [10.2, 10.9, 11.1, 11.4, 11.6, 11.8]],
            ].map(([k, v, pts]) => (
              <div key={k as string} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{k as string}</span>
                  <span className="num text-sm font-semibold">{v as string}</span>
                </div>
                <Sparkline points={pts as number[]} />
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
