import { useEffect, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { BrainCircuit, Tag, Users, Quote } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter, EvidenceLink } from "@/components/ui-kit";
import { api } from "@/lib/api";

type Risk = {
  id: string;
  report_id: string;
  category: string;
  severity: string;
  confidence_score: number;
  summary: string;
  source_page: number | null;
  source_paragraph: string | null;
  source_text_hash: string | null;
  entities: Array<{ entity_type: string; text: string; start_char: number | null; end_char: number | null; confidence: number | null }>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export const Route = createFileRoute("/engine")({
  head: () => ({
    meta: [
      { title: "Corporate Risk Intelligence Engine — GlobalRisk AI" },
      { name: "description", content: "AI risk extraction with categorisation, named entities, topics, severity and explainable summaries." },
      { property: "og:title", content: "Corporate Risk Intelligence Engine — GlobalRisk AI" },
      { property: "og:description", content: "Explainable AI risk extraction from corporate disclosures." },
    ],
  }),
  component: Engine,
});

function Engine() {
  const [category, setCategory] = useState<string>("All");
  const [selected, setSelected] = useState<string | null>(null);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.risks.list({ page_size: 50 })
      .then((data: { risks: Risk[] }) => {
        setRisks(data.risks);
        if (data.risks.length > 0) {
          setSelected(data.risks[0].id);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const categories = [...new Set(risks.map((r) => r.category))].sort();
  const list = category === "All" ? risks : risks.filter((r) => r.category === category);
  const active = risks.find((r) => r.id === selected) ?? list[0];

  if (loading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Risk Engine"
          title="Loading..."
          description="Loading risk data..."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Risk Engine"
        title="Corporate risk intelligence engine"
        description="Every extracted disclosure is categorised, scored for severity and confidence, and linked back to its source paragraph."
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {["All", ...categories].map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={`num rounded-full border px-3 py-1.5 text-[11px] transition-colors ${
              category === c
                ? "border-primary/50 bg-primary/15 text-primary"
                : "border-border bg-secondary/30 text-muted-foreground hover:border-primary/30"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr]">
        <div className="space-y-3">
          {list.map((r, i) => (
            <motion.button
              key={r.id}
              onClick={() => setSelected(r.id)}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={`panel w-full p-4 text-left transition-colors ${
                active?.id === r.id ? "border-primary/50" : "hover:border-primary/30"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={r.severity.toLowerCase() as any} />
                <span className="num text-[10px] text-muted-foreground">{r.id}</span>
                <span className="num ml-auto rounded-md border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {r.category}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium">{r.summary.slice(0, 80)}...</p>
              <p className="mt-1 text-xs text-muted-foreground">{r.report_id} · confidence: {(r.confidence_score * 100).toFixed(0)}%</p>
              <div className="mt-2.5">
                <ConfidenceMeter value={r.confidence_score} />
              </div>
            </motion.button>
          ))}
          {list.length === 0 && (
            <div className="text-xs text-muted-foreground text-center py-4">No risks found for this category</div>
          )}
        </div>

        <div className="lg:sticky lg:top-20 lg:h-fit">
          <AnimatePresence mode="wait">
            {active && (
              <motion.div
                key={active.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25 }}
                className="panel p-5"
              >
                <div className="flex items-center gap-2">
                  <BrainCircuit className="size-4 text-primary" />
                  <p className="num text-[11px] uppercase tracking-wider text-primary">Explainable analysis</p>
                  <span className="num ml-auto text-[10px] text-muted-foreground">{active.id}</span>
                </div>
                <h2 className="mt-3 text-lg font-semibold">{active.summary.slice(0, 100)}...</h2>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <SeverityBadge severity={active.severity.toLowerCase() as any} />
                  <span className="text-xs text-muted-foreground">{active.category} · confidence: {(active.confidence_score * 100).toFixed(0)}%</span>
                </div>

                <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{active.summary}</p>

                {active.source_paragraph && (
                  <div className="mt-4 rounded-xl border-l-2 border-primary bg-primary/5 p-3">
                    <Quote className="mb-1 size-3.5 text-primary" />
                    <p className="text-sm italic leading-relaxed">"{active.source_paragraph.slice(0, 200)}..."</p>
                    <div className="mt-2">
                      <EvidenceLink source={`Page ${active.source_page ?? "—"} · ${active.report_id}`} />
                    </div>
                  </div>
                )}

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="num mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                      <Users className="size-3" /> Named entities
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {active.entities.map((e, i) => (
                        <span key={i} className="num rounded-md bg-secondary px-2 py-1 text-[10px]">{e.text}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="num mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                      <Tag className="size-3" /> Metadata
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(active.metadata || {}).map(([k, v]) => (
                        <span key={k} className="num rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] text-primary">
                          {k}: {String(v)}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-5 border-t border-border/60 pt-4">
                  <ConfidenceMeter value={active.confidence_score} label="model confidence" />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
