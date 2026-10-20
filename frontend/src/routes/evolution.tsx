import { Fragment } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, useCallback } from "react";
import { motion } from "motion/react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import {
  Plus,
  Minus,
  TrendingUp,
  Flame,
  Eye,
  AlertTriangle,
  RefreshCw,
  FileText,
  ExternalLink,
} from "lucide-react";
import { GlassCard, PageHeader, SeverityBadge, ConfidenceMeter } from "@/components/ui-kit";
import { api, type DocumentStatusResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { SideBySideEvidenceViewer } from "@/components/SideBySideEvidenceViewer";

type RiskEvidence = {
  document_id: string | null;
  report_year: number | null;
  page: number | null;
  chunk_id: string | null;
  text: string;
  section: string | null;
  text_hash: string | null;
  char_start: number | null;
  char_end: number | null;
  context_before: string | null;
  context_after: string | null;
  metadata: Record<string, unknown>;
};

type RiskItem = {
  id: string;
  report_id: string;
  category: string;
  severity: string;
  confidence_score: number;
  summary: string;
  source_page: number | null;
  source_paragraph: string | null;
  source_text_hash: string | null;
  entities: Array<{
    entity_type: string;
    text: string;
    start_char: number | null;
    end_char: number | null;
    confidence: number | null;
  }>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

type RiskWithEvidence = {
  risk: RiskItem;
  evidence: RiskEvidence | null;
};

type ComparisonResponse = {
  company_id: string;
  year_current: number;
  year_previous: number;
  new_risks: RiskWithEvidence[];
  removed_risks: RiskWithEvidence[];
  severity_increased: RiskWithEvidence[];
  severity_decreased: RiskWithEvidence[];
  modified_risks: RiskWithEvidence[];
  total_changes: number;
  ai_summary: string | null;
  processing_time_seconds: number;
};

type HeatmapCell = {
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  count: number;
  score: number;
};

type HeatmapResponse = {
  cells: HeatmapCell[];
  total_risks: number;
};

type RiskTrendPoint = {
  year: number;
  score: number;
};

type EvolutionSummaryResponse = {
  company_id: string;
  period: string;
  total_risks_current: number;
  total_risks_previous: number;
  net_change: number;
  new_risks_count: number;
  removed_risks_count: number;
  severity_changes: { increased: number; decreased: number; modified: number };
  top_new_categories: Array<{ category: string; count: number }>;
  top_removed_categories: Array<{ category: string; count: number }>;
  ai_narrative: string;
};

type EvidenceComparisonResponse = {
  risk_id: string;
  change_type: string | null;
  previous_risk: RiskItem | null;
  current_risk: RiskItem | null;
  previous_evidence: RiskEvidence | null;
  current_evidence: RiskEvidence | null;
};

function heatColor(v: number) {
  if (v >= 75) return "var(--severity-critical)";
  if (v >= 55) return "var(--severity-high)";
  if (v >= 35) return "var(--severity-medium)";
  return "var(--severity-low)";
}

function formatSeverity(severity: string) {
  return severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase();
}

function RiskCard({
  risk,
  evidence,
  changeType,
  onViewEvidence,
}: {
  risk: RiskItem;
  evidence: RiskEvidence | null;
  changeType: string;
  onViewEvidence: () => void;
}) {
  const isRemoved = changeType === "REMOVED";
  const badgeColor: Record<string, string> = {
    NEW: "var(--severity-high)",
    ESCALATED: "var(--severity-critical)",
    DE_ESCALATED: "var(--positive)",
    MODIFIED: "var(--severity-medium)",
    REMOVED: "var(--positive)",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border border-border/60 bg-secondary/25 p-2.5 ${isRemoved ? "opacity-70" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={risk.severity.toLowerCase() as any} />
            <span className="num text-[10px] text-muted-foreground truncate">{risk.category}</span>
            <span
              className="ml-auto px-1.5 py-0.5 text-[9px] font-medium rounded shrink-0"
              style={{
                background: `${badgeColor[changeType] ?? "var(--muted)"}20`,
                color: badgeColor[changeType] ?? "var(--muted-foreground)",
              }}
            >
              {changeType}
            </span>
          </div>
          <p className="mt-1.5 text-xs line-clamp-2 truncate-2" title={risk.summary}>{risk.summary}</p>
          {evidence?.page && (
            <p className="mt-1 num text-[10px] text-muted-foreground flex items-center gap-1 truncate">
              <FileText className="size-3" aria-hidden="true" />
              Page {evidence.page}
              {evidence.section && <span> · {evidence.section}</span>}
            </p>
          )}
          <ConfidenceMeter value={risk.confidence_score} className="mt-1.5" />
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 p-0 shrink-0"
          onClick={onViewEvidence}
          aria-label={`View evidence for ${risk.category} risk`}
        >
          <Eye className="size-3.5" aria-hidden="true" />
        </Button>
      </div>
    </motion.div>
  );
}

function Evolution() {
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [summary, setSummary] = useState<EvolutionSummaryResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);
  const [heatmapTotalRisks, setHeatmapTotalRisks] = useState(0);
  const [riskTrend, setRiskTrend] = useState<RiskTrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [companyId, setCompanyId] = useState("");
  const [yearCurrent, setYearCurrent] = useState(new Date().getFullYear());
  const [yearPrevious, setYearPrevious] = useState(new Date().getFullYear() - 1);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerRiskId, setViewerRiskId] = useState("");
  const [viewerChangeType, setViewerChangeType] = useState<
    "NEW" | "REMOVED" | "MODIFIED" | "ESCALATED" | "DE_ESCALATED" | "SEVERITY_UP" | "SEVERITY_DOWN"
  >("NEW");
  const [viewerRiskPrev, setViewerRiskPrev] = useState<RiskItem | null>(null);
  const [viewerRiskCurrent, setViewerRiskCurrent] = useState<RiskItem | null>(null);
  const [viewerEvidencePrev, setViewerEvidencePrev] = useState<RiskEvidence | null>(null);
  const [viewerEvidenceCurrent, setViewerEvidenceCurrent] = useState<RiskEvidence | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
    const cid =
      params.get("company") ??
      params.get("company_id") ??
      import.meta.env.VITE_DASHBOARD_COMPANY_ID ??
      "";
    const yc = Number(
      params.get("yearA") ??
        params.get("year_current") ??
        import.meta.env.VITE_DASHBOARD_YEAR_CURRENT ??
        new Date().getFullYear(),
    );
    const yp = Number(
      params.get("yearB") ??
        params.get("year_previous") ??
        import.meta.env.VITE_DASHBOARD_YEAR_PREVIOUS ??
        new Date().getFullYear() - 1,
    );
    setCompanyId(cid);
    setYearCurrent(yc);
    setYearPrevious(yp);
  }, []);

  const fetchData = useCallback(async () => {
    if (!companyId) return;
    setLoading(true);
    setError(null);
    try {
      const [compData, summaryData, heatmapData, trendData] = await Promise.all([
        api.comparison.compare({
          company_id: companyId,
          year_current: yearCurrent,
          year_previous: yearPrevious,
        }),
        api.comparison.getEvolution(companyId, yearCurrent, yearPrevious),
        api.dashboard.getHeatmap(companyId, yearCurrent),
        api.dashboard.getRiskEvolution(companyId),
      ]);
      setComparison(compData);
      setSummary(summaryData);
      setHeatmap(heatmapData.cells);
      setHeatmapTotalRisks(heatmapData.total_risks);
      setRiskTrend(trendData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load comparison");
    } finally {
      setLoading(false);
    }
  }, [companyId, yearCurrent, yearPrevious]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const openEvidence = async (
    riskId: string,
    changeType:
      | "NEW"
      | "REMOVED"
      | "MODIFIED"
      | "ESCALATED"
      | "DE_ESCALATED"
      | "SEVERITY_UP"
      | "SEVERITY_DOWN",
    riskPrev?: RiskItem,
    riskCurrent?: RiskItem,
    evidencePrev?: RiskEvidence,
    evidenceCurrent?: RiskEvidence,
  ) => {
    try {
      const evidence = await api.comparison.getRiskEvidence(riskId);
      setViewerRiskId(riskId);
      setViewerChangeType(changeType);
      setViewerRiskPrev(evidence.previous_risk ?? riskPrev ?? null);
      setViewerRiskCurrent(evidence.current_risk ?? riskCurrent ?? null);
      setViewerEvidencePrev(evidence.previous_evidence ?? evidencePrev ?? null);
      setViewerEvidenceCurrent(evidence.current_evidence ?? evidenceCurrent ?? null);
      setViewerOpen(true);
    } catch (err) {
      console.error("Failed to load evidence:", err);
    }
  };

  const closeViewer = () => {
    setViewerOpen(false);
    setViewerRiskId("");
    setViewerRiskPrev(null);
    setViewerRiskCurrent(null);
    setViewerEvidencePrev(null);
    setViewerEvidenceCurrent(null);
  };

  if (loading)
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Risk Comparison"
          title="Loading..."
          description="Fetching year-over-year risk comparison data."
        />
        <div className="flex min-h-[55vh] max-w-xl items-center justify-center mx-auto">
          <GlassCard className="w-full text-center">
            <div className="mx-auto grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
              <RefreshCw className="size-5 animate-spin" />
            </div>
            <h1 className="mt-4 text-lg font-semibold">Loading comparison</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Computing year-over-year risk changes
            </p>
          </GlassCard>
        </div>
      </div>
    );

  if (error)
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Risk Comparison"
          title="Error"
          description="Failed to load comparison data."
        />
        <div className="flex min-h-[55vh] max-w-xl items-center justify-center mx-auto">
          <GlassCard className="w-full text-center">
            <div className="mx-auto grid size-10 place-items-center rounded-xl bg-destructive/10 text-destructive">
              <AlertTriangle className="size-5" />
            </div>
            <h1 className="mt-4 text-lg font-semibold">Comparison unavailable</h1>
            <p className="mt-2 text-sm text-muted-foreground">{error}</p>
            <Button className="mt-4" onClick={fetchData}>
              <RefreshCw className="size-4 mr-2" />
              Retry
            </Button>
          </GlassCard>
        </div>
      </div>
    );

  if (!comparison) {
    return (
      <div className="mx-auto max-w-[1400px]">
        <PageHeader
          eyebrow="Risk Comparison"
          title="No Data"
          description="No comparison data available for the selected company and years."
        />
      </div>
    );
  }

  const added = comparison.new_risks ?? [];
  const escalated = comparison.severity_increased ?? [];
  const deescalated = comparison.severity_decreased ?? [];
  const modified = comparison.modified_risks ?? [];
  const removed = comparison.removed_risks ?? [];

  const totalCurrentRisks =
    summary?.total_risks_current ??
    added.length + escalated.length + deescalated.length + modified.length;
  const totalPreviousRisks =
    summary?.total_risks_previous ??
    removed.length + escalated.length + deescalated.length + modified.length;
  const riskScoreChange = summary?.net_change ?? totalCurrentRisks - totalPreviousRisks;

  return (
    <div className="mx-auto max-w-[1400px]">
      <PageHeader
        eyebrow="Risk Comparison"
        title={`Risk Comparison: FY{yearPrevious} → FY{yearCurrent}`}
        description={
          summary?.ai_narrative ??
          "Year-over-year risk additions, removals, severity changes, and emerging themes."
        }
      />

      {/* Risk Score Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <GlassCard delay={0}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">Previous Year Risks</p>
              <p className="num text-3xl font-bold">{totalPreviousRisks}</p>
            </div>
            <div className="grid w-12 place-items-center rounded-xl bg-muted/50 text-muted-foreground">
              <FileText className="size-5" />
            </div>
          </div>
        </GlassCard>
        <GlassCard delay={0.05}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">Current Year Risks</p>
              <p className="num text-3xl font-bold">{totalCurrentRisks}</p>
            </div>
            <div className="grid w-12 place-items-center rounded-xl bg-primary/10 text-primary">
              <FileText className="size-5" />
            </div>
          </div>
        </GlassCard>
        <GlassCard
          delay={0.1}
          className={riskScoreChange >= 0 ? "border-destructive/30" : "border-positive/30"}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground">Net Change</p>
              <p
                className="num text-3xl font-bold"
                style={{ color: riskScoreChange >= 0 ? "var(--destructive)" : "var(--positive)" }}
              >
                {riskScoreChange >= 0 ? "+" : ""}
                {riskScoreChange}
              </p>
            </div>
            <div
              className="grid w-12 place-items-center rounded-xl"
              style={{
                background: riskScoreChange >= 0 ? "var(--destructive)/10" : "var(--positive)/10",
              }}
            >
              {riskScoreChange >= 0 ? (
                <TrendingUp className="size-5" style={{ color: "var(--destructive)" }} />
              ) : (
                <TrendingUp className="size-5" style={{ color: "var(--positive)" }} />
              )}
            </div>
          </div>
        </GlassCard>
      </div>

      {/* LLM Explanation */}
      {comparison.ai_summary && (
        <GlassCard className="mt-4" delay={0.15}>
          <div className="flex items-start gap-3">
            <div className="grid w-8 place-items-center rounded-xl bg-primary/10 text-primary mt-0.5">
              <Flame className="size-4" />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold">AI Explanation</h3>
              <p className="mt-1 text-sm text-muted-foreground whitespace-pre-wrap">
                {comparison.ai_summary}
              </p>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Risk Changes Grid */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* New Risks */}
        <GlassCard delay={0.2}>
          <div className="mb-3 flex items-center gap-2">
            <Plus className="size-4" style={{ color: "var(--severity-high)" }} />
            <h2 className="text-sm font-semibold">New Risks ({added.length})</h2>
          </div>
          <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
            {added.map((item) => (
              <RiskCard
                key={item.risk.id}
                risk={item.risk}
                evidence={item.evidence}
                changeType="NEW"
                onViewEvidence={() =>
                  openEvidence(item.risk.id, "NEW", undefined, item.risk, undefined, item.evidence)
                }
              />
            ))}
            {added.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">
                No new risks detected
              </div>
            )}
          </div>
        </GlassCard>

        {/* Escalated Risks */}
        <GlassCard delay={0.25}>
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="size-4" style={{ color: "var(--severity-critical)" }} />
            <h2 className="text-sm font-semibold">Severity Increased ({escalated.length})</h2>
          </div>
          <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
            {escalated.map((item) => (
              <RiskCard
                key={item.risk.id}
                risk={item.risk}
                evidence={item.evidence}
                changeType="ESCALATED"
                onViewEvidence={() =>
                  openEvidence(
                    item.risk.id,
                    "ESCALATED",
                    undefined,
                    item.risk,
                    undefined,
                    item.evidence,
                  )
                }
              />
            ))}
            {escalated.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">
                No escalated risks
              </div>
            )}
          </div>
        </GlassCard>

        {/* De-escalated Risks */}
        <GlassCard delay={0.3}>
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp
              className="size-4"
              style={{ color: "var(--positive)", transform: "rotate(180deg)" }}
            />
            <h2 className="text-sm font-semibold">Severity Decreased ({deescalated.length})</h2>
          </div>
          <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
            {deescalated.map((item) => (
              <RiskCard
                key={item.risk.id}
                risk={item.risk}
                evidence={item.evidence}
                changeType="DE_ESCALATED"
                onViewEvidence={() =>
                  openEvidence(
                    item.risk.id,
                    "DE_ESCALATED",
                    undefined,
                    item.risk,
                    undefined,
                    item.evidence,
                  )
                }
              />
            ))}
            {deescalated.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">
                No de-escalated risks
              </div>
            )}
          </div>
        </GlassCard>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* Modified Risks */}
        <GlassCard delay={0.35}>
          <div className="mb-3 flex items-center gap-2">
            <Minus className="size-4" style={{ color: "var(--severity-medium)" }} />
            <h2 className="text-sm font-semibold">Modified Risks ({modified.length})</h2>
          </div>
          <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
            {modified.map((item) => (
              <RiskCard
                key={item.risk.id}
                risk={item.risk}
                evidence={item.evidence}
                changeType="MODIFIED"
                onViewEvidence={() =>
                  openEvidence(
                    item.risk.id,
                    "MODIFIED",
                    undefined,
                    item.risk,
                    undefined,
                    item.evidence,
                  )
                }
              />
            ))}
            {modified.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">
                No modified risks
              </div>
            )}
          </div>
        </GlassCard>

        {/* Removed Risks */}
        <GlassCard delay={0.4}>
          <div className="mb-3 flex items-center gap-2">
            <Minus className="size-4" style={{ color: "var(--positive)" }} />
            <h2 className="text-sm font-semibold">Removed Risks ({removed.length})</h2>
          </div>
          <div className="space-y-2.5 max-h-[400px] overflow-y-auto">
            {removed.map((item) => (
              <RiskCard
                key={item.risk.id}
                risk={item.risk}
                evidence={item.evidence}
                changeType="REMOVED"
                onViewEvidence={() =>
                  openEvidence(
                    item.risk.id,
                    "REMOVED",
                    item.risk,
                    undefined,
                    item.evidence,
                    undefined,
                  )
                }
              />
            ))}
            {removed.length === 0 && (
              <div className="text-xs text-muted-foreground text-center py-4">No removed risks</div>
            )}
          </div>
        </GlassCard>

        {/* Processing Info */}
        <GlassCard delay={0.45}>
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="size-4" style={{ color: "var(--muted-foreground)" }} />
            <h2 className="text-sm font-semibold">Processing Info</h2>
          </div>
          <div className="space-y-2 text-xs text-muted-foreground">
            <p>
              Total changes: <span className="font-medium">{comparison.total_changes}</span>
            </p>
            <p>
              Processing time:{" "}
              <span className="font-medium">{comparison.processing_time_seconds.toFixed(2)}s</span>
            </p>
            <p>
              Comparison:{" "}
              <span className="font-medium">
                FY{yearPrevious} → FY{yearCurrent}
              </span>
            </p>
            {summary && (
              <>
                <p>
                  New risks: <span className="font-medium">{summary.new_risks_count}</span>
                </p>
                <p>
                  Removed risks: <span className="font-medium">{summary.removed_risks_count}</span>
                </p>
                <p>
                  Escalated:{" "}
                  <span className="font-medium">{summary.severity_changes.increased}</span>
                </p>
                <p>
                  De-escalated:{" "}
                  <span className="font-medium">{summary.severity_changes.decreased}</span>
                </p>
                <p>
                  Modified: <span className="font-medium">{summary.severity_changes.modified}</span>
                </p>
              </>
            )}
          </div>
        </GlassCard>
      </div>

      {/* Risk Trend Chart */}
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <GlassCard delay={0.5}>
          <h2 className="mb-4 text-sm font-semibold">Composite Risk Score Timeline</h2>
          {riskTrend.length > 0 ? (
            <figure className="w-full" aria-label="Composite risk score timeline chart showing risk score over years">
              <figcaption className="sr-only">
                Line chart showing composite risk score from {riskTrend[0]?.year} to {riskTrend[riskTrend.length - 1]?.year}.
                Current score: {riskTrend[riskTrend.length - 1]?.score ?? 'N/A'}.
                {riskTrend.length > 1 && `Change: ${((riskTrend[riskTrend.length - 1]?.score ?? 0) - (riskTrend[0]?.score ?? 0)).toFixed(1)}`}
              </figcaption>
              <ResponsiveContainer width="100%" height={230}>
                <LineChart data={riskTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis
                    dataKey="year"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Year', position: 'insideBottom', offset: -10, fill: 'var(--muted-foreground)', fontSize: 11 }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Risk Score', angle: -90, position: 'insideLeft', offset: 10, fill: 'var(--muted-foreground)', fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "var(--popover)",
                      border: "1px solid var(--border)",
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                    formatter={(value: number) => [value.toFixed(1), 'Risk Score']}
                    labelFormatter={(year: number) => `Year ${year}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="var(--chart-1)"
                    strokeWidth={2.4}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </figure>
          ) : (
            <div className="text-xs text-muted-foreground text-center py-8" role="status">
              No trend data available
            </div>
          )}
        </GlassCard>

        <GlassCard delay={0.55}>
          <div className="mb-3 flex items-center gap-2">
            <Flame className="size-4 text-primary" />
            <h2 className="text-sm font-semibold">Top New Risk Categories</h2>
          </div>
          <div className="space-y-3">
            {summary?.top_new_categories?.slice(0, 5).map((cat, i) => (
              <motion.div
                key={cat.category}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.06 }}
                className="rounded-xl border border-border/60 bg-secondary/25 p-3"
              >
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium">{cat.category}</p>
                  <span className="num text-[11px]" style={{ color: "var(--negative)" }}>
                    {cat.count} new
                  </span>
                </div>
              </motion.div>
            ))}
            {!summary?.top_new_categories?.length && (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="rounded-xl border border-border/60 bg-secondary/25 p-3"
              >
                <p className="text-xs text-muted-foreground">No emerging themes detected</p>
              </motion.div>
            )}
          </div>
        </GlassCard>
      </div>

      {/* Heatmap */}
      <GlassCard className="mt-4 overflow-x-auto" delay={0.6}>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Category × Severity Heatmap</h2>
          <span className="num text-[10px] text-muted-foreground">
            Total risks: {heatmapTotalRisks}
          </span>
        </div>
        {heatmap.length > 0 ? (
          <figure className="min-w-[720px]" aria-label="Category by severity heatmap showing risk counts">
            <figcaption className="sr-only">
              Heatmap with {Array.from(new Set(heatmap.map(c => c.category))).length} risk categories and 4 severity levels.
              Total risks: {heatmapTotalRisks}. Categories: {Array.from(new Set(heatmap.map(c => c.category))).join(', ')}.
            </figcaption>
            {/* Get unique categories and severities */}
            {(() => {
              const categories = Array.from(new Set(heatmap.map((c) => c.category))).sort();
              const severities: ("critical" | "high" | "medium" | "low")[] = [
                "critical",
                "high",
                "medium",
                "low",
              ];
              const severityLabels = {
                critical: "Critical",
                high: "High",
                medium: "Medium",
                low: "Low",
              };
              const severityColors = {
                critical: "var(--severity-critical)",
                high: "var(--severity-high)",
                medium: "var(--severity-medium)",
                low: "var(--severity-low)",
              };

              // Create a map for quick lookup
              const cellMap = new Map<string, HeatmapCell>();
              heatmap.forEach((cell) => {
                cellMap.set(`${cell.category}|${cell.severity}`, cell);
              });

              return (
                <div
                  role="table"
                  aria-label="Risk category by severity matrix"
                  className="grid gap-1.5"
                  style={{ gridTemplateColumns: `120px repeat(${categories.length}, 1fr)` }}
                >
                  {/* Header row */}
                  <div role="columnheader" aria-label="Severity" />
                  {categories.map((cat) => (
                    <div
                      key={cat}
                      role="columnheader"
                      className="num pb-1 text-center text-[10px] text-muted-foreground font-medium"
                    >
                      {cat}
                    </div>
                  ))}

                  {/* Severity rows */}
                  {severities.map((sev) => (
                    <Fragment key={sev}>
                      <div
                        role="rowheader"
                        className="flex items-center pr-2 text-[11px] font-medium"
                        style={{ color: severityColors[sev] }}
                      >
                        {severityLabels[sev]}
                      </div>
                      {categories.map((cat) => {
                        const cell = cellMap.get(`${cat}|${sev}`);
                        const count = cell?.count ?? 0;
                        const score = cell?.score ?? 0;
                        const maxCount = Math.max(...heatmap.map((c) => c.count), 1);
                        const intensity = count > 0 ? 20 + (count / maxCount) * 80 : 0;

                        return (
                          <motion.div
                            key={`${cat}|${sev}`}
                            role="cell"
                            aria-label={`${cat}, ${severityLabels[sev]}: ${count} risks, average score ${score.toFixed(1)}`}
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.3 }}
                            className="num grid h-9 place-items-center rounded-md text-[10px] font-medium transition-transform hover:scale-105"
                            style={{
                              background:
                                count > 0
                                  ? `color-mix(in oklab, ${severityColors[sev]} ${intensity}%, transparent)`
                                  : "transparent",
                              color: intensity > 60 ? "var(--background)" : "var(--foreground)",
                              border:
                                count > 0
                                  ? `1px solid color-mix(in oklab, ${severityColors[sev]} 40%, transparent)`
                                  : "1px solid var(--border)",
                            }}
                          >
                            {count > 0 ? count : "—"}
                          </motion.div>
                        );
                      })}
                    </Fragment>
                  ))}
                </div>
              );
            })()}
          </figure>
        ) : (
          <div className="text-xs text-muted-foreground text-center py-8" role="status">
            No heatmap data available
          </div>
        )}
      </GlassCard>

      {/* Evidence Viewer */}
      <SideBySideEvidenceViewer
        open={viewerOpen}
        onOpenChange={closeViewer}
        riskId={viewerRiskId}
        changeType={viewerChangeType}
        yearPrevious={yearPrevious}
        yearCurrent={yearCurrent}
        companyId={companyId}
        riskPrev={viewerRiskPrev}
        riskCurrent={viewerRiskCurrent}
        evidencePrev={viewerEvidencePrev}
        evidenceCurrent={viewerEvidenceCurrent}
      />
    </div>
  );
}

export const Route = createFileRoute("/evolution")({
  head: () => ({
    meta: [
      { title: "Risk Evolution Analytics — GlobalRisk AI" },
      {
        name: "description",
        content:
          "Track new and removed risks, severity migration, emerging themes, timelines and category heatmaps.",
      },
      { property: "og:title", content: "Risk Evolution Analytics — GlobalRisk AI" },
      {
        property: "og:description",
        content: "Year-over-year disclosure evolution and emerging risk themes.",
      },
    ],
  }),
  component: Evolution,
});
