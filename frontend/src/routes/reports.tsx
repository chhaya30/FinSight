import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { FileDown, Check } from "lucide-react";
import { GlassCard, PageHeader } from "@/components/ui-kit";
import { companies } from "@/lib/mock-data";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Executive Report Generator — GlobalRisk AI" },
      { name: "description", content: "Compose and export board-ready PDF risk briefings with evidence-linked AI insights." },
      { property: "og:title", content: "Executive Report Generator — GlobalRisk AI" },
      { property: "og:description", content: "Generate downloadable executive risk reports." },
    ],
  }),
  component: Reports,
});

const sections = [
  "Executive summary",
  "Composite risk score & drivers",
  "New and escalated disclosures",
  "Evidence appendix with citations",
  "Financial health correlation",
  "Peer benchmarking",
  "Market & regulatory signals",
];

function Reports() {
  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Reports"
        title="Executive report generator"
        description="Assemble a board-ready briefing. Every insight carries its source citation and confidence score."
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_1.1fr]">
        <GlassCard delay={0}>
          <h2 className="mb-3 text-sm font-semibold">Configuration</h2>
          <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Issuer</p>
          <select className="mb-4 w-full rounded-lg border border-border bg-secondary/40 px-2.5 py-2 text-xs outline-none">
            {companies.map((c) => <option key={c.id}>{c.name}</option>)}
          </select>
          <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Sections</p>
          <div className="space-y-1.5">
            {sections.map((s, i) => (
              <label key={s} className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2 text-xs">
                <span className="grid size-4 place-items-center rounded-[5px]" style={{ background: i < 5 ? "var(--gradient-primary)" : "var(--muted)" }}>
                  {i < 5 && <Check className="size-3 text-primary-foreground" />}
                </span>
                {s}
              </label>
            ))}
          </div>
          <button
            className="num mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-xs font-medium"
            style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)", boxShadow: "var(--shadow-glow)" }}
          >
            <FileDown className="size-4" /> Generate PDF report
          </button>
        </GlassCard>

        <GlassCard delay={0.1}>
          <h2 className="mb-3 text-sm font-semibold">Preview</h2>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-card p-6 shadow-inner"
          >
            <p className="num text-[10px] uppercase tracking-[0.2em] text-primary">GlobalRisk AI · Confidential</p>
            <h3 className="mt-2 text-lg font-semibold">Kaveri Energy Ltd — FY2025 Risk Briefing</h3>
            <p className="num mt-1 text-[10px] text-muted-foreground">Generated 04 Aug 2026 · 14 pages · 42 citations</p>
            <div className="mt-4 space-y-2 text-xs leading-relaxed text-muted-foreground">
              <p>
                Composite risk score rose 11 points to 85, the largest increase in the coverage universe, driven by a
                newly disclosed financing contingency around decarbonisation capital expenditure.
              </p>
              <p>
                Two disclosures escalated to critical severity; community relations matters remain stable at low
                severity with unchanged language versus FY2024.
              </p>
            </div>
            <div className="mt-4 space-y-1.5">
              {sections.slice(0, 5).map((s, i) => (
                <div key={s} className="num flex items-center justify-between border-b border-border/40 pb-1 text-[10px] text-muted-foreground">
                  <span>{i + 1}. {s}</span>
                  <span>p.{(i + 1) * 2}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </GlassCard>
      </div>
    </div>
  );
}
