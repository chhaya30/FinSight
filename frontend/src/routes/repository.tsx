import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { motion } from "motion/react";
import { UploadCloud, FileText, ScanLine, Search, CheckCircle2, Loader2, Clock } from "lucide-react";
import { GlassCard, PageHeader } from "@/components/ui-kit";
import { documents } from "@/lib/mock-data";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/repository")({
  head: () => ({
    meta: [
      { title: "Corporate Intelligence Repository — GlobalRisk AI" },
      { name: "description", content: "Drag-and-drop filing ingestion with OCR, versioning, metadata and processing status." },
      { property: "og:title", content: "Corporate Intelligence Repository — GlobalRisk AI" },
      { property: "og:description", content: "Ingest, OCR and version multi-company, multi-year filings." },
    ],
  }),
  component: Repository,
});

const statusMeta: Record<string, { icon: typeof Clock; color: string; label: string }> = {
  indexed: { icon: CheckCircle2, color: "var(--positive)", label: "Indexed" },
  processing: { icon: Loader2, color: "var(--severity-medium)", label: "Processing" },
  queued: { icon: Clock, color: "var(--muted-foreground)", label: "Queued" },
};

function Repository() {
  const [dragging, setDragging] = useState(false);
  const [query, setQuery] = useState("");
  const filtered = documents.filter((d) =>
    `${d.name} ${d.company} ${d.type} ${d.year}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Repository"
        title="Corporate intelligence repository"
        description="Multi-company, multi-year filing store with OCR extraction, metadata enrichment and document versioning."
      />

      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
        }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className={`panel flex flex-col items-center justify-center gap-3 border-dashed p-10 text-center transition-colors ${
          dragging ? "border-primary bg-primary/5" : ""
        }`}
      >
        <motion.span
          animate={{ y: dragging ? -6 : 0 }}
          className="grid size-14 place-items-center rounded-2xl"
          style={{ background: "var(--gradient-primary)", boxShadow: "var(--shadow-glow)" }}
        >
          <UploadCloud className="size-6 text-primary-foreground" />
        </motion.span>
        <p className="text-sm font-medium">Drop annual reports, 10-K, 20-F or BRSR PDFs here</p>
        <p className="max-w-md text-xs text-muted-foreground">
          Files are OCR-processed, segmented into disclosure blocks and versioned against prior filings automatically.
        </p>
        <button className="num mt-1 rounded-xl px-4 py-2 text-xs font-medium" style={{ background: "var(--gradient-primary)", color: "var(--primary-foreground)" }}>
          Browse files
        </button>
      </motion.div>

      <div className="mt-4 grid gap-4 lg:grid-cols-4">
        {[
          ["Documents", "1,284"],
          ["OCR pages", "312,406"],
          ["Companies", "6"],
          ["Years covered", "2019 – 2025"],
        ].map(([k, v], i) => (
          <GlassCard key={k} delay={i * 0.05} className="py-4">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</p>
            <p className="num mt-1 text-xl font-semibold">{v}</p>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="mt-4 p-0" delay={0.15}>
        <div className="flex flex-wrap items-center gap-3 border-b border-border/60 p-4">
          <div className="flex flex-1 items-center gap-2 rounded-xl border border-border bg-secondary/40 px-3 py-2">
            <Search className="size-4 text-muted-foreground" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search filings by name, company, type or year"
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>
          <span className="num text-xs text-muted-foreground">{filtered.length} results</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-sm">
            <thead>
              <tr className="num border-b border-border/60 text-left text-[10px] uppercase tracking-wider text-muted-foreground">
                {["Document", "Company", "Type", "Year", "Pages", "Version", "OCR", "Risks", "Status"].map((h) => (
                  <th key={h} className="px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((d, i) => {
                const s = statusMeta[d.status] ?? statusMeta["queued"]!;
                return (
                  <motion.tr
                    key={d.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className="border-b border-border/40 transition-colors last:border-0 hover:bg-secondary/30"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <FileText className="size-4 shrink-0 text-primary" />
                        <span className="num truncate text-xs">{d.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">{d.company}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{d.type}</td>
                    <td className="num px-4 py-3 text-xs">{d.year}</td>
                    <td className="num px-4 py-3 text-xs text-muted-foreground">{d.pages}</td>
                    <td className="num px-4 py-3 text-xs">{d.version}</td>
                    <td className="px-4 py-3">
                      {d.ocr ? <ScanLine className="size-4 text-primary" /> : <span className="text-xs text-muted-foreground">—</span>}
                    </td>
                    <td className="num px-4 py-3 text-xs">{d.risks || "—"}</td>
                    <td className="px-4 py-3">
                      <span className="num inline-flex items-center gap-1.5 text-[11px]" style={{ color: s.color }}>
                        <s.icon className={`size-3.5 ${d.status === "processing" ? "animate-spin" : ""}`} />
                        {s.label}
                      </span>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassCard>

      <GlassCard className="mt-4" delay={0.2}>
        <h2 className="mb-3 text-sm font-semibold">Ingestion pipeline</h2>
        <div className="grid gap-3 md:grid-cols-5">
          {["Upload", "OCR & layout", "Segmentation", "Risk extraction", "Index & version"].map((step, i) => (
            <div key={step} className="rounded-xl border border-border/60 bg-secondary/25 p-3">
              <p className="num text-[10px] text-primary">STEP {i + 1}</p>
              <p className="mt-1 text-xs font-medium">{step}</p>
              <Skeleton className="mt-3 h-1.5 w-full" />
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
