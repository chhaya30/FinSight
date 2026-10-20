import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { FileDown, Check, Loader2, AlertCircle } from "lucide-react";
import { GlassCard, PageHeader } from "@/components/ui-kit";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

type Company = {
  id: string;
  name: string;
  ticker_symbol: string | null;
  sector: string | null;
  listed_exchange: string | null;
  country: string | null;
  market_cap: number | null;
  currency: string | null;
  created_at: string;
  updated_at: string;
};

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
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>("");
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
  const [generating, setGenerating] = useState(false);
  const [includeEvolution, setIncludeEvolution] = useState(true);
  const [includeFinancial, setIncludeFinancial] = useState(true);
  const [includeNews, setIncludeNews] = useState(true);

  useEffect(() => {
    api.companies.list({ page_size: 100 })
      .then((data: { companies: Company[] }) => {
        setCompanies(data.companies);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleGeneratePDF = async () => {
    if (!selectedCompanyId) {
      toast.error("Please select a company");
      return;
    }

    setGenerating(true);
    try {
      const blob = await api.reports.downloadExecutiveSummary({
        company_id: selectedCompanyId,
        year: selectedYear,
        include_evolution: includeEvolution,
        include_financial: includeFinancial,
        include_news: includeNews,
      });

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const company = companies.find(c => c.id === selectedCompanyId);
      link.download = `${company?.name?.replace(/\s+/g, '_') || 'Company'}_FY${selectedYear}_Executive_Risk_Summary.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success("PDF report generated and downloaded");
    } catch (err: unknown) {
      const error = err as { message?: string };
      toast.error(error.message || "Failed to generate PDF report");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Reports"
          title="Loading..."
          description="Loading companies..."
        />
      </div>
    );
  }

  const selectedCompany = companies.find(c => c.id === selectedCompanyId);

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
          <select
            value={selectedCompanyId}
            onChange={(e) => setSelectedCompanyId(e.target.value)}
            className="mb-4 w-full rounded-lg border border-border bg-secondary/40 px-2.5 py-2 text-xs outline-none"
          >
            <option value="">Select a company</option>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.ticker_symbol ?? c.id})</option>)}
          </select>

          <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Fiscal Year</p>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            className="mb-4 w-full rounded-lg border border-border bg-secondary/40 px-2.5 py-2 text-xs outline-none"
          >
            {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Options</p>
          <div className="space-y-2 mb-4">
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={includeEvolution}
                onChange={(e) => setIncludeEvolution(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              Include year-over-year evolution
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={includeFinancial}
                onChange={(e) => setIncludeFinancial(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              Include financial health context
            </label>
            <label className="flex items-center gap-2 text-xs cursor-pointer">
              <input
                type="checkbox"
                checked={includeNews}
                onChange={(e) => setIncludeNews(e.target.checked)}
                className="rounded border-border text-primary focus:ring-primary"
              />
              Include market signals
            </label>
          </div>

          <p className="num mb-2 text-[10px] uppercase tracking-wider text-muted-foreground">Sections</p>
          <div className="space-y-1.5 mb-4">
            {sections.map((s, i) => (
              <label key={s} className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2 text-xs">
                <span className="grid size-4 place-items-center rounded-[5px]" style={{ background: i < 5 ? "var(--gradient-primary)" : "var(--muted)" }}>
                  {i < 5 && <Check className="size-3 text-primary-foreground" />}
                </span>
                {s}
              </label>
            ))}
          </div>

          <Button
            className="w-full"
            size="lg"
            onClick={handleGeneratePDF}
            disabled={generating || !selectedCompanyId}
          >
            {generating ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Generating PDF...
              </>
            ) : (
              <>
                <FileDown className="size-4" />
                Generate PDF Report
              </>
            )}
          </Button>
        </GlassCard>

        <GlassCard delay={0.1}>
          <h2 className="mb-3 text-sm font-semibold">Preview</h2>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-card p-6 shadow-inner min-h-[400px]"
          >
            {selectedCompany ? (
              <>
                <p className="num text-[10px] uppercase tracking-[0.2em] text-primary">GlobalRisk AI · Confidential</p>
                <h3 className="mt-2 text-lg font-semibold">{selectedCompany.name} — FY{selectedYear} Risk Briefing</h3>
                <p className="num mt-1 text-[10px] text-muted-foreground">Estimated: ~{sections.length} sections · {companies.length > 0 ? '40+' : '0'} citations</p>
                <div className="mt-4 space-y-2 text-xs leading-relaxed text-muted-foreground">
                  <p>
                    This report will include an executive narrative generated by AI, a breakdown of {companies.length > 0 ? 'identified' : 'potential'} material risks by severity and category,
                    year-over-year evolution analysis (if prior year data exists), financial health context, and an evidence appendix with page-level citations.
                  </p>
                  <p>
                    Risk extraction is performed on the uploaded annual report using semantic section detection, chunking, and LLM-based risk classification.
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
                <div className="mt-4 p-3 rounded-lg bg-primary/5 border border-primary/20">
                  <p className="text-xs text-primary font-medium">Report will be generated with:</p>
                  <ul className="mt-1 text-xs text-muted-foreground space-y-1">
                    <li>• Company: {selectedCompany.name}</li>
                    <li>• Fiscal Year: {selectedYear}</li>
                    <li>• Evolution Analysis: {includeEvolution ? 'Included' : 'Excluded'}</li>
                    <li>• Financial Context: {includeFinancial ? 'Included' : 'Excluded'}</li>
                    <li>• Market Signals: {includeNews ? 'Included' : 'Excluded'}</li>
                  </ul>
                </div>
              </>
            ) : (
              <>
                <p className="num text-[10px] uppercase tracking-[0.2em] text-primary">GlobalRisk AI · Confidential</p>
                <h3 className="mt-2 text-lg font-semibold">Select a company to preview</h3>
                <p className="num mt-1 text-[10px] text-muted-foreground">Configuration will populate preview data</p>
                <div className="mt-4 space-y-1.5">
                  {sections.slice(0, 5).map((s, i) => (
                    <div key={s} className="num flex items-center justify-between border-b border-border/40 pb-1 text-[10px] text-muted-foreground">
                      <span>{i + 1}. {s}</span>
                      <span>p.{(i + 1) * 2}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </motion.div>
        </GlassCard>
      </div>
    </div>
  );
}