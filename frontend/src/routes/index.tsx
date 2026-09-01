import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
  BarChart,
} from "recharts";
import { motion } from "motion/react";
import { ArrowUpRight, Sparkle } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter, StatCard, EvidenceLink } from "@/components/ui-kit";
import { companies, risks, riskTrend, news } from "@/lib/mock-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Executive Dashboard — GlobalRisk AI" },
      { name: "description", content: "Portfolio-wide risk posture, emerging themes and AI insights linked to source evidence." },
      { property: "og:title", content: "Executive Dashboard — GlobalRisk AI" },
      { property: "og:description", content: "Portfolio-wide risk posture and AI insights with citations." },
    ],
  }),
  component: Dashboard,
});

const chartStyle = {
  contentStyle: {
    background: "var(--popover)",
    border: "1px solid var(--border)",
    borderRadius: 12,
    fontSize: 12,
  },
};

function Dashboard() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Executive Dashboard"
        title="Portfolio risk posture"
        description="Aggregated intelligence across 6 covered issuers, 1,284 filings and 18,402 extracted disclosures."
        actions={
          <>
            <Link to="/reports" className="num rounded-xl border border-border bg-secondary/50 px-3 py-2 text-xs hover:border-primary/40">
              Generate brief
            </Link>
            <Link
              to="/explorer"
              className="num rounded-xl px-3 py-2 text-xs font-medium"
              style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}
            >
              Explore risks
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Composite risk index" value="71.4" delta={5.2} hint="vs prior year" delay={0} />
        <StatCard label="Critical disclosures" value="11" delta={37.5} hint="6 newly introduced" delay={0.05} />
        <StatCard label="Filings processed" value="1,284" delta={-2.1} hint="last 30 days" delay={0.1} />
        <StatCard label="Avg. model confidence" value="88%" hint="evidence-linked" delay={0.15} />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <GlassCard className="xl:col-span-2" delay={0.1}>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold">Risk severity distribution</h2>
              <p className="text-xs text-muted-foreground">Six-year disclosure trend across coverage universe</p>
            </div>
            <span className="num rounded-md border border-border px-2 py-1 text-[10px] text-muted-foreground">FY20–FY25</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={riskTrend}>
              <defs>
                {["critical", "high", "medium"].map((k, i) => (
                  <linearGradient key={k} id={`g-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={`var(--chart-${i + 4 > 5 ? 1 : i + 4})`} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={`var(--chart-${i + 4 > 5 ? 1 : i + 4})`} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="year" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <Tooltip {...chartStyle} />
              <Area type="monotone" dataKey="critical" stroke="var(--severity-critical)" fill="url(#g-critical)" strokeWidth={2} />
              <Area type="monotone" dataKey="high" stroke="var(--severity-high)" fill="url(#g-high)" strokeWidth={2} />
              <Area type="monotone" dataKey="medium" stroke="var(--severity-medium)" fill="url(#g-medium)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard delay={0.15}>
          <div className="mb-4 flex items-center gap-2">
            <Sparkle className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">AI executive insight</h2>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Disclosure severity has shifted decisively upward in FY25, driven by two vectors: climate transition
            financing (Energy) and AI regulatory classification (Technology). Litigation contingencies remain the
            single largest unquantified exposure in the universe.
          </p>
          <div className="mt-4 space-y-3">
            <ConfidenceMeter value={0.92} />
            <div className="flex flex-wrap gap-1.5">
              <EvidenceLink source="Kaveri FY25 p.42" />
              <EvidenceLink source="Nimbus 10-K p.34" />
              <EvidenceLink source="Solstice 20-F p.63" />
            </div>
          </div>
          <div className="mt-5 space-y-2 border-t border-border/60 pt-4">
            {[
              ["Emerging theme", "AI Regulation +180%"],
              ["Fastest escalation", "Kaveri Energy +11 pts"],
              ["Most improved", "Solstice Pharma −7 pts"],
            ].map(([k, v]) => (
              <div key={k} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{k}</span>
                <span className="num font-medium">{v}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <GlassCard className="xl:col-span-2" delay={0.2}>
          <h2 className="mb-4 text-sm font-semibold">Priority risk queue</h2>
          <div className="space-y-3">
            {risks.slice(0, 5).map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 + i * 0.05 }}
                className="rounded-xl border border-border/60 bg-secondary/25 p-3 transition-colors hover:border-primary/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="num text-[11px] text-muted-foreground">{r.id}</span>
                  <span className="text-xs text-muted-foreground">· {r.company}</span>
                  <span className="num ml-auto rounded-md border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {r.category}
                  </span>
                </div>
                <p className="mt-2 text-sm font-medium">{r.title}</p>
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <ConfidenceMeter value={r.confidence} />
                  <EvidenceLink source={r.source} />
                </div>
              </motion.div>
            ))}
          </div>
        </GlassCard>

        <div className="space-y-4">
          <GlassCard delay={0.25}>
            <h2 className="mb-3 text-sm font-semibold">Coverage universe</h2>
            <div className="space-y-2">
              {companies.map((c) => (
                <div key={c.id} className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-secondary/40">
                  <span className="num grid size-7 place-items-center rounded-md bg-secondary text-[10px]">{c.ticker.slice(0, 2)}</span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">{c.name}</p>
                    <p className="num text-[10px] text-muted-foreground">{c.market} · {c.sector}</p>
                  </div>
                  <span className="num text-sm font-semibold">{c.score}</span>
                  <span className="num text-[10px]" style={{ color: c.delta >= 0 ? "var(--negative)" : "var(--positive)" }}>
                    {c.delta >= 0 ? "+" : ""}{c.delta}
                  </span>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard delay={0.3}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Live market signals</h2>
              <Link to="/market" className="text-primary"><ArrowUpRight className="size-4" /></Link>
            </div>
            <div className="space-y-2.5">
              {news.slice(0, 4).map((n) => (
                <div key={n.id} className="text-xs">
                  <div className="num flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="text-primary">{n.source}</span>
                    <span>{n.time} ago</span>
                    <span style={{ color: n.sentiment >= 0 ? "var(--positive)" : "var(--negative)" }}>
                      {n.sentiment >= 0 ? "+" : ""}{n.sentiment.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-0.5 leading-snug">{n.title}</p>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      </div>

      <GlassCard className="mt-4" delay={0.35}>
        <h2 className="mb-4 text-sm font-semibold">Composite risk score by issuer</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={companies}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="ticker" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
            <Tooltip {...chartStyle} cursor={{ fill: "var(--muted)", opacity: 0.3 }} />
            <Bar dataKey="score" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </GlassCard>
    </div>
  );
}
