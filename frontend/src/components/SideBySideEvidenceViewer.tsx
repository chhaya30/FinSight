"use client";

import { useState } from "react";
import { FileText, ChevronLeft, ChevronRight, X, ExternalLink } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { GlassCard, SeverityBadge, EvidenceLink } from "@/components/ui-kit";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type ChangeType =
  "NEW" | "REMOVED" | "MODIFIED" | "ESCALATED" | "DE-ESCALATED" | "SEVERITY_UP" | "SEVERITY_DOWN";

type RiskEvidence = {
  document_id?: string;
  report_year?: number;
  page?: number;
  chunk_id?: string;
  text: string;
  section?: string;
  text_hash?: string;
  char_start?: number;
  char_end?: number;
  context_before?: string;
  context_after?: string;
  metadata?: Record<string, unknown>;
};

type RiskItem = {
  id: string;
  category: string;
  severity: string;
  confidence_score: number;
  summary: string;
  source_page?: number;
  source_paragraph?: string;
  source_text_hash?: string;
};

type ViewerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  riskId: string;
  changeType: ChangeType;
  yearPrevious: number;
  yearCurrent: number;
  companyId: string;
  riskPrev?: RiskItem;
  riskCurrent?: RiskItem;
  evidencePrev?: RiskEvidence;
  evidenceCurrent?: RiskEvidence;
};

function getChangeTypeColor(changeType: ChangeType): string {
  switch (changeType) {
    case "NEW":
      return "var(--severity-high)";
    case "REMOVED":
      return "var(--muted-foreground)";
    case "MODIFIED":
    case "ESCALATED":
    case "SEVERITY_UP":
      return "var(--severity-critical)";
    case "DE-ESCALATED":
    case "SEVERITY_DOWN":
      return "var(--severity-medium)";
    default:
      return "var(--primary)";
  }
}

function getChangeTypeLabel(changeType: ChangeType): string {
  switch (changeType) {
    case "NEW":
      return "New Risk";
    case "REMOVED":
      return "Removed Risk";
    case "MODIFIED":
      return "Modified Risk";
    case "ESCALATED":
    case "SEVERITY_UP":
      return "Escalated Risk";
    case "DE-ESCALATED":
    case "SEVERITY_DOWN":
      return "De-escalated Risk";
    default:
      return "Risk Change";
  }
}

export function SideBySideEvidenceViewer({
  open,
  onOpenChange,
  riskId,
  changeType,
  yearPrevious,
  yearCurrent,
  companyId,
  riskPrev,
  riskCurrent,
  evidencePrev,
  evidenceCurrent,
}: ViewerProps) {
  const [loading, setLoading] = useState(false);
  const [pair, setPair] = useState<{
    previous_risk?: RiskItem;
    current_risk?: RiskItem;
    previous_evidence?: RiskEvidence;
    current_evidence?: RiskEvidence;
    change_type?: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tonePrev = "var(--muted-foreground)";
  const toneCurrent = getChangeTypeColor(changeType);

  const fetchEvidence = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.comparison.getRiskEvidence(riskId);
      setPair(data as any);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evidence");
    } finally {
      setLoading(false);
    }
  };

  const prevEvidence = pair?.previous_evidence ?? evidencePrev;
  const currEvidence = pair?.current_evidence ?? evidenceCurrent;
  const prevRisk = pair?.previous_risk ?? riskPrev;
  const currRisk = pair?.current_risk ?? riskCurrent;
  const fetchedChangeType = pair?.change_type ?? changeType;

  const prevText =
    prevEvidence?.text ||
    prevRisk?.source_paragraph ||
    prevRisk?.summary ||
    "No source evidence available for this side.";
  const currText =
    currEvidence?.text ||
    currRisk?.source_paragraph ||
    currRisk?.summary ||
    "No source evidence available for this side.";

  const prevUnavailable = !prevEvidence && !prevRisk;
  const currUnavailable = !currEvidence && !currRisk;

  const prevSeverity = prevRisk?.severity || "medium";
  const currSeverity = currRisk?.severity || "medium";

  const handleViewSource = (year: number, page?: number, chunkId?: string) => {
    if (chunkId) {
      window.open(
        `${import.meta.env.VITE_API_BASE_URL?.replace("/api/v1", "")}/documents/${chunkId}`,
        "_blank",
      );
    } else if (page) {
      window.open(
        `/evidence?company_id=${companyId}&year_previous=${yearPrevious}&year_current=${yearCurrent}&risk_id=${riskId}`,
        "_blank",
      );
    }
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[1200px] max-h-[90vh] overflow-hidden p-0" role="dialog" aria-modal="true" aria-label="Side-by-side evidence comparison">
        <DialogHeader className="p-6 pb-0">
          <DialogTitle className="flex items-center justify-between">
            <div>
              <p className="num text-[11px] uppercase tracking-[0.22em] text-primary">
                Evidence Viewer
              </p>
              <h2 className="text-lg font-semibold">
                {getChangeTypeLabel(fetchedChangeType)} ·{" "}
                {prevRisk?.category ?? currRisk?.category ?? "Risk"}
              </h2>
            </div>
            <span
              className="num inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider"
              style={{
                color: toneCurrent,
                background: `color-mix(in oklab, ${toneCurrent} 14%, transparent)`,
                border: `1px solid color-mix(in oklab, ${toneCurrent} 34%, transparent)`,
              }}
              aria-label={`Change type: ${getChangeTypeLabel(fetchedChangeType)}`}
            >
              <span className="size-1.5 rounded-full" style={{ background: toneCurrent }} aria-hidden="true" />
              {getChangeTypeLabel(fetchedChangeType)}
            </span>
          </DialogTitle>
          <DialogDescription>
            FY{yearPrevious} ↔ FY{yearCurrent} · Side-by-side source evidence comparison
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 pb-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {loading && (
            <div className="flex items-center justify-center py-12" role="status" aria-live="polite">
              <div className="flex flex-col items-center gap-3">
                <div className="size-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">Loading evidence...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}

          {!loading && !error && (
            <div className="grid gap-4 lg:grid-cols-2" role="region" aria-label="Side-by-side evidence panels">
              <article className="panel flex flex-col" aria-labelledby="prev-report-heading">
                <header className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                  <div>
                    <p id="prev-report-heading" className="text-sm font-semibold">Previous annual report</p>
                    <p className="num text-[10px] text-muted-foreground">
                      FY{yearPrevious} ·{" "}
                      {prevEvidence?.section || prevRisk?.category || "Risk disclosure"}
                    </p>
                  </div>
                  <span
                    className="num rounded-md border px-2 py-0.5 text-[10px]"
                    style={{
                      color: tonePrev,
                      borderColor: `color-mix(in oklab, ${tonePrev} 40%, transparent)`,
                    }}
                    aria-label={`Page reference: ${prevEvidence?.page ? `p.${prevEvidence.page}` : prevRisk?.source_page ? `p.${prevRisk.source_page}` : "source unavailable"}`}
                  >
                    {prevEvidence?.page
                      ? `p.${prevEvidence.page}`
                      : prevRisk?.source_page
                        ? `p.${prevRisk.source_page}`
                        : "source"}
                  </span>
                </header>
                <div
                  role="region"
                  aria-label={`Previous year evidence text`}
                  className={`flex-1 p-5 text-sm leading-relaxed overflow-y-auto ${prevUnavailable ? "text-muted-foreground/60 italic" : ""}`}
                  tabIndex={0}
                  style={
                    !prevUnavailable
                      ? {
                          background: `color-mix(in oklab, ${tonePrev} 10%, transparent)`,
                          boxShadow: `inset 2px 0 0 ${tonePrev}`,
                        }
                      : undefined
                  }
                >
                  {prevText}
                </div>
                <footer className="border-t border-border/60 p-4">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <SeverityBadge severity={prevSeverity.toLowerCase() as any} />
                    {prevEvidence?.page && (
                      <EvidenceLink source={`FY${yearPrevious} AR p.${prevEvidence.page}`} />
                    )}
                  </div>
                  <button
                    onClick={() =>
                      handleViewSource(yearPrevious, prevEvidence?.page, prevEvidence?.chunk_id)
                    }
                    className="num inline-flex items-center gap-1.5 rounded-md border border-border/70 bg-secondary/40 px-3 py-1.5 text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
                    disabled={prevUnavailable}
                    aria-label={prevUnavailable ? "Source unavailable" : `View source for FY${yearPrevious} risk on page ${prevEvidence?.page ?? prevRisk?.source_page ?? "unknown"}`}
                  >
                    <FileText className="size-3.5" aria-hidden="true" />
                    View source
                    <ExternalLink className="size-3.5" aria-hidden="true" />
                  </button>
                </footer>
              </article>

              <article className="panel flex flex-col" aria-labelledby="curr-report-heading">
                <header className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                  <div>
                    <p id="curr-report-heading" className="text-sm font-semibold">Current annual report</p>
                    <p className="num text-[10px] text-muted-foreground">
                      FY{yearCurrent} ·{" "}
                      {currEvidence?.section || currRisk?.category || "Risk disclosure"}
                    </p>
                  </div>
                  <span
                    className="num rounded-md border px-2 py-0.5 text-[10px]"
                    style={{
                      color: toneCurrent,
                      borderColor: `color-mix(in oklab, ${toneCurrent} 40%, transparent)`,
                    }}
                    aria-label={`Page reference: ${currEvidence?.page ? `p.${currEvidence.page}` : currRisk?.source_page ? `p.${currRisk.source_page}` : "source unavailable"}`}
                  >
                    {currEvidence?.page
                      ? `p.${currEvidence.page}`
                      : currRisk?.source_page
                        ? `p.${currRisk.source_page}`
                        : "source"}
                  </span>
                </header>
                <div
                  role="region"
                  aria-label={`Current year evidence text`}
                  className={`flex-1 p-5 text-sm leading-relaxed overflow-y-auto ${currUnavailable ? "text-muted-foreground/60 italic" : ""}`}
                  tabIndex={0}
                  style={
                    !currUnavailable
                      ? {
                          background: `color-mix(in oklab, ${toneCurrent} 10%, transparent)`,
                          boxShadow: `inset 2px 0 0 ${toneCurrent}`,
                        }
                      : undefined
                  }
                >
                  {currText}
                </div>
                <div className="border-t border-border/60 p-4">
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <SeverityBadge severity={currSeverity.toLowerCase() as any} />
                    {currEvidence?.page && (
                      <EvidenceLink source={`FY${yearCurrent} AR p.${currEvidence.page}`} />
                    )}
                  </div>
                  <button
                    onClick={() =>
                      handleViewSource(yearCurrent, currEvidence?.page, currEvidence?.chunk_id)
                    }
                    className="num inline-flex items-center gap-1.5 rounded-md border border-border/70 bg-secondary/40 px-3 py-1.5 text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-primary"
                    disabled={currUnavailable}
                  >
                    <FileText className="size-3.5" />
                    View source
                    <ExternalLink className="size-3.5" />
                  </button>
                </div>
</article>
              </div>
            )}

          {!loading && !error && (
            <GlassCard className="mt-4" delay={0.1}>
              <div className="mb-3 flex items-center gap-2">
                <FileText className="size-4 text-primary" />
                <h2 className="text-sm font-semibold">Change context</h2>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {currRisk?.summary || prevRisk?.summary || "No summary available for this change."}
              </p>
            </GlassCard>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
