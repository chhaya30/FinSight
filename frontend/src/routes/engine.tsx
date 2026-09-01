import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion, AnimatePresence } from "motion/react";
import { BrainCircuit, Tag, Users, Quote } from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter, EvidenceLink } from "@/components/ui-kit";
import { risks, riskCategories } from "@/lib/mock-data";

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
  const [selected, setSelected] = useState(risks[0]!.id);
  const list = category === "All" ? risks : risks.filter((r) => r.category === category);
  const active = risks.find((r) => r.id === selected) ?? list[0]!;

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Risk Engine"
        title="Corporate risk intelligence engine"
        description="Every extracted disclosure is categorised, scored for severity and confidence, and linked back to its source paragraph."
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {["All", ...riskCategories].map((c) => (
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
                active.id === r.id ? "border-primary/50" : "hover:border-primary/30"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={r.severity} />
                <span className="num text-[10px] text-muted-foreground">{r.id}</span>
                <span className="num ml-auto rounded-md border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {r.category}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium">{r.title}</p>
              <p className="mt-1 text-xs text-muted-foreground">{r.company} · FY{r.year}</p>
              <div className="mt-2.5">
                <ConfidenceMeter value={r.confidence} />
              </div>
            </motion.button>
          ))}
        </div>

        <div className="lg:sticky lg:top-20 lg:h-fit">
          <AnimatePresence mode="wait">
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
              <h2 className="mt-3 text-lg font-semibold">{active.title}</h2>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <SeverityBadge severity={active.severity} />
                <span className="text-xs text-muted-foreground">{active.company} · FY{active.year}</span>
                <span className="num rounded-md border border-border px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">
                  {active.status}
                </span>
              </div>

              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">{active.summary}</p>

              <div className="mt-4 rounded-xl border-l-2 border-primary bg-primary/5 p-3">
                <Quote className="mb-1 size-3.5 text-primary" />
                <p className="text-sm italic leading-relaxed">“{active.quote}”</p>
                <div className="mt-2">
                  <EvidenceLink source={active.source} />
                </div>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="num mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                    <Users className="size-3" /> Named entities
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {active.entities.map((e) => (
                      <span key={e} className="num rounded-md bg-secondary px-2 py-1 text-[10px]">{e}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="num mb-2 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                    <Tag className="size-3" /> Extracted topics
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {active.topics.map((t) => (
                      <span key={t} className="num rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] text-primary">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-5 border-t border-border/60 pt-4">
                <ConfidenceMeter value={active.confidence} label="model confidence" />
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
