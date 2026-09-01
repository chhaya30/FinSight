import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Sparkle, ArrowLeftRight } from "lucide-react";
import { GlassCard, PageHeader, ConfidenceMeter, EvidenceLink, SeverityBadge } from "@/components/ui-kit";

export const Route = createFileRoute("/evidence")({
  head: () => ({
    meta: [
      { title: "Evidence Viewer — GlobalRisk AI" },
      { name: "description", content: "Side-by-side disclosure comparison with semantic highlights, AI explanations and source citations." },
      { property: "og:title", content: "Evidence Viewer — GlobalRisk AI" },
      { property: "og:description", content: "Compare disclosures across years with semantic highlighting." },
    ],
  }),
  component: Evidence,
});

const prior = [
  { t: "We face risks associated with the transition to lower-carbon energy sources, including changes in policy and technology.", h: false },
  { t: "Our capital expenditure plans are funded through existing facilities and operating cash flow.", h: true },
  { t: "We monitor developments in climate-related regulation across our operating jurisdictions.", h: false },
];

const current = [
  { t: "We face risks associated with the transition to lower-carbon energy sources, including changes in policy, technology and financing availability.", h: false },
  { t: "Our transition plan contemplates capital expenditure materially in excess of currently committed facilities, and there can be no assurance such financing will be available on acceptable terms.", h: true },
  { t: "Failure to secure such financing could require us to defer projects or dispose of assets.", h: true },
];

function Column({ label, sub, rows, tone }: { label: string; sub: string; rows: typeof prior; tone: string }) {
  return (
    <div className="panel flex flex-col p-0">
      <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="num text-[10px] text-muted-foreground">{sub}</p>
        </div>
        <span className="num rounded-md border px-2 py-0.5 text-[10px]" style={{ color: tone, borderColor: `color-mix(in oklab, ${tone} 40%, transparent)` }}>
          source
        </span>
      </div>
      <div className="space-y-3 p-4 text-sm leading-relaxed">
        {rows.map((r, i) => (
          <motion.p
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.1 + i * 0.08 }}
            className={r.h ? "rounded-lg px-2 py-1.5" : "px-2 py-1.5 text-muted-foreground"}
            style={r.h ? { background: `color-mix(in oklab, ${tone} 14%, transparent)`, boxShadow: `inset 2px 0 0 ${tone}` } : {}}
          >
            {r.t}
          </motion.p>
        ))}
      </div>
    </div>
  );
}

function Evidence() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Evidence Viewer"
        title="Side-by-side disclosure comparison"
        description="Kaveri Energy Ltd · Climate transition risk · FY2024 vs FY2025 · semantic diff with AI explanation."
        actions={
          <span className="num flex items-center gap-2 rounded-xl border border-border bg-secondary/40 px-3 py-2 text-xs">
            <ArrowLeftRight className="size-3.5 text-primary" /> FY24 ↔ FY25
          </span>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Column label="FY2024 Annual Report" sub="Item 1A · Risk Factors · p.38" rows={prior} tone="var(--muted-foreground)" />
        <Column label="FY2025 Annual Report" sub="Item 1A · Risk Factors · p.42" rows={current} tone="var(--severity-critical)" />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <GlassCard className="lg:col-span-2" delay={0.15}>
          <div className="mb-3 flex items-center gap-2">
            <Sparkle className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">AI explanation of the change</h2>
            <span className="ml-auto"><SeverityBadge severity="critical" /></span>
          </div>
          <p className="text-sm leading-relaxed text-muted-foreground">
            The FY25 language converts a previously neutral funding statement into an explicit financing contingency.
            Three signals drive the severity uplift: (1) removal of the assurance that capex is covered by existing
            facilities, (2) introduction of “no assurance such financing will be available”, and (3) a new consequence
            sentence describing project deferral or asset disposal. Combined, these move the disclosure from
            informational to a quantifiable liquidity risk within 24 months.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <ConfidenceMeter value={0.94} />
            <EvidenceLink source="FY2024 AR p.38" />
            <EvidenceLink source="FY2025 AR p.42" />
            <EvidenceLink source="MD&A Liquidity p.51" />
          </div>
        </GlassCard>

        <GlassCard delay={0.2}>
          <h2 className="mb-3 text-sm font-semibold">Source navigation</h2>
          <div className="space-y-2">
            {[
              ["Item 1A — Risk Factors", "p.42"],
              ["MD&A — Liquidity", "p.51"],
              ["Notes — Borrowings", "p.132"],
              ["BRSR — Principle 6", "p.61"],
            ].map(([s, p]) => (
              <button key={s} className="flex w-full items-center justify-between rounded-lg border border-border/60 bg-secondary/25 px-3 py-2 text-xs transition-colors hover:border-primary/40">
                <span>{s}</span>
                <span className="num text-muted-foreground">{p}</span>
              </button>
            ))}
          </div>
          <div className="mt-4 border-t border-border/60 pt-3">
            <p className="num text-[10px] uppercase tracking-wider text-muted-foreground">Semantic highlight legend</p>
            <div className="mt-2 space-y-1.5 text-[11px]">
              {[
                ["Materially changed", "var(--severity-critical)"],
                ["Newly introduced", "var(--severity-high)"],
                ["Unchanged", "var(--muted-foreground)"],
              ].map(([l, c]) => (
                <div key={l} className="flex items-center gap-2">
                  <span className="size-2 rounded-sm" style={{ background: c }} />
                  <span className="text-muted-foreground">{l}</span>
                </div>
              ))}
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
