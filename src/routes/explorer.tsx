import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { Search, SlidersHorizontal } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter, EvidenceLink } from "@/components/ui-kit";
import { risks, riskCategories, companies, type Severity } from "@/lib/mock-data";

export const Route = createFileRoute("/explorer")({
  head: () => ({
    meta: [
      { title: "Risk Explorer — GlobalRisk AI" },
      { name: "description", content: "Semantic search and filtering across governance, cyber, ESG, climate, regulatory and litigation risk." },
      { property: "og:title", content: "Risk Explorer — GlobalRisk AI" },
      { property: "og:description", content: "Semantic exploration of extracted corporate risk disclosures." },
    ],
  }),
  component: Explorer,
});

const severities: Severity[] = ["critical", "high", "medium", "low"];

function Explorer() {
  const [q, setQ] = useState("");
  const [cats, setCats] = useState<string[]>([]);
  const [sevs, setSevs] = useState<string[]>([]);
  const [company, setCompany] = useState("All");

  const toggle = (arr: string[], v: string, set: (x: string[]) => void) =>
    set(arr.includes(v) ? arr.filter((a) => a !== v) : [...arr, v]);

  const results = risks.filter(
    (r) =>
      (!q || `${r.title} ${r.summary} ${r.topics.join(" ")}`.toLowerCase().includes(q.toLowerCase())) &&
      (cats.length === 0 || cats.includes(r.category)) &&
      (sevs.length === 0 || sevs.includes(r.severity)) &&
      (company === "All" || r.company === company),
  );

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Risk Explorer"
        title="Semantic risk exploration"
        description="Query the extracted disclosure graph by meaning, then narrow with category, severity and issuer filters."
      />

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="space-y-4 lg:sticky lg:top-20 lg:h-fit">
          <GlassCard delay={0}>
            <div className="mb-3 flex items-center gap-2">
              <SlidersHorizontal className="size-4 text-primary" />
              <h2 className="text-sm font-semibold">Filters</h2>
            </div>

            <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Issuer</p>
            <select
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="mb-4 w-full rounded-lg border border-border bg-secondary/40 px-2.5 py-2 text-xs outline-none"
            >
              <option>All</option>
              {companies.map((c) => (
                <option key={c.id}>{c.name}</option>
              ))}
            </select>

            <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Severity</p>
            <div className="mb-4 flex flex-wrap gap-1.5">
              {severities.map((s) => (
                <button
                  key={s}
                  onClick={() => toggle(sevs, s, setSevs)}
                  className={`num rounded-full border px-2.5 py-1 text-[10px] uppercase transition-colors ${
                    sevs.includes(s) ? "border-primary/50 bg-primary/15 text-primary" : "border-border text-muted-foreground"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Category</p>
            <div className="flex flex-wrap gap-1.5">
              {riskCategories.map((c) => (
                <button
                  key={c}
                  onClick={() => toggle(cats, c, setCats)}
                  className={`rounded-lg border px-2 py-1 text-[10px] transition-colors ${
                    cats.includes(c) ? "border-primary/50 bg-primary/15 text-primary" : "border-border text-muted-foreground hover:border-primary/30"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </GlassCard>
        </div>

        <div>
          <div className="panel mb-4 flex items-center gap-2 px-4 py-3">
            <Search className="size-4 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. financing availability for decarbonisation capex"
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <span className="num text-xs text-muted-foreground">{results.length}</span>
          </div>

          <div className="space-y-3">
            {results.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="panel p-4 transition-colors hover:border-primary/40"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={r.severity} />
                  <span className="num rounded-md border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">{r.category}</span>
                  <span className="text-xs text-muted-foreground">{r.company} · FY{r.year}</span>
                </div>
                <p className="mt-2 text-sm font-medium">{r.title}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{r.summary}</p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                  <ConfidenceMeter value={r.confidence} />
                  <EvidenceLink source={r.source} />
                </div>
              </motion.div>
            ))}
            {results.length === 0 && (
              <div className="panel p-10 text-center text-sm text-muted-foreground">No disclosures match these filters.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
