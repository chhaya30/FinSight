import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { ScanSearch, Plus, X, Zap } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter } from "@/components/ui-kit";
import { risks, riskCategories } from "@/lib/mock-data";

export const Route = createFileRoute("/scanner")({
  head: () => ({
    meta: [
      { title: "Multi-Factor Risk Scanner — GlobalRisk AI" },
      { name: "description", content: "Build AND/OR screening logic across risk categories, severities and financial thresholds." },
      { property: "og:title", content: "Multi-Factor Risk Scanner — GlobalRisk AI" },
      { property: "og:description", content: "Custom AND/OR screening across the disclosure universe." },
    ],
  }),
  component: Scanner,
});

type Clause = { id: number; field: string; op: string; value: string };

function Scanner() {
  const [logic, setLogic] = useState<"AND" | "OR">("AND");
  const [clauses, setClauses] = useState<Clause[]>([
    { id: 1, field: "Category", op: "is", value: "Climate" },
    { id: 2, field: "Severity", op: "is at least", value: "high" },
  ]);
  const [ran, setRan] = useState(true);

  const add = () =>
    setClauses((c) => [...c, { id: Date.now(), field: "Category", op: "is", value: riskCategories[0]! }]);

  const rank = { low: 1, medium: 2, high: 3, critical: 4 } as const;
  const matches = risks.filter((r) => {
    const tests = clauses.map((c) => {
      if (c.field === "Category") return r.category === c.value;
      if (c.field === "Severity") return rank[r.severity] >= (rank[c.value as keyof typeof rank] ?? 0);
      if (c.field === "Status") return r.status === c.value;
      return true;
    });
    return logic === "AND" ? tests.every(Boolean) : tests.some(Boolean);
  });

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Scanner"
        title="Multi-factor risk scanner"
        description="Compose boolean screens across categories, severities and disclosure status to isolate exposures."
      />

      <GlassCard delay={0}>
        <div className="mb-4 flex items-center gap-2">
          <ScanSearch className="size-4 text-primary" />
          <h2 className="text-sm font-semibold">Screen definition</h2>
          <div className="num ml-auto flex overflow-hidden rounded-lg border border-border text-[10px]">
            {(["AND", "OR"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLogic(l)}
                className={`px-3 py-1.5 transition-colors ${logic === l ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          {clauses.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex flex-wrap items-center gap-2 rounded-xl border border-border/60 bg-secondary/25 p-2.5"
            >
              <span className="num w-10 text-[10px] text-primary">{i === 0 ? "WHERE" : logic}</span>
              <select
                value={c.field}
                onChange={(e) => setClauses((cs) => cs.map((x) => (x.id === c.id ? { ...x, field: e.target.value } : x)))}
                className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs outline-none"
              >
                {["Category", "Severity", "Status"].map((f) => <option key={f}>{f}</option>)}
              </select>
              <span className="num text-[11px] text-muted-foreground">{c.field === "Severity" ? "is at least" : "is"}</span>
              <select
                value={c.value}
                onChange={(e) => setClauses((cs) => cs.map((x) => (x.id === c.id ? { ...x, value: e.target.value } : x)))}
                className="rounded-lg border border-border bg-background/60 px-2 py-1.5 text-xs outline-none"
              >
                {(c.field === "Category" ? riskCategories : c.field === "Severity" ? ["low", "medium", "high", "critical"] : ["new", "escalated", "persistent", "removed"]).map(
                  (v) => <option key={v}>{v}</option>,
                )}
              </select>
              <button
                onClick={() => setClauses((cs) => cs.filter((x) => x.id !== c.id))}
                className="ml-auto rounded-md p-1 text-muted-foreground hover:bg-secondary"
              >
                <X className="size-3.5" />
              </button>
            </motion.div>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button onClick={add} className="num flex items-center gap-1.5 rounded-xl border border-border bg-secondary/40 px-3 py-2 text-xs hover:border-primary/40">
            <Plus className="size-3.5" /> Add condition
          </button>
          <button
            onClick={() => setRan(true)}
            className="num flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-medium"
            style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}
          >
            <Zap className="size-3.5" /> Run scan
          </button>
        </div>
      </GlassCard>

      {ran && (
        <GlassCard className="mt-4" delay={0.1}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Scan results</h2>
            <span className="num text-xs text-muted-foreground">{matches.length} of {risks.length} disclosures</span>
          </div>
          <div className="space-y-2.5">
            {matches.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-xl border border-border/60 bg-secondary/25 p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="num text-[10px] text-muted-foreground">{r.category} · {r.status}</span>
                  <span className="text-xs text-muted-foreground">{r.company}</span>
                </div>
                <p className="mt-1.5 text-sm">{r.title}</p>
                <div className="mt-2"><ConfidenceMeter value={r.confidence} /></div>
              </motion.div>
            ))}
            {matches.length === 0 && <p className="py-8 text-center text-sm text-muted-foreground">No disclosures satisfy this screen.</p>}
          </div>
        </GlassCard>
      )}
    </div>
  );
}
